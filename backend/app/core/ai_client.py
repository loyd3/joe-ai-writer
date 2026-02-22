import openai
from app.core.config import get_settings

settings = get_settings()

class AIClient:
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url if settings.openai_base_url else None
        )
        self.model = settings.openai_model
    
    async def chat_completion(self, messages: list, temperature: float = 0.7, **kwargs):
        """通用对话接口"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream_completion(self, messages: list, temperature: float = 0.7):
        """流式对话接口"""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

ai_client = AIClient()