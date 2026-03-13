"""
系统配置 API - 管理 AI 模型配置、系统设置等
使用 system_configs 表存储配置（键值对形式）
"""

from fastapi import APIRouter, HTTPException, Depends
from app.core.config import get_settings
from pydantic import BaseModel
from typing import Literal, Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import SystemConfig
from app.api.auth import get_current_user
import json

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
        models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o"],
    ),
    AIProviderInfo(
        id="deepseek",
        name="DeepSeek",
        description="DeepSeek AI，中文表现优秀",
        models=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
    ),
    AIProviderInfo(
        id="siliconflow",
        name="SiliconFlow",
        description="SiliconFlow 模型平台，支持多种开源模型",
        models=[
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct",
        ],
    ),
    AIProviderInfo(
        id="custom",
        name="自定义 API",
        description="兼容 OpenAI API 格式的自定义端点",
        models=["custom"],
    ),
]


def _get_db_config(db: Session, key: str, default=None):
    """从数据库获取配置值"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if config and config.config_value:
        try:
            return json.loads(config.config_value).get("value", default)
        except:
            return config.config_value
    return default


def _set_db_config(db: Session, key: str, value):
    """设置数据库配置值"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    config_json = json.dumps({"value": value})
    
    if config:
        config.config_value = config_json
        print(f"[SystemAPI] 更新配置 {key}: {str(value)[:30] if value else 'None'}...")
    else:
        config = SystemConfig(config_key=key, config_value=config_json)
        db.add(config)
        print(f"[SystemAPI] 新建配置 {key}: {str(value)[:30] if value else 'None'}...")
    db.commit()


@router.get("/ai-config", response_model=CurrentAIConfig)
def get_ai_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取当前 AI 配置信息（优先从数据库 system_configs 读取）"""
    # 优先从数据库读取
    db_provider = _get_db_config(db, "ai_provider")
    db_model = _get_db_config(db, "ai_model")
    
    if db_provider:
        return CurrentAIConfig(
            provider=db_provider,
            model=db_model or "deepseek-chat",
            available_providers=AVAILABLE_PROVIDERS
        )
    
    # 回退到配置文件
    settings = get_settings()
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
async def test_ai_connection(
    config: AIConfigUpdate,
    db: Session = Depends(get_db)
):
    """测试 AI 连接"""

    try:
        # 获取 base_url 和 model
        base_url_map = {
            "openai": config.base_url or "https://api.openai.com/v1",
            "deepseek": config.base_url or "https://api.deepseek.com/v1",
            "siliconflow": config.base_url or "https://api.siliconflow.cn/v1",
            "custom": config.base_url or ""
        }
        
        base_url = base_url_map.get(config.provider, "")
        api_key = config.api_key or ""
        
        # 先测试 HTTP 连接
        import httpx
        import ssl
        import os
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with httpx.AsyncClient(
                timeout=10.0,
                verify=ssl_context,
                follow_redirects=True
            ) as client:
                # 测试 API 地址是否可达
                test_url = f"{base_url}/models" if base_url else ""
                if test_url:
                    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    response = await client.get(test_url, headers=headers)
                    
                    if response.status_code == 401:
                        http_status = "可达 (需要有效 API Key)"
                    elif response.status_code == 200:
                        http_status = "可达且认证成功"
                    else:
                        http_status = f"状态码: {response.status_code}"
                else:
                    http_status = "未配置 base_url"
        except Exception as e:
            http_status = f"连接失败: {str(e)}"
        
        # 打印诊断信息
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        
        return {
            "success": "失败" not in http_status and "未配置" not in http_status,
            "message": f"HTTP 连接测试: {http_status}",
            "diagnostics": {
                "base_url": base_url,
                "api_key_prefix": api_key[:10] + "..." if api_key else "未设置",
                "http_proxy": http_proxy,
                "https_proxy": https_proxy,
            }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "diagnostics": {}
        }


@router.get("/network-test")
async def network_test():
    """测试网络连接"""
    import httpx
    import ssl
    import socket
    import os
    
    results = {
        "dns_resolution": {},
        "http_connection": {},
        "ssl_connection": {},
        "proxy_settings": {},
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    
    # 检查代理设置
    results["proxy_settings"] = {
        "HTTP_PROXY": os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'),
        "HTTPS_PROXY": os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'),
    }
    
    # 测试 DNS 解析
    hosts_to_test = [
        ("api.deepseek.com", "DeepSeek API"),
        ("api.openai.com", "OpenAI API"),
        ("www.google.com", "Google"),
        ("www.baidu.com", "Baidu"),
    ]
    
    for host, name in hosts_to_test:
        try:
            ip = socket.gethostbyname(host)
            results["dns_resolution"][name] = {"status": "success", "ip": ip}
        except Exception as e:
            results["dns_resolution"][name] = {"status": "failed", "error": str(e)}
    
    # 测试 HTTP 连接 (禁用 SSL)
    urls_to_test = [
        ("https://api.deepseek.com/v1/models", "DeepSeek API"),
        ("https://www.baidu.com", "Baidu HTTPS"),
    ]
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    for url, name in urls_to_test:
        try:
            async with httpx.AsyncClient(
                verify=ssl_context,
                timeout=10.0,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                results["http_connection"][name] = {
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "url": url
                }
        except Exception as e:
            results["http_connection"][name] = {
                "status": "failed",
                "error": str(e),
                "url": url
            }
    
    # 测试 SSL 连接 (启用 SSL 验证)
    for url, name in urls_to_test:
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                results["ssl_connection"][name] = {
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "ssl_verify": True
                }
        except Exception as e:
            results["ssl_connection"][name] = {
                "status": "failed",
                "error": str(e),
                "ssl_verify": True
            }
    
    # 判断整体网络状态
    has_success = any(
        r.get("status") == "success" 
        for r in results["dns_resolution"].values()
    )
    
    return {
        "success": has_success,
        "message": "网络测试完成，请查看详细信息" if has_success else "网络连接异常",
        "results": results
    }


@router.get("/health")
def health_check():
    """系统健康检查"""
    settings = get_settings()
    return {
        "status": "ok",
        "version": "1.1.0",
        "features": ["multi-provider-ai", "memory-system", "streaming", "config-persistence"],
        "default_provider": settings.ai_provider,
    }


# ========== 用户 AI 配置管理 ==========
@router.get("/user-ai-config")
def get_user_ai_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取用户保存的 AI 配置（从 system_configs 表优先）"""
    # 从数据库读取
    provider = _get_db_config(db, "ai_provider")
    model = _get_db_config(db, "ai_model")
    api_key = _get_db_config(db, "ai_api_key")
    base_url = _get_db_config(db, "ai_base_url")
    temperature = _get_db_config(db, "ai_temperature")
    max_tokens = _get_db_config(db, "ai_max_tokens")
    
    if provider:
        return {
            "provider": provider,
            "model": model,
            "api_key": api_key[:10] + "..." if api_key else None,  # 脱敏显示
            "base_url": base_url,
            "temperature": float(temperature) if temperature else 0.7,
            "max_tokens": int(max_tokens) if max_tokens else 4096,
            "source": "database"
        }
    
    # 回退到配置文件
    settings = get_settings()
    return {
        "provider": settings.ai_provider,
        "model": settings.deepseek_model if settings.ai_provider == "deepseek" else 
                 settings.openai_model if settings.ai_provider == "openai" else
                 settings.siliconflow_model if settings.ai_provider == "siliconflow" else
                 settings.custom_model,
        "temperature": settings.ai_temperature,
        "max_tokens": settings.ai_max_tokens,
        "source": "env",
        "message": "尚未保存配置到数据库，使用的是环境变量默认值"
    }


@router.post("/user-ai-config")
def save_user_ai_config(
    config: AIConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """保存用户 AI 配置到 system_configs 表"""
    from app.core.ai_client import refresh_ai_client
    
    try:
        # 获取默认值
        base_url_map = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "custom": ""
        }
        
        default_models = {
            "openai": "gpt-4",
            "deepseek": "deepseek-chat",
            "siliconflow": "deepseek-ai/DeepSeek-V3",
            "custom": "custom"
        }
        
        # 保存到 system_configs 表
        print(f"[SystemAPI] 保存 AI 配置: provider={config.provider}, model={config.model}")
        print(f"[SystemAPI] API Key: {'已提供' if config.api_key else '未提供'}")
        
        _set_db_config(db, "ai_provider", config.provider)
        _set_db_config(db, "ai_model", config.model or default_models.get(config.provider, "custom"))
        _set_db_config(db, "ai_api_key", config.api_key)
        _set_db_config(db, "ai_base_url", config.base_url or base_url_map.get(config.provider, ""))
        _set_db_config(db, "ai_temperature", config.temperature or 0.7)
        _set_db_config(db, "ai_max_tokens", 4096)
        
        print(f"[SystemAPI] 配置已保存到数据库")
        
        # 刷新 AI 客户端（使用新配置）
        refresh_ai_client(db=db)
        
        return {
            "success": True,
            "message": f"AI 配置已保存到数据库: {config.provider} - {config.model}",
            "provider": config.provider,
            "model": config.model
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置更新失败: {str(e)}")


@router.delete("/user-ai-config")
def delete_user_ai_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除用户的 AI 数据库配置，回退到环境变量"""
    from app.core.ai_client import refresh_ai_client
    
    try:
        # 删除 system_configs 中的 AI 配置
        keys = ["ai_provider", "ai_model", "ai_api_key", "ai_base_url", "ai_temperature", "ai_max_tokens"]
        for key in keys:
            config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if config:
                db.delete(config)
        db.commit()
        
        # 刷新 AI 客户端（回退到环境变量）
        refresh_ai_client()
        
        return {
            "success": True,
            "message": "已删除数据库配置，将使用环境变量配置"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"删除配置失败: {str(e)}")
