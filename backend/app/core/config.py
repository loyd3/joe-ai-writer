from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Joe AI Writer"
    debug: bool = True
    
    # Database
    database_url: str = "sqlite:///./joe_writer.db"
    
    # AI Configuration
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()