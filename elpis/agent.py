"""Agent 核心：基于 LangChain create_agent 的流式实现（最简版）

用 astream 多模式（messages + values）实现流式：
- messages 流：逐 token 输出 LLM 文本
- values 流：每步更新完整 state，最后一步即最终结果
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.errors import GraphRecursionError
from elpis.config import settings
from elpis.tools import ALL_TOOLS
from elpis.prompts import load_system_prompt


def _build_llm() -> ChatOpenAI:
    """构建 LLM 实例"""
    kwargs = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": settings.openai_temperature,
        "streaming": True,   # 流式模式
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


async def _build_agent():
    """构建 Agent: LLM + 工具（内建 + MCP） + 系统提示词，自动循环调用直到完成"""
    llm = _build_llm()
    system_prompt = load_system_prompt()
    # MCP 工具：加载失败会降级为空列表，不影响 Agent 启动
    from elpis.mcp import load_mcp_tools
    mcp_tools = await load_mcp_tools()
    return create_agent(llm, tools=ALL_TOOLS + mcp_tools, system_prompt=system_prompt)


def _extract_tool_calls(messages: list) -> list[dict]:
    """从消息历史中提取所有工具调用记录（含输入和输出）"""
    tool_calls = []
    tool_results = {}
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                result_msg = tool_results.get(tc["id"])
                tool_calls.append({
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["args"],
                    "output": result_msg.content if result_msg else "(无结果)",
                })
    return tool_calls


def _prepare_messages(user_input: str, history: list | None = None, max_history: int = 30) -> list:
    """拼接历史消息与新的用户输入，并做滑动窗口裁剪（按条数）"""
    messages = list(history) if history else []
    if len(messages) > max_history:
        start = 0
        for idx in range(len(messages) - 1, -1, -1):
            if isinstance(messages[idx], HumanMessage) and len(messages) - idx <= max_history:
                start = idx
                break
        messages = messages[start:]
    messages.append(HumanMessage(content=user_input))
    return messages


async def run_agent_stream(user_input: str, history: list | None = None):
    """流式运行 Agent。

    事件类型：
        {"type": "token", "content": "..."}    # LLM 输出的一个 token
        {"type": "done",  "response": "...",    # 结束，返回完整结果
         "tool_calls": [...], "iterations": N, "messages": [...]}
        {"type": "error", "message": "..."}     # 异常中断
    """
    agent = await _build_agent()
    config = {"recursion_limit": settings.max_agent_iterations * 2 + 5}
    messages = _prepare_messages(user_input, history)

    final_state = None

    try:
        async for mode, payload in agent.astream(
            {"messages": messages},
            config=config,
            stream_mode=["messages", "values"],   # messages 逐 token，values 给完整 state
        ):
            if mode == "messages":
                chunk, _ = payload
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield {"type": "token", "content": str(chunk.content)}
            elif mode == "values":
                final_state = payload                # 每步都更新，最后一步即最终 state
    except GraphRecursionError:
        yield {"type": "error", "message": f"达到最大迭代次数（{settings.max_agent_iterations}），任务未完成。"}
        return
    except Exception as e:
        yield {"type": "error", "message": f"发生未知错误：{e}"}
        return

    # 防御：极端情况下 values 流没 yield 过
    if final_state is None:
        yield {"type": "error", "message": "Agent 执行结束但未获得最终状态。"}
        return

    msgs = final_state["messages"]                  # 完整、正确的消息历史

    # 最终回复：取最后一条有内容的 AIMessage（与原版逻辑一致）
    response_text = ""
    for msg in reversed(msgs):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = str(msg.content)
            break

    yield {
        "type": "done",
        "response": response_text,
        "tool_calls": _extract_tool_calls(msgs),
        "iterations": sum(1 for m in msgs if isinstance(m, AIMessage)),
        "messages": msgs,
    }
