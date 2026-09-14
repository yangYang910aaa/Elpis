"""配置管理：从环境变量和 .env 文件加载配置"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent 全局配置"""
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # ===== LLM API（OpenAI 兼容，支持硅基流动等第三方端点）=====
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = ""  
    openai_temperature: float = 0.7

    # ===== Agent 行为 =====
    max_agent_iterations: int = 20
    agent_workspace: str = ""

    # ===== 安全 =====
    require_confirmation_for_shell: bool = True
    shell_blacklist: str = "rm -rf /,format,mkfs,dd if="

    @property
    def workspace_path(self) -> Path:
        """获取 Agent 工作目录，未配置则使用当前目录"""
        if self.agent_workspace:
            return Path(self.agent_workspace).resolve()
        return Path.cwd()

    @property
    def shell_blacklist_commands(self) -> list[str]:
        """解析 Shell 黑名单为列表"""
        return [cmd.strip() for cmd in self.shell_blacklist.split(",") if cmd.strip()]


# 全局单例
settings = Settings()
