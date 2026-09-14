"""命令行入口：终端交互式 Agent"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from mirage.config import settings
from mirage.agent import run_agent

console = Console()


def print_banner():
    """打印欢迎横幅"""
    banner = Text()
    banner.append("🔮 Mirage\n", style="bold cyan")
    banner.append(f"工作目录: {settings.workspace_path}\n", style="dim")
    banner.append(f"模型: {settings.openai_model}\n", style="dim")
    banner.append("输入 'exit' 或 'quit' 退出，输入 'clear' 清空对话\n", style="dim")
    console.print(Panel(banner, border_style="cyan"))


def print_tool_call(call: dict, index: int):
    """打印工具调用信息"""
    name = call.get("name", "unknown")
    tool_input = call.get("input", {})

    # 工具调用标题
    title = Text()
    title.append(f"🔧 工具调用 #{index + 1}: ", style="bold yellow")
    title.append(name, style="bold green")
    console.print(title)

    # 输入参数
    if tool_input:
        for key, value in tool_input.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            console.print(f"   {key}: {val_str}", style="dim")

    # 输出结果
    output = call.get("output", "")
    if output:
        if len(output) > 300:
            output = output[:300] + "..."
        console.print(f"   → {output}", style="italic dim")
    console.print()


def chat_loop():
    """主对话循环"""
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

    conversation_history = []

    while True:
        try:
            user_input = console.input("[bold blue]你:[/bold blue] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n再见！", style="cyan")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            console.print("再见！", style="cyan")
            break
        if user_input.lower() == "clear":
            conversation_history = []
            console.print("对话已清空", style="green")
            continue

        # 运行 Agent
        console.print()
        with console.status("[bold green]Agent 思考中...", spinner="dots"):
            try:
                result = run_agent(user_input)
            except Exception as e:
                console.print(f"[red]出错了: {e}[/red]\n")
                continue

        # 展示工具调用过程
        if result["tool_calls"]:
            console.print(Text("── 工具调用过程 ──", style="bold yellow"))
            for i, call in enumerate(result["tool_calls"]):
                print_tool_call(call, i)

        # 展示最终回复
        console.print(Text("── Agent 回复 ──", style="bold cyan"))
        if result["response"]:
            console.print(Markdown(result["response"]))
        else:
            console.print("[dim](无文本回复)[/dim]")

        # 统计信息
        console.print(
            f"\n[dim]迭代 {result['iterations']} 轮，"
            f"调用 {len(result['tool_calls'])} 次工具[/dim]\n"
        )


def main():
    """CLI 入口"""
    chat_loop()


if __name__ == "__main__":
    main()
