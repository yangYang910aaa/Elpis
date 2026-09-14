"""Agent 核心：基于 LangChain create_agent 的标准实现

使用 LangChain 标准组件：
- ChatOpenAI: LLM 封装
- @tool 装饰器: 工具定义
- create_agent: LangChain 官方推荐的 Agent 构建函数（运行在 LangGraph 之上）
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from langchain.agents import create_agent
from mirage.config import settings
from mirage.tools import ALL_TOOLS
from mirage.prompts import load_system_prompt


def _build_llm() -> ChatOpenAI:
    """构建 LLM 实例"""
    kwargs = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": settings.openai_temperature,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def _build_agent():
    """构建 Agent: LLM + 工具 + 系统提示词，自动循环调用直到完成"""
    llm = _build_llm()
    system_prompt = load_system_prompt()
    return create_agent(llm, tools=ALL_TOOLS, system_prompt=system_prompt)


def _extract_tool_calls(messages: list) -> list[dict]:
    """从消息历史中提取所有工具调用记录（含输入和输出）"""
    tool_calls = []
    # 建立 tool_call_id -> ToolMessage 的映射
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


def run_agent(user_input: str) -> dict:
    """运行 Agent: 处理用户输入，返回最终结果

    Returns:
        {
            "response": str,           # AI 最终文本回复
            "tool_calls": list,        # 所有工具调用记录
            "iterations": int,         # 实际迭代次数（LLM 调用轮数）
            "messages": list,          # 完整消息历史
        }
    """
    agent = _build_agent()

    # recursion_limit 限制最大递归步数，防止无限循环
    # 每轮 Agent 迭代约消耗 2 步（LLM + Tool），所以乘以 2 再加余量
    config = {"recursion_limit": settings.max_agent_iterations * 2 + 5}

    result = agent.invoke(
        {"messages":[HumanMessage(content=user_input)]},
        config=config,
    )

    messages = result["messages"]

    # 提取最终回复：最后一个 AIMessage 的文本内容
    response_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content
            break

    # 统计迭代次数：AIMessage 的数量（每轮 LLM 调用一个 AIMessage）
    iterations = sum(1 for msg in messages if isinstance(msg, AIMessage))

    return {
        "response": response_text,
        "tool_calls": _extract_tool_calls(messages),
        "iterations": iterations,
        "messages": messages,
    }
