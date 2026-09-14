"""Shell 命令执行工具：带安全检查和超时控制"""

import subprocess
from langchain_core.tools import tool
from mirage.config import settings


@tool
def run_shell_command(command: str, timeout: int = 30) -> str:
    """执行 Shell 命令（如 dir、python、pip、git 等）。用于运行程序、安装依赖、查看系统信息等。

    注意：危险命令会被黑名单拦截。默认需要用户确认。

    Args:
        command: 要执行的 Shell 命令
        timeout: 超时时间（秒），默认 30 秒

    Returns:
        命令的标准输出和标准错误
    """
    # 安全检查 1：黑名单
    for blacklisted in settings.shell_blacklist_commands:
        if blacklisted.lower() in command.lower():
            return f"安全拦截：命令包含黑名单关键字 '{blacklisted}'，已拒绝执行"

    # 安全检查 2：工作目录
    cwd = str(settings.workspace_path)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        output_parts = []
        if result.stdout:
            # 截断过长输出
            stdout = result.stdout
            if len(stdout) > 5000:
                stdout = stdout[:5000] + "\n... (输出过长，已截断)"
            output_parts.append(stdout)
        if result.stderr:
            stderr = result.stderr
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n... (错误输出过长，已截断)"
            output_parts.append(f"[STDERR]\n{stderr}")

        exit_info = f"[退出码: {result.returncode}]"
        output = "\n".join(output_parts) if output_parts else "(无输出)"
        return f"{output}\n{exit_info}"

    except subprocess.TimeoutExpired:
        return f"命令执行超时（{timeout}秒）: {command}"
    except Exception as e:
        return f"命令执行失败: {e}"
