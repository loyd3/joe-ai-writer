"""
统一 AI 客户端 - 支持多模型提供商
支持: OpenAI, DeepSeek, SiliconFlow, 自定义 API
"""

import openai
from app.core.config import get_settings, Settings
from typing import AsyncGenerator, Optional


class AIClient:
    """统一的 AI 客户端，支持多个模型提供商"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client = None
        self._init_client()

    def _init_client(self):
        """根据配置的 provider 初始化对应的客户端"""
        provider = self.settings.ai_provider

        if provider == "openai":
            api_key = self.settings.openai_api_key
            base_url = self.settings.openai_base_url or "https://api.openai.com/v1"
            self.model = self.settings.openai_model or "gpt-4"
        elif provider == "deepseek":
            api_key = self.settings.deepseek_api_key
            base_url = self.settings.deepseek_base_url or "https://api.deepseek.com/v1"
            self.model = self.settings.deepseek_model or "deepseek-chat"
        elif provider == "siliconflow":
            api_key = self.settings.siliconflow_api_key
            base_url = self.settings.siliconflow_base_url or "https://api.siliconflow.cn/v1"
            self.model = self.settings.siliconflow_model or "deepseek-ai/DeepSeek-V3"
        elif provider == "custom":
            api_key = self.settings.custom_api_key
            base_url = self.settings.custom_base_url
            self.model = self.settings.custom_model
            if not base_url:
                raise ValueError("Custom provider requires custom_base_url")
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

        if not api_key:
            raise ValueError(f"API key not configured for provider: {provider}")

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

        print(f"[AIClient] Initialized with provider: {provider}, model: {self.model}")

    @property
    def client(self):
        if not self._client:
            self._init_client()
        return self._client

    async def chat_completion(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = 60.0,
        **kwargs,
    ) -> str:
        """通用对话接口（非流式）"""
        import asyncio
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.settings.ai_temperature,
                    max_tokens=max_tokens or self.settings.ai_max_tokens,
                    **kwargs,
                ),
                timeout=timeout
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            raise Exception("AI 请求超时，请稍后重试")

    async def stream_completion(
        self, messages: list, temperature: Optional[float] = None, max_tokens: Optional[int] = None,
        timeout: float = 120.0
    ) -> AsyncGenerator[str, None]:
        """流式对话接口，带超时保护"""
        import asyncio
        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.settings.ai_temperature,
                    max_tokens=max_tokens or self.settings.ai_max_tokens,
                    stream=True,
                ),
                timeout=30.0  # 连接超时
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except asyncio.TimeoutError:
            raise Exception("AI 连接超时，请稍后重试")


# 全局客户端实例（延迟初始化）
_ai_client_instance: AIClient | None = None


def get_ai_client() -> AIClient:
    """获取 AI 客户端实例（延迟初始化）"""
    global _ai_client_instance
    if _ai_client_instance is None:
        _ai_client_instance = AIClient()
    return _ai_client_instance


# 向后兼容 - 使用属性访问器实现真正的延迟加载
class _LazyAIClient:
    """延迟加载的 AI 客户端代理"""

    _client: AIClient | None = None

    def _get_client(self):
        if self._client is None:
            self._client = get_ai_client()
        return self._client

    def __getattr__(self, name):
        return getattr(self._get_client(), name)

    async def chat_completion(self, *args, **kwargs):
        return await self._get_client().chat_completion(*args, **kwargs)

    async def stream_completion(self, *args, **kwargs):
        async for chunk in self._get_client().stream_completion(*args, **kwargs):
            yield chunk


ai_client = _LazyAIClient()
