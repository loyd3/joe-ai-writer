from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    app_name: str = "Joe AI Writer"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./joe_writer.db"

    # AI Provider Configuration (支持多个大模型)
    ai_provider: Literal["openai", "deepseek", "siliconflow", "custom"] = "deepseek"

    # OpenAI 配置
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"

    # DeepSeek 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # SiliconFlow 配置
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "deepseek-ai/DeepSeek-V3"

    # 自定义 API 配置
    custom_api_key: str = ""
    custom_base_url: str = ""
    custom_model: str = ""

    # AI 参数
    ai_temperature: float = 0.7
    ai_max_tokens: int = 4096

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
