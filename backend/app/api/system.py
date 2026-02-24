"""
系统配置 API - 管理 AI 模型配置、系统设置等
"""
from fastapi import APIRouter, HTTPException
from app.core.config import get_settings
from pydantic import BaseModel
from typing import Literal, Optional

router = APIRouter(prefix="/api/system", tags=["system"])

class AIProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    models: list[str]

class CurrentAIConfig(BaseModel):
    provider: str
    model: str
    available_providers: list[AIProviderInfo]

class AIConfigUpdate(BaseModel):
    provider: Literal["openai", "deepseek", "siliconflow", "custom"]
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None

# 支持的 AI 提供商配置
AVAILABLE_PROVIDERS = [
    AIProviderInfo(
        id="openai",
        name="OpenAI",
        description="OpenAI 官方 API",
        models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o"]
    ),
    AIProviderInfo(
        id="deepseek",
        name="DeepSeek",
        description="DeepSeek AI，中文表现优秀",
        models=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
    ),
    AIProviderInfo(
        id="siliconflow",
        name="SiliconFlow",
        description="SiliconFlow 模型平台，支持多种开源模型",
        models=[
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct"
        ]
    ),
    AIProviderInfo(
        id="custom",
        name="自定义 API",
        description="兼容 OpenAI API 格式的自定义端点",
        models=["custom"]
    )
]

@router.get("/ai-config", response_model=CurrentAIConfig)
def get_ai_config():
    """获取当前 AI 配置信息"""
    settings = get_settings()
    
    # 根据当前 provider 返回对应的 model
    if settings.ai_provider == "openai":
        current_model = settings.openai_model
    elif settings.ai_provider == "deepseek":
        current_model = settings.deepseek_model
    elif settings.ai_provider == "siliconflow":
        current_model = settings.siliconflow_model
    else:
        current_model = settings.custom_model
    
    return CurrentAIConfig(
        provider=settings.ai_provider,
        model=current_model,
        available_providers=AVAILABLE_PROVIDERS
    )

@router.get("/ai-config/providers")
def get_available_providers():
    """获取所有可用的 AI 提供商"""
    return AVAILABLE_PROVIDERS

@router.post("/ai-config/test")
async def test_ai_connection(config: AIConfigUpdate):
    """测试 AI 连接"""
    from app.core.ai_client import AIClient
    
    try:
        # 临时创建客户端测试连接
        settings = get_settings()
        
        # 构建测试配置
        test_settings = {
            "ai_provider": config.provider,
            "openai_api_key": settings.openai_api_key,
            "openai_base_url": settings.openai_base_url,
            "openai_model": settings.openai_model,
            "deepseek_api_key": settings.deepseek_api_key,
            "deepseek_base_url": settings.deepseek_base_url,
            "deepseek_model": settings.deepseek_model,
            "siliconflow_api_key": settings.siliconflow_api_key,
            "siliconflow_base_url": settings.siliconflow_base_url,
            "siliconflow_model": settings.siliconflow_model,
            "custom_api_key": settings.custom_api_key,
            "custom_base_url": settings.custom_base_url,
            "custom_model": settings.custom_model,
            "ai_temperature": config.temperature or settings.ai_temperature,
            "ai_max_tokens": settings.ai_max_tokens,
        }
        
        # 如果提供了新的配置，覆盖原有配置
        if config.api_key:
            if config.provider == "openai":
                test_settings["openai_api_key"] = config.api_key
            elif config.provider == "deepseek":
                test_settings["deepseek_api_key"] = config.api_key
            elif config.provider == "siliconflow":
                test_settings["siliconflow_api_key"] = config.api_key
            else:
                test_settings["custom_api_key"] = config.api_key
        
        if config.base_url:
            if config.provider == "openai":
                test_settings["openai_base_url"] = config.base_url
            elif config.provider == "deepseek":
                test_settings["deepseek_base_url"] = config.base_url
            elif config.provider == "siliconflow":
                test_settings["siliconflow_base_url"] = config.base_url
            else:
                test_settings["custom_base_url"] = config.base_url
        
        if config.model:
            if config.provider == "openai":
                test_settings["openai_model"] = config.model
            elif config.provider == "deepseek":
                test_settings["deepseek_model"] = config.model
            elif config.provider == "siliconflow":
                test_settings["siliconflow_model"] = config.model
            else:
                test_settings["custom_model"] = config.model
        
        # 创建临时配置类
        class TempSettings:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        temp_client = AIClient(TempSettings(**test_settings))
        
        # 测试简单对话
        response = await temp_client.chat_completion(
            messages=[{"role": "user", "content": "你好，请回复 '连接成功'"}],
            temperature=0.3,
            max_tokens=50
        )
        
        return {
            "success": True,
            "message": "连接成功",
            "response": response[:100]  # 只返回前100个字符
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }

@router.get("/health")
def health_check():
    """系统健康检查"""
    return {
        "status": "ok",
        "version": "1.1.0",
        "features": ["multi-provider-ai", "memory-system", "streaming"]
    }
