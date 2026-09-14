"""提示词管理模块

集中管理 Agent 的系统提示词、技能提示词、输出模板等。
所有提示词统一使用 Markdown 格式（.md），放在本目录下。
通过 load_prompt(name) 按文件名加载，支持子目录。

目录结构示例：
    prompts/
    ├── __init__.py
    ├── system_prompt.md        # 核心系统提示词
    ├── welcome.md               # 欢迎语
    └── templates/               # 输出模板
        ├── report.md
        └── email.md

加载方式：
    load_prompt("system_prompt")      # 加载 system_prompt.md
    load_prompt("templates/report")   # 加载 templates/report.md
"""

from pathlib import Path


def _scan_prompts() -> dict[str, str]:
    """扫描 prompts 目录下所有 .md 文件，返回 {name: content} 字典"""
    prompts_dir = Path(__file__).parent
    prompts = {}

    for md_file in prompts_dir.rglob("*.md"):
        # 计算相对于 prompts 目录的路径，去掉 .md 后缀作为 key
        rel_path = md_file.relative_to(prompts_dir)
        name = str(rel_path.with_suffix(""))
        # Windows 下路径分隔符统一为 /
        name = name.replace("\\", "/")
        prompts[name] = md_file.read_text(encoding="utf-8")

    return prompts


def load_prompt(name: str) -> str:
    """加载指定名称的提示词

    Args:
        name: 提示词名称，对应文件名（不带 .md 后缀），
              子目录下的文件用 "子目录/文件名" 格式

    Returns:
        提示词文本（Markdown 格式）

    Raises:
        KeyError: 提示词名称不存在时抛出
    """
    prompts = _scan_prompts()

    if name not in prompts:
        available = "\n  - ".join(sorted(prompts.keys()))
        raise KeyError(f"提示词 '{name}' 不存在，可用的有:\n  - {available}")

    return prompts[name]


def load_system_prompt() -> str:
    """加载系统提示词（便捷方法，等价于 load_prompt('system_prompt')）"""
    return load_prompt("system_prompt")


def list_prompts() -> list[str]:
    """列出所有可用的提示词名称"""
    return sorted(_scan_prompts().keys())
