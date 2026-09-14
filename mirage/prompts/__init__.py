"""提示词管理模块

集中管理 Agent 的系统提示词、few-shot 示例等，避免硬编码在代码里。

未来可以加：
- system_prompt.txt: 系统提示词（Agent 的角色、能力、行为规范）
- few_shot/：少样本示例，教 Agent 怎么处理特定场景
- prompt_templates.py：动态提示词模板，根据场景拼接提示词
"""

from pathlib import Path


def load_system_prompt() -> str:
    """加载系统提示词文本"""
    prompt_path = Path(__file__).parent / "system_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")
