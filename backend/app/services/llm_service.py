"""
LLM 服务 - 统一封装 AI 调用接口
兼容旧代码调用方式
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.ai_client import ai_client


class LLMService:
    """LLM 服务 - 统一 AI 调用封装"""
    
    @staticmethod
    async def chat(
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        发送聊天请求到 AI
        
        Args:
            messages: 消息列表
            model: 模型名称（可选，使用默认配置）
            temperature: 温度参数
            stream: 是否流式返回
            
        Returns:
            AI 回复文本
        """
        if stream:
            chunks = []
            async for chunk in ai_client.stream_completion(messages):
                chunks.append(chunk)
            return "".join(chunks)
        else:
            return await ai_client.chat_completion(messages)
    
    @staticmethod
    async def chat_stream(
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        流式发送聊天请求到 AI
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            
        Yields:
            AI 回复文本片段
        """
        async for chunk in ai_client.stream_completion(messages):
            yield chunk
    
    @staticmethod
    async def generate_text(
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        根据提示词生成文本
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model: 模型名称
            temperature: 温度参数
            
        Returns:
            生成的文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await ai_client.chat_completion(messages)
    
    @staticmethod
    async def generate_json(
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成 JSON 格式的回复
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model: 模型名称
            
        Returns:
            解析后的 JSON 字典
        """
        import json
        
        # 添加 JSON 格式要求
        json_system_prompt = system_prompt or ""
        json_system_prompt += "\n\n重要：你的回复必须是合法的 JSON 格式，不要包含 markdown 代码块标记或其他额外文本。"
        
        messages = [
            {"role": "system", "content": json_system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await ai_client.chat_completion(messages)
        
        # 尝试解析 JSON
        try:
            # 移除可能的 markdown 代码块
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"无法解析 JSON 响应: {str(e)}\n原始响应: {response}")

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """实例方法：供自动写作等模块调用"""
        messages = [{"role": "user", "content": prompt}]
        return await ai_client.chat_completion(
            messages, max_tokens=max_tokens
        )

    async def generate_stream(
        self, prompt: str, max_tokens: Optional[int] = None
    ):
        """流式生成文本"""
        messages = [{"role": "user", "content": prompt}]
        async for chunk in ai_client.stream_completion(
            messages, max_tokens=max_tokens
        ):
            yield chunk


# 创建单例实例
llm_service = LLMService()
