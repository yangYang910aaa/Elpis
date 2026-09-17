"""MCP 扩展模块

把外部 MCP 服务器（如麦当劳官方 MCP）的工具接入 Elpis Agent。

使用：
    from elpis.mcp import load_mcp_tools

    tools = await load_mcp_tools()   # 返回 LangChain BaseTool 列表

服务器清单在 servers.yaml 中声明，敏感信息（如 Token）通过 .env
环境变量注入（servers.yaml 中用 ${ENV_VAR} 占位）。
"""

from elpis.mcp.manager import (
    get_last_error,
    load_mcp_tools,
    load_server_configs,
    reset_mcp_tools,
    shutdown_mcp,
)

__all__ = [
    "load_mcp_tools",
    "load_server_configs",
    "get_last_error",
    "reset_mcp_tools",
    "shutdown_mcp",
]
