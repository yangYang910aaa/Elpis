"""提示词管理模块

集中管理 Agent 的系统提示词、few-shot 示例等，避免硬编码在代码里。
所有提示词统一放在 prompts.yaml 中，通过 load_prompt(name) 加载。

未来可以加：
- few_shot：少样本示例，教 Agent 怎么处理特定场景
- prompt_templates：动态提示词模板，根据场景拼接提示词
- 多语言提示词
"""

from pathlib import Path
import yaml


def load_prompt(name: str) -> str:
    """加载指定名称的提示词

    Args:
        name: 提示词名称（对应 prompts.yaml 中的 key）

    Returns:
        提示词文本

    Raises:
        KeyError: 提示词名称不存在时抛出
    """
    prompt_path = Path(__file__).parent / "prompts.yaml"
    with open(prompt_path, encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    if name not in prompts:
        available = ", ".join(prompts.keys())
        raise KeyError(f"提示词 '{name}' 不存在，可用的有: {available}")

    return prompts[name]


def load_system_prompt() -> str:
    """加载系统提示词（便捷方法，等价于 load_prompt('system')）"""
    return load_prompt("system")
