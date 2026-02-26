from typing import Optional, AsyncGenerator
from sqlalchemy.orm import Session
from app.core.ai_client import ai_client
from app.services.ai_memory_service import AIMemoryService
from app.services.rag_service import rag_service
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
        
        # 记录交互
        interaction = AIInteraction(
            document_id=request.document_id,
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
        user_id: int,
        use_rag: bool = True
    ) -> AsyncGenerator[str, None]:
        """处理 AI 请求（流式），支持 RAG 检索"""
        from app.models.models import Document
        
        memory_context = ""
        doc = db.query(Document).filter(Document.id == request.document_id).first()
        if doc:
            if use_rag:
                # 使用 RAG 检索相关上下文
                # 构建查询：结合当前操作、选中文本和指令
                query_parts = [request.action]
                if request.selected_text:
                    query_parts.append(request.selected_text[:200])
                if request.instruction:
                    query_parts.append(request.instruction)
                query = " ".join(query_parts)
                
                memory_context = rag_service.build_context_string(
                    doc.project_id,
                    query,
                    max_length=1200
                )
            else:
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
        
        # 记录交互
        interaction = AIInteraction(
            document_id=request.document_id,
            interaction_type=request.action,
            user_input=request.instruction or request.selected_text or "",
            ai_response="".join(full_response),
            context_used={"memory_used": bool(memory_context), "rag_used": use_rag}
        )
        db.add(interaction)
        db.commit()
    
    @staticmethod
    async def chat(
        db: Session,
        document_id: int,
        messages: list[ChatMessage],
        include_memory: bool = True,
        user_id: Optional[int] = None,
        use_rag: bool = True
    ) -> AsyncGenerator[str, None]:
        """自由对话模式，支持 RAG 检索"""
        from app.models.models import Document
        
        formatted_messages = [{"role": "system", "content": AIWritingService.SYSTEM_PROMPT}]
        
        if include_memory:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                # 获取用户最新的问题或上下文
                user_query = ""
                for msg in reversed(messages):
                    if msg.role == "user":
                        user_query = msg.content
                        break
                
                if use_rag and user_query:
                    # 使用 RAG 检索相关上下文
                    rag_context = rag_service.build_context_string(
                        doc.project_id, 
                        user_query,
                        max_length=1500
                    )
                    if rag_context:
                        formatted_messages.append({
                            "role": "system",
                            "content": f"以下是与当前问题相关的项目设定，请优先参考：\n{rag_context}"
                        })
                else:
                    # 回退到完整上下文
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

    # 根据项目设定生成的提示词模板
    GENERATE_PROMPTS = {
        "opening": "请根据以上项目设定，生成故事/文章的开头段落（约 300–500 字）。要求：自然引入世界观与角色，符合写作风格。",
        "continue": "请根据以上项目设定和当前文档已有内容，续写下一段（约 300–500 字）。保持风格一致，情节自然衔接。",
        "outline_section": "请根据以上项目设定中的大纲，任选一节或按顺序写一节正文（约 400–600 字）。需符合角色与世界观设定。",
        "scene": "请根据以上项目设定，生成一个具体场景片段（约 300–400 字），可包含对话与动作，贴合角色性格与世界观。",
        "custom": None,  # 由前端传入 custom_instruction
    }

    @staticmethod
    async def generate_from_memory(
        db: Session,
        project_id: int,
        generate_type: str,
        custom_instruction: Optional[str] = None,
        current_content: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """根据项目设定生成内容（流式）"""
        memory_context = AIMemoryService.build_memory_context(db, project_id)
        if not memory_context.strip():
            yield "[错误] 该项目暂无设定内容，请先在「项目设定」中填写大纲、角色或世界观后再生成。"
            return

        system_prompt = """你是一位专业的写作助手。用户将提供「项目设定」和具体生成要求。
请严格依据设定中的角色、世界观、写作风格和大纲来生成内容，保持风格统一、逻辑自洽。只输出生成的正文，不要输出解释或标题。"""

        user_parts = [f"【项目设定】\n{memory_context}"]
        if current_content:
            user_parts.append(f"\n【当前文档末尾内容】\n{current_content}")

        prompt_template = AIWritingService.GENERATE_PROMPTS.get(generate_type)
        if generate_type == "custom" and custom_instruction:
            instruction = custom_instruction
        elif prompt_template:
            instruction = prompt_template
        else:
            instruction = custom_instruction or "请根据项目设定生成一段正文。"

        user_parts.append(f"\n【生成要求】\n{instruction}")
        user_content = "\n".join(user_parts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        async for chunk in ai_client.stream_completion(messages):
            yield chunk
