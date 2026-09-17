"""命令行入口：终端交互式 Agent"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.status import Status
from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style

from elpis.config import settings
from elpis.agent import run_agent_stream
from elpis.tools import ALL_TOOLS

console = Console()


# ============= 斜杠命令定义 =============
COMMANDS = {
    "/help": "显示所有可用命令",
    "/model": "查看或切换模型,用法:/model 模型名称",
    "/clear": "清空当前对话历史",
    "/tools": "显示当前可用工具",
    "/exit": "退出程序",
}
COMMAND_NAMES = list(COMMANDS.keys())


class SlashCompleter(Completer):
    """输入/时, 弹出斜杠命令候选"""
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            for cmd in COMMAND_NAMES:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text), display_meta=COMMANDS.get(cmd, "未知命令"))


# ============= 展示相关 =============
def print_banner():
    """打印欢迎横幅（简洁文字版）"""
    banner = Text()
    banner.append("你好！我是✨ Elpis，有什么可以帮您？\n", style="bold cyan")
    banner.append(f"工作目录: {settings.workspace_path}\n", style="dim")
    banner.append(f"模型: {settings.openai_model}\n", style="dim")
    banner.append("输入 /help 查看命令，输入 /exit 退出程序", style="dim")
    console.print(Panel(banner, border_style="cyan"))

def print_tool_call(call: dict, index: int):
    """模型调用了工具之后,打印工具调用信息"""
    name = call.get("name", "unknown")
    tool_input = call.get("input", {})

    title = Text()
    title.append(f"🔧 工具调用 #{index + 1}: ", style="bold yellow")
    title.append(name, style="bold green")
    console.print(title)

    if tool_input:
        for key, value in tool_input.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            console.print(f"   {key}: {val_str}", style="dim")

    output = call.get("output", "")
    if output:
        if len(output) > 300:
            output = output[:300] + "..."
        console.print(f"   → {output}", style="italic dim")
    console.print()


# ============= 命令处理 =============
def handle_command(user_input: str, history: list):
    """执行斜杠命令。返回(history, should_exit)"""
    parts = user_input.split(maxsplit=1)
    name = parts[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    if name == "/exit":
        console.print("再见!", style="cyan")
        return history, True

    if name == "/clear":
        console.print("对话已清空", style="green")
        return [], False

    if name == "/help":
        console.print(Text("----可用命令----"), style="bold cyan")
        for cmd, desc in COMMANDS.items():
            console.print(f" [bold green]{cmd}[/bold green]  [dim]{desc}[/dim]")
        return history, False

    if name == "/model":
        if arg:
            settings.openai_model = arg
            console.print(f"已切换到模型: {settings.openai_model}", style="bold cyan")
            return history, False
        else:
            console.print(f"当前模型: {settings.openai_model}", style="bold cyan")
            return history, False

    if name == "/tools":
        console.print(Text("----可用工具----"), style="bold cyan")
        for tool in ALL_TOOLS:
            desc = (tool.description or "").strip().splitlines()[0]
            console.print(f" [bold green]{tool.name}[/bold green]  [dim]{desc[:40]}[/dim]")
        return history, False

    return history, False


async def chat_loop():
    """主对话循环（异步流式版）"""
    print_banner()

    # 检查 API key
    if not settings.openai_api_key:
        console.print(
            Panel(
                "[bold red]未配置 OPENAI_API_KEY[/bold red]\n\n"
                "请在项目根目录 .env 文件中添加：\n"
                "OPENAI_API_KEY=你的API密钥\n\n"
                "可以参考 .env.example 文件",
                border_style="red",
            )
        )
        return

    conversation_history = []  # 多轮对话历史

    # 深色菜单配色
    style = Style.from_dict({
        "completion-menu": "bg:#2D2D2D border:#A3D5E8",
        "completion-menu.completion": "fg:#D0D0D0",
        "completion-menu.completion.current": "bg:#A3D5E8 fg:#1A1B1C bold",
        "completion-menu.meta": "fg:#8A8A8A",
        "completion-menu.meta.completion.current": "fg:#4A4A4A",
    })
    session = PromptSession(
        completer=SlashCompleter(),
        style=style,
        complete_while_typing=True,
    )

    while True:
        try:
            user_input = await session.prompt_async(HTML("<b><yellow>你:</yellow></b>"))
            user_input = user_input.strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n再见！", style="cyan")
            break

        if not user_input:
            continue

        # 斜杠命令:本地处理,不发给Agent
        if user_input.startswith("/"):
            conversation_history, should_exit = handle_command(user_input, conversation_history)
            if should_exit:
                break
            continue

        # 普通输入: 流式发给Agent
        console.print()
        console.print(Text("── Agent 回复 ──", style="bold cyan"))

        token_count = 0
        final_result = None
        error_msg = None

        # 手动控制 Status：第一个 token 到来前显示转圈，
        # 第一个 token 到来后停止（Rich 的 Live 与不换行流式打印有冲突，会吞掉输出）
        status = Status("[bold green]Agent 思考中...", console=console, spinner="dots")
        status.start()
        first_token = True

        try:
            async for event in run_agent_stream(user_input, history=conversation_history):
                etype = event["type"]

                if etype == "token":
                    if first_token:
                        status.stop()
                        first_token = False
                    # 逐 token 实时打印，不换行
                    console.print(event["content"], end="")
                    token_count += 1

                elif etype == "done":
                    final_result = event

                elif etype == "error":
                    error_msg = event["message"]

        except Exception as e:
            error_msg = f"出错了: {e}"
        finally:
            # 确保 Status 被停止（纯工具调用无 token 输出、或异常时 first_token 仍为 True）
            if first_token:
                status.stop()

        # token 打印用了 end=""，这里补换行
        if token_count > 0:
            console.print()

        # 错误提示
        if error_msg:
            console.print(f"\n[red]{error_msg}[/red]\n")
            continue

        # 保存本轮消息历史，供下一轮使用
        if final_result:
            conversation_history = list(final_result["messages"])

            # 展示工具调用过程
            if final_result["tool_calls"]:
                console.print()
                console.print(Text("── 工具调用过程 ──", style="bold yellow"))
                for i, call in enumerate(final_result["tool_calls"]):
                    print_tool_call(call, i)

            # 统计信息
            console.print(
                f"\n[dim]迭代 {final_result['iterations']} 轮，"
                f"调用 {len(final_result['tool_calls'])} 次工具，"
                f"输出 {token_count} 个 token[/dim]\n"
            )
        else:
            console.print("\n[dim](无回复)[/dim]\n")


def main():
    """CLI 入口"""
    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
