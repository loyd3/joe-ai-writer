from pathlib import Path

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal

# 项目根目录（backend 的上级），便于加载根目录 .env（start.py 场景）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Joe AI Writer"
    debug: bool = True

    # Database - MySQL 配置（默认使用本地 MySQL）
    database_url: str = "mysql+pymysql://root:password@localhost:3306/aiwriter?charset=utf8mb4"
    
    # MySQL 连接池配置
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600

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

    # CORS 允许的来源（逗号分隔，空则用默认开发列表）
    cors_origins: str = ""

    class Config:
        # 优先读项目根目录 .env，否则读当前目录 .env（兼容直接 cd backend 启动）
        env_file = (
            _PROJECT_ROOT / ".env"
            if (_PROJECT_ROOT / ".env").exists()
            else ".env"
        )


@lru_cache()
def get_settings():
    return Settings()
