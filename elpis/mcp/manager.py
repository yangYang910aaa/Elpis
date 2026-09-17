"""MCP 服务器连接与工具适配层

把外部 MCP 服务器（Streamable HTTP 传输）暴露的工具加载为 LangChain 工具，
与内建工具（elpis.tools.ALL_TOOLS）合并后交给 Agent 调用。

设计要点：
- 声明式配置：servers.yaml 列出服务器清单，${ENV_VAR} 占位符从 .env 解析
- 长驻连接：CLI 进程内连接复用（模块级单例 + 异步锁）
- 优雅降级：单个服务器连接失败只影响它自己；全部失败返回空列表，不拖垮 Agent
- 零额外依赖：直接用 mcp 官方 SDK（httpx2 + ClientSession），不引入 langchain-mcp-adapters
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from elpis.config import settings

import httpx2
import yaml
from langchain_core.tools import BaseTool, StructuredTool
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# ==================== 模块级单例（CLI 长驻进程内复用） ====================

_mcp_tools: list[BaseTool] | None = None
_load_lock: asyncio.Lock | None = None
_last_error: str = ""
_connections: list[ServerConnection] = []


def _get_lock() -> asyncio.Lock:
    global _load_lock
    if _load_lock is None:
        _load_lock = asyncio.Lock()
    return _load_lock


def get_last_error() -> str:
    """返回最近一次加载失败的原因（无则空字符串）"""
    return _last_error


def reset_mcp_tools() -> None:
    """清空缓存的工具列表（测试 / 配置变更后重新加载时使用）"""
    global _mcp_tools, _last_error
    _mcp_tools = None
    _last_error = ""


# ==================== 配置加载 ====================

def _servers_yaml_path() -> Path:
    return Path(__file__).resolve().parent / "servers.yaml"


def _resolve_env(value: str) -> str:
    """替换字符串中的 ${ENV_VAR} 占位符。

    取值顺序：elpis.config.settings（已从 .env 加载）→ os.environ。
    """
    def repl(match: re.Match) -> str:
        name = match.group(1)
        val = getattr(settings, name.lower(), None)
        if val is None:
            val = os.environ.get(name, "")
        return str(val)

    return re.sub(r"\$\{(\w+)\}", repl, value)


def load_server_configs() -> list[dict]:
    """读取 servers.yaml，解析占位符，返回已启用的服务器配置列表。"""
    path = _servers_yaml_path()
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    servers = data.get("servers", [])
    for cfg in servers:
        headers = cfg.get("headers") or {}
        cfg["headers"] = {k: _resolve_env(str(v)) for k, v in headers.items()}
    return [c for c in servers if c.get("enabled", True)]


# ==================== 单个服务器连接 ====================

class ServerConnection:
    """管理一个 MCP 服务器的会话生命周期。

    连接在 start() 建立、在进程结束时随 GC 释放；期间所有工具调用复用同一会话。
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._http_client: httpx2.AsyncClient | None = None
        self._transport_cm: Any = None
        self._streams: Any = None
        self.session: ClientSession | None = None

    async def start(self) -> None:
        """建立 Streamable HTTP 连接并完成 MCP initialize 握手"""
        headers = self.cfg.get("headers") or {}
        self._http_client = httpx2.AsyncClient(headers=headers, timeout=30.0)
        self._transport_cm = streamable_http_client(
            self.cfg["url"], http_client=self._http_client
        )
        self._streams = await self._transport_cm.__aenter__()
        read_stream, write_stream = self._streams
        self.session = ClientSession(read_stream, write_stream)
        # mcp 2.x：__aenter__ 启动内部 dispatcher（task group），否则发请求会报
        # "JSONRPCDispatcher.send_raw_request called before run()"
        await self.session.__aenter__()
        await self.session.initialize()

    async def close(self) -> None:
        """关闭会话与连接（幂等）"""
        if self.session is not None:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None
        if self._transport_cm is not None and self._streams is not None:
            try:
                await self._transport_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._transport_cm = None
            self._streams = None
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            except Exception:
                pass
            self._http_client = None

    async def list_tools(self) -> list[Any]:
        """拉取服务器声明的工具列表（mcp.types.Tool）"""
        assert self.session is not None, "连接尚未建立"
        result = await self.session.list_tools()
        return list(result.tools)


# ==================== MCP 工具 → LangChain 工具 ====================

_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def _sanitize_name(name: str) -> str:
    """LangChain 工具名只允许字母、数字、下划线、连字符"""
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def _map_json_type(prop: dict) -> type:
    t = prop.get("type", "string")
    if isinstance(t, list):  # JSON Schema 允许类型数组，取第一个非 null 类型
        t = next((x for x in t if x != "null"), "string")
    return _TYPE_MAP.get(t, str)


def _build_args_schema(tool_schema: dict) -> type:
    """从 MCP 工具的 inputSchema（JSON Schema）动态生成 Pydantic 模型"""
    from pydantic import BaseModel, Field, create_model

    schema = tool_schema or {}
    props = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    fields: dict[str, tuple[type, Any]] = {}
    for name, prop in props.items():
        desc = prop.get("description", "")
        field_type = _map_json_type(prop)
        if name in required:
            fields[name] = (field_type, Field(..., description=desc))
        else:
            fields[name] = (field_type, Field(prop.get("default", None), description=desc))
    return create_model("ToolArgs", **fields)


def _format_call_result(result: Any) -> str:
    """把 MCP call_tool 的 CallToolResult 转成可读文本"""
    parts: list[str] = []
    for content in result.content:
        ctype = getattr(content, "type", "text")
        if ctype == "text":
            parts.append(str(content.text))
        elif ctype == "image":
            parts.append(f"[图片 {getattr(content, 'mimeType', 'image')}]")
        else:
            parts.append(str(content))
    text = "\n".join(p for p in parts if p)
    if getattr(result, "isError", False):
        return f"[MCP 错误]\n{text or '(无错误详情)'}"
    return text or "(无输出)"


def _make_tool(connection: ServerConnection, server_id: str, mcp_tool: Any) -> BaseTool:
    """把一个 MCP 工具包装成 LangChain StructuredTool"""

    async def _run(**kwargs: Any) -> str:
        if connection.session is None:
            return "[MCP 错误] 服务器连接已关闭"
        try:
            result = await connection.session.call_tool(mcp_tool.name, arguments=kwargs)
        except Exception as e:  # noqa: BLE001 —— 工具调用失败要转成文本返回，不能抛给 Agent
            return f"[MCP 调用失败] {e}"
        return _format_call_result(result)

    tool_name = f"{server_id}__{_sanitize_name(mcp_tool.name)}"
    desc = mcp_tool.description or mcp_tool.name
    return StructuredTool.from_function(
        coroutine=_run,
        name=tool_name,
        description=f"{desc}\n\n（来自 MCP 服务器：{server_id}）",
        args_schema=_build_args_schema(mcp_tool.input_schema),
    )


def _friendly_error(cfg: dict, exc: Exception) -> str:
    """把连接异常转成对用户可操作的提示"""
    msg = str(exc)
    # 鉴权头里的 Token 为空 → 提示先去申请
    auth = (cfg.get("headers") or {}).get("Authorization", "")
    token = auth.removeprefix("Bearer").strip() if auth.startswith("Bearer") else ""
    if auth and not token:
        return "MCD_MCP_TOKEN 未配置，请到 open.mcd.cn 申请后填入 .env"
    if "403" in msg or "401" in msg or "forbidden" in msg.lower():
        return "鉴权失败（403/401）：Token 无效或已过期，请检查 MCD_MCP_TOKEN"
    return msg or type(exc).__name__


async def _connect_server(cfg: dict) -> tuple[ServerConnection, list[BaseTool]]:
    """连接单个服务器并返回 (连接对象, 转换后的工具列表)。

    失败时保证连接资源被清理，避免残留异步任务。
    """
    connection = ServerConnection(cfg)
    try:
        await connection.start()
    except Exception:
        await connection.close()
        raise
    mcp_tools = await connection.list_tools()
    tools = [_make_tool(connection, cfg["id"], t) for t in mcp_tools]
    return connection, tools


# ==================== 对外入口 ====================

async def load_mcp_tools() -> list[BaseTool]:
    """加载所有已启用 MCP 服务器的工具（进程内只加载一次，连接长驻）。

    失败策略：单个服务器失败只跳过它；全部失败返回空列表并记录原因。
    """
    global _mcp_tools, _last_error
    if _mcp_tools is not None:
        return _mcp_tools

    async with _get_lock():
        if _mcp_tools is not None:
            return _mcp_tools

        servers = load_server_configs()
        all_tools: list[BaseTool] = []
        failures: list[str] = []

        for cfg in servers:
            try:
                connection, tools = await _connect_server(cfg)
                _connections.append(connection)
                all_tools.extend(tools)
            except Exception as e:  # noqa: BLE001 —— 单服务器失败不阻断整体
                name = cfg.get("name", cfg.get("id", "?"))
                # 鉴权类失败给出可操作提示
                hint = _friendly_error(cfg, e)
                failures.append(f"{name}: {hint}")

        _last_error = "；".join(failures)
        _mcp_tools = all_tools
        return _mcp_tools


async def shutdown_mcp() -> None:
    """关闭所有 MCP 连接并清空缓存（程序退出前调用，保证优雅退出）"""
    global _mcp_tools, _last_error
    for conn in _connections:
        try:
            await conn.close()
        except Exception:
            pass
    _connections.clear()
    _mcp_tools = None
    _last_error = ""


__all__ = [
    "load_mcp_tools",
    "load_server_configs",
    "get_last_error",
    "reset_mcp_tools",
    "shutdown_mcp",
]
