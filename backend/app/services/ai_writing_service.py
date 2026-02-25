from typing import Optional, AsyncGenerator
from sqlalchemy.orm import Session
from app.core.ai_client import ai_client
from app.services.ai_memory_service import AIMemoryService
from app.schemas.schemas import AIRequest, ChatMessage
from app.models.models import AIInteraction

class AIWritingService:
    """AI 写作服务 - 处理各种写作相关的 AI 交互"""
    
    SYSTEM_PROMPT = """你是一位专业的写作助手，具备以下能力：
1. 根据上下文理解文章的整体结构和目标
2. 提供有针对性的写作建议
3. 帮助润色和修改文本
4. 保持对角色设定、故事线、大纲的记忆一致性
5. 尊重用户的写作风格和意图

在回复时，请注意：
- 保持与已有内容的风格一致性
- 尊重已有的角色设定和世界观
- 如果建议修改，说明理由
- 可以提出建设性的问题帮助用户思考"""

    @staticmethod
    def _build_messages(
        action: str,
        content: str,
        memory_context: str,
        selected_text: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> list:
        """构建 AI 对话消息"""
        messages = [
            {"role": "system", "content": AIWritingService.SYSTEM_PROMPT}
        ]
        
        # 添加记忆上下文
        if memory_context:
            messages.append({
                "role": "system", 
                "content": f"以下是项目的背景信息，请在回复时参考：\n{memory_context}"
            })
        
        # 添加当前文档内容
        messages.append({
            "role": "user",
            "content": f"当前文档内容：\n{content}"
        })
        
        # 根据操作类型构建用户请求
        action_prompts = {
            'guide': "请阅读以上内容，给出具体的写作指导建议。",
            'revise': f"请修改以下文本：\n{selected_text}\n\n修改要求：{instruction or '提升表达质量，保持原意'}",
            'polish': f"请润色以下文本，使其更加流畅自然：\n{selected_text}",
            'continue': "请根据已有内容，合理地续写下一段。",
            'brainstorm': f"请围绕以下内容进行头脑风暴：\n{instruction or '提供创意建议'}",
            'expand': f"请扩展以下内容的细节：\n{selected_text}",
            'summarize': "请总结以上内容的主要观点。",
        }
        
        user_prompt = action_prompts.get(action, instruction or "请协助改进这段文字。")
        
        if selected_text and action not in ['revise', 'polish', 'expand']:
            user_prompt = f"关于这段文字：\n{selected_text}\n\n{user_prompt}"
        
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    @staticmethod
    async def process_request(
        db: Session,
        request: AIRequest,
        document_content: str,
        user_id: int
    ) -> str:
        """处理 AI 请求（非流式）"""
        # 获取记忆上下文
        memory_context = ""
        if request.document_id:
            # 这里需要根据 document_id 获取 project_id
            from app.models.models import Document
            doc = db.query(Document).filter(Document.id == request.document_id).first()
            if doc:
                memory_context = AIMemoryService.build_memory_context(db, doc.project_id)
        
        messages = AIWritingService._build_messages(
            action=request.action,
            content=document_content,
            memory_context=memory_context,
            selected_text=request.selected_text,
            instruction=request.instruction
        )
        
        response = await ai_client.chat_completion(messages)
        
        # 记录交互（关联用户ID）
        interaction = AIInteraction(
            document_id=request.document_id,
            user_id=user_id,
            interaction_type=request.action,
            user_input=request.instruction or request.selected_text or "",
            ai_response=response,
            context_used={"memory_used": bool(memory_context)}
        )
        db.add(interaction)
        db.commit()
        
        return response
    
    @staticmethod
    async def stream_request(
        db: Session,
        request: AIRequest,
        document_content: str,
        user_id: int
    ) -> AsyncGenerator[str, None]:
        """处理 AI 请求（流式）"""
        from app.models.models import Document
        
        memory_context = ""
        doc = db.query(Document).filter(Document.id == request.document_id).first()
        if doc:
            memory_context = AIMemoryService.build_memory_context(db, doc.project_id)
        
        messages = AIWritingService._build_messages(
            action=request.action,
            content=document_content,
            memory_context=memory_context,
            selected_text=request.selected_text,
            instruction=request.instruction
        )
        
        full_response = []
        async for chunk in ai_client.stream_completion(messages):
            full_response.append(chunk)
            yield chunk
        
        # 记录交互（关联用户ID）
        interaction = AIInteraction(
            document_id=request.document_id,
            user_id=user_id,
            interaction_type=request.action,
            user_input=request.instruction or request.selected_text or "",
            ai_response="".join(full_response),
            context_used={"memory_used": bool(memory_context)}
        )
        db.add(interaction)
        db.commit()
    
    @staticmethod
    async def chat(
        db: Session,
        document_id: int,
        messages: list[ChatMessage],
        include_memory: bool = True,
        user_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """自由对话模式"""
        from app.models.models import Document
        
        formatted_messages = [{"role": "system", "content": AIWritingService.SYSTEM_PROMPT}]
        
        if include_memory:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                memory_context = AIMemoryService.build_memory_context(db, doc.project_id)
                if memory_context:
                    formatted_messages.append({
                        "role": "system",
                        "content": f"项目背景：\n{memory_context}"
                    })
        
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})
        
        async for chunk in ai_client.stream_completion(formatted_messages):
            yield chunk
