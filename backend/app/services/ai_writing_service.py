from typing import Optional, AsyncGenerator
from sqlalchemy.orm import Session
import json
import asyncio
from app.core.ai_client import ai_client
from app.services.ai_memory_service import AIMemoryService
from app.services.long_text_processor import LongTextProcessor, process_long_text_stream
# from app.services.rag_service import rag_service  # RAG 功能已移除
from app.schemas.schemas import AIRequest, ChatMessage, AIGenerateProgress, AIGenerateChunk, LiteraryAnalysisResult, Character
from app.models.models import AIInteraction

class AIWritingService:
    """AI 写作服务 - 处理各种写作相关的 AI 交互"""

    SYSTEM_PROMPT = """你是一位专业的写作助手,具备以下能力:
1. 根据上下文理解文章的整体结构和目标
2. 提供有针对性的写作建议
3. 帮助润色和修改文本
4. 保持对角色设定、故事线、大纲的记忆一致性
5. 尊重用户的写作风格和意图

在回复时,请注意:
- 保持与已有内容的风格一致性
- 尊重已有的角色设定和世界观
- 当用户请求「修改」「润色」「扩展」「续写」时:只输出生成好的正文内容,不要输出任何说明、理由、前缀(如「改写如下:」「修改建议:」等),直接给出结果即可
- 当用户请求「指导」「总结」「头脑风暴」等建议类问题时,可以正常给出说明和建议"""

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
                "content": f"以下是项目的背景信息,请在回复时参考:\n{memory_context}"
            })

        # 仅对「改写类」请求基于选中内容生成,避免默认把整篇文档喂给模型。
        # 当用户确实没有选中内容时,才退回使用完整文档。
        rewrite_actions = {"revise", "polish", "expand", "continue"}
        include_full_document = True
        if action in rewrite_actions and selected_text and selected_text.strip():
            include_full_document = False

        if include_full_document:
            messages.append({
                "role": "user",
                "content": f"当前文档内容:\n{content}"
            })

        # 根据操作类型构建用户请求(改写类只返回正文,不要说明或前缀)
        action_prompts = {
            'guide': "请阅读以上内容,给出具体的写作指导建议。",
            'revise': f"请直接修改以下文本,不要加任何说明或前缀,只输出修改后的正文:\n{selected_text}\n\n修改要求:{instruction or '提升表达质量,保持原意'}\n\n编辑器格式约定(用于自动排版):大标题用单独一行以 `##` 开头;小标题用单独一行以 `###` 开头;引用/对话用单独一行以 `>` 开头;列表用单独一行以 `- ` 开头;分割线用单独一行使用 `---`;段落之间空一行;不要使用 Markdown 标题 `#`,不要使用 `**`/`*` 加粗斜体,不要输出 ``` 代码块。",
            'polish': f"请直接润色以下文本,不要加任何说明或前缀,只输出润色后的正文:\n{selected_text}\n\n编辑器格式约定(用于自动排版):大标题用单独一行以 `##` 开头;小标题用单独一行以 `###` 开头;引用/对话用单独一行以 `>` 开头;列表用单独一行以 `- ` 开头;分割线用单独一行使用 `---`;段落之间空一行;不要使用 Markdown 标题 `#`,不要使用 `**`/`*` 加粗斜体,不要输出 ``` 代码块。",
            'continue': "请根据已有内容,直接续写下一段正文,不要加任何说明或前缀。\n\n编辑器格式约定(用于自动排版):大标题用单独一行以 `##` 开头;小标题用单独一行以 `###` 开头;引用/对话用单独一行以 `>` 开头;列表用单独一行以 `- ` 开头;分割线用单独一行使用 `---`;段落之间空一行;不要使用 Markdown 标题 `#`,不要使用 `**`/`*` 加粗斜体,不要输出 ``` 代码块。",
            'brainstorm': f"请围绕以下内容进行头脑风暴:\n{instruction or '提供创意建议'}",
            'expand': f"请直接扩展以下内容的细节,不要加任何说明或前缀,只输出扩展后的正文:\n{selected_text}\n\n编辑器格式约定(用于自动排版):大标题用单独一行以 `##` 开头;小标题用单独一行以 `###` 开头;引用/对话用单独一行以 `>` 开头;列表用单独一行以 `- ` 开头;分割线用单独一行使用 `---`;段落之间空一行;不要使用 Markdown 标题 `#`,不要使用 `**`/`*` 加粗斜体,不要输出 ``` 代码块。",
            'summarize': "请总结以上内容的主要观点。",
        }

        user_prompt = action_prompts.get(action, instruction or "请协助改进这段文字。")

        if selected_text and action not in ['revise', 'polish', 'expand']:
            user_prompt = f"关于这段文字:\n{selected_text}\n\n{user_prompt}"

        messages.append({"role": "user", "content": user_prompt})

        return messages

    @staticmethod
    async def process_request(
        db: Session,
        request: AIRequest,
        document_content: str,
        user_id: int
    ) -> str:
        """处理 AI 请求(非流式)"""
        try:
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
        except ValueError as e:
            return f"[配置错误] {str(e)}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
        except Exception as e:
            error_msg = str(e)
            if "API Key" in error_msg or "api_key" in error_msg:
                return f"[错误] API Key 配置问题: {error_msg}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
            elif "连接" in error_msg or "Connection" in error_msg:
                return f"[错误] 网络连接问题: {error_msg}\n请检查网络连接或 API 地址是否正确。"
            else:
                return f"[错误] AI 请求失败: {error_msg}"

    @staticmethod
    async def stream_request(
        db: Session,
        request: AIRequest,
        document_content: str,
        user_id: int,
        use_rag: bool = True
    ) -> AsyncGenerator[str, None]:
        """处理 AI 请求(流式),支持 RAG 检索和长文本处理"""
        from app.models.models import Document

        try:
            memory_context = ""
            doc = db.query(Document).filter(Document.id == request.document_id).first()
            if doc:
                # RAG 功能已移除,直接使用 AIMemoryService
                memory_context = AIMemoryService.build_memory_context(db, doc.project_id)

            # 获取要处理的文本
            input_text = request.selected_text or document_content or ""

            # 估算输入 token 数
            estimated_input_tokens = len(input_text)

            # 检查是否需要长文本处理
            # 当文本长度超过阈值时,启用分段处理
            LONG_TEXT_THRESHOLD = 6000  # 字符数阈值

            if estimated_input_tokens > LONG_TEXT_THRESHOLD and request.action in ['polish', 'revise', 'expand']:
                # 使用长文本处理器
                async for chunk in AIWritingService._process_long_text_stream(
                    db, request, input_text, memory_context, user_id
                ):
                    yield chunk
                return

            # 短文本使用原有处理逻辑
            messages = AIWritingService._build_messages(
                action=request.action,
                content=document_content,
                memory_context=memory_context,
                selected_text=request.selected_text,
                instruction=request.instruction
            )

            # 根据输入内容长度动态计算 max_tokens
            # 润色操作需要足够的 token 来返回完整内容
            max_tokens = min(64000, max(4096, estimated_input_tokens * 2 + 1000))

            # 检查是否需要警告用户文本可能过长
            provider = ai_client.provider
            from app.core.ai_client import AIClient
            provider_limit = AIClient.PROVIDER_TOKEN_LIMITS.get(provider, 8192)
            if estimated_input_tokens > provider_limit // 3 and request.action in ['polish', 'revise', 'expand']:
                yield f"[提示] 当前文本较长(约 {estimated_input_tokens} 字符),模型输出限制为 {provider_limit} tokens。"
                yield f"如结果不完整,建议分段处理或使用支持更长输出的模型(如 Claude 3.5 Sonnet)。\n\n"

            full_response = []
            async for chunk in ai_client.stream_completion(messages, max_tokens=max_tokens):
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
        except ValueError as e:
            yield f"\n\n[配置错误] {str(e)}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
        except Exception as e:
            error_msg = str(e)
            if "API Key" in error_msg or "api_key" in error_msg:
                yield f"\n\n[错误] API Key 配置问题: {error_msg}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
            elif "连接" in error_msg or "Connection" in error_msg:
                yield f"\n\n[错误] 网络连接问题: {error_msg}\n请检查网络连接或 API 地址是否正确。"
            else:
                yield f"\n\n[错误] AI 请求失败: {error_msg}"

    @staticmethod
    async def _process_long_text_stream(
        db: Session,
        request: AIRequest,
        input_text: str,
        memory_context: str,
        user_id: int
    ) -> AsyncGenerator[str, None]:
        """
        处理长文本流式请求

        将长文本分段处理,保持上下文连贯性
        """
        processor = LongTextProcessor(max_chunk_size=8000, overlap_size=500, context_size=200)

        # 分段
        segments = processor.split_text(input_text)
        total_segments = len(segments)

        yield f"[长文本处理] 文本较长(约 {len(input_text)} 字符),将分为 {total_segments} 段处理...\n\n"

        all_responses = []

        for i, segment in enumerate(segments):
            # 发送段落进度
            yield f"\n[处理第 {i+1}/{total_segments} 段]\n"

            # 构建系统提示词
            system_prompt = AIWritingService._build_system_prompt(request.action, memory_context)

            # 构建段落提示词
            segment_prompt = processor.build_segment_prompt(segment, request.action, request.instruction)

            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": segment_prompt}
            ]

            # 计算该段落的 max_tokens
            estimated_tokens = len(segment.content) * 2 + 1000
            max_tokens = min(64000, max(4096, estimated_tokens))

            # 调用 AI
            segment_response = []
            try:
                async for chunk in ai_client.stream_completion(messages, max_tokens=max_tokens):
                    segment_response.append(chunk)
                    yield chunk

                all_responses.append("".join(segment_response))

            except Exception as e:
                error_msg = f"[第 {i+1} 段处理失败: {str(e)}]"
                yield error_msg
                all_responses.append(error_msg)

        # 记录交互(合并后的结果)
        full_response = "\n\n".join(all_responses)
        interaction = AIInteraction(
            document_id=request.document_id,
            interaction_type=request.action,
            user_input=request.instruction or input_text[:500] + "..." if len(input_text) > 500 else input_text,
            ai_response=full_response,
            context_used={"memory_used": bool(memory_context), "rag_used": False, "long_text_segments": total_segments}
        )
        db.add(interaction)
        db.commit()

        yield f"\n\n[长文本处理完成,共 {total_segments} 段]"

    @staticmethod
    async def chat(
        db: Session,
        document_id: int,
        messages: list[ChatMessage],
        include_memory: bool = True,
        user_id: Optional[int] = None,
        use_rag: bool = True
    ) -> AsyncGenerator[str, None]:
        """自由对话模式,支持 RAG 检索"""
        from app.models.models import Document

        try:
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
                        # RAG 功能已移除,直接使用 AIMemoryService
                        memory_context = AIMemoryService.build_memory_context(db, doc.project_id)
                        if memory_context:
                            formatted_messages.append({
                                "role": "system",
                                "content": f"项目背景:\n{memory_context}"
                            })
                    else:
                        # 回退到完整上下文
                        memory_context = AIMemoryService.build_memory_context(db, doc.project_id)
                        if memory_context:
                            formatted_messages.append({
                                "role": "system",
                                "content": f"项目背景:\n{memory_context}"
                            })

            for msg in messages:
                formatted_messages.append({"role": msg.role, "content": msg.content})

            async for chunk in ai_client.stream_completion(formatted_messages):
                yield chunk

        except ValueError as e:
            # 配置错误
            yield f"\n\n[配置错误] {str(e)}"
        except Exception as e:
            # 其他错误
            error_msg = str(e)
            if "API Key" in error_msg or "api_key" in error_msg:
                yield f"\n\n[错误] API Key 配置问题: {error_msg}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
            elif "连接" in error_msg or "Connection" in error_msg:
                yield f"\n\n[错误] 网络连接问题: {error_msg}\n请检查网络连接或 API 地址是否正确。"
            else:
                yield f"\n\n[错误] AI 请求失败: {error_msg}"

    # 根据项目设定生成的提示词模板
    GENERATE_PROMPTS = {
        "opening": "请根据以上项目设定,生成故事/文章的开头段落(约 300-500 字)。要求:自然引入世界观与角色,符合写作风格。",
        "continue": "请根据以上项目设定和当前文档已有内容,续写下一段(约 300-500 字)。保持风格一致,情节自然衔接。",
        "outline_section": "请根据以上项目设定中的大纲,任选一节或按顺序写一节正文(约 400-600 字)。需符合角色与世界观设定。",
        "scene": "请根据以上项目设定,生成一个具体场景片段(约 300-400 字),可包含对话与动作,贴合角色性格与世界观。",
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
        """根据项目设定生成内容(流式)"""
        try:
            memory_context = AIMemoryService.build_memory_context(db, project_id)
            if not memory_context.strip():
                yield "[错误] 该项目暂无设定内容,请先在「项目设定」中填写大纲、角色或世界观后再生成。"
                return

            system_prompt = """你是一位专业的写作助手。用户将提供「项目设定」和具体生成要求。
请严格依据设定中的角色、世界观、写作风格和大纲来生成内容,保持风格统一、逻辑自洽。只输出生成的正文,不要输出解释或标题。
格式约定:小节标题单独一行以 ## 开头;对话/引用以 > 开头;列表以 - 开头;段落之间空一行。不要使用 ``` 代码块。"""

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
        except ValueError as e:
            yield f"\n\n[配置错误] {str(e)}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
        except Exception as e:
            error_msg = str(e)
            if "API Key" in error_msg or "api_key" in error_msg:
                yield f"\n\n[错误] API Key 配置问题: {error_msg}\n请前往系统设置中配置正确的 AI 模型和 API Key。"
            elif "连接" in error_msg or "Connection" in error_msg:
                yield f"\n\n[错误] 网络连接问题: {error_msg}\n请检查网络连接或 API 地址是否正确。"
            else:
                yield f"\n\n[错误] AI 生成失败: {error_msg}"

    @staticmethod
    def _estimate_chinese_chars(tokens: int) -> int:
        """估算中文字符数(中文约1.5 tokens/字)"""
        return int(tokens / 1.5)

    @staticmethod
    def _build_system_prompt(
        memory_context: str,
        outline_node: dict,
        previous_context: str,
        custom_instruction: Optional[str],
        max_chars: int
    ) -> str:
        """构建系统提示词"""
        node_title = outline_node.get('title', '未命名章节')
        node_description = outline_node.get('description', '')

        system_parts = [
            "你是一位专业的小说/文章写作助手。请根据项目设定和章节大纲,生成高质量的正文内容。",
            "",
            "要求:",
            "1. 严格遵循世界观、角色设定和写作风格",
            "2. 内容紧扣章节主题和大纲描述",
            "3. 保持与前文的连贯性(如有前文)",
            f"4. 字数控制在 {max_chars} 字符以内",
            "5. 只输出生成的正文,不要输出章节标题或解释",
            "6. 使用自然流畅的中文写作",
            "",
            "【格式约定】为便于自动排版,请适当使用以下标记(每行单独使用):",
            "- 小节标题:单独一行,以 ## 开头,如 ## 场景一",
            "- 子标题:单独一行,以 ### 开头",
            "- 对话/引用:以 > 开头的行,如 > \"你好。\"",
            "- 列表:以 - 开头的行",
            "- 段落之间空一行。不要使用 ``` 等代码块标记。"
        ]

        return "\n".join(system_parts)

    @staticmethod
    def _build_chapter_prompt(
        memory_context: str,
        outline_node: dict,
        previous_context: str,
        custom_instruction: Optional[str],
        max_chars: int
    ) -> list:
        """构建章节生成的 prompt"""
        node_title = outline_node.get('title', '未命名章节')
        node_description = outline_node.get('description', '')
        
        # 使用 _build_system_prompt 构建系统提示词
        system_prompt = AIWritingService._build_system_prompt(
            memory_context=memory_context,
            outline_node=outline_node,
            previous_context=previous_context,
            custom_instruction=custom_instruction,
            max_chars=max_chars
        )

        user_parts = [f"【项目设定】\n{memory_context}"]
        
        user_parts.append(f"\n【当前章节】\n标题：{node_title}")
        if node_description:
            user_parts.append(f"大纲描述：{node_description}")
        
        if previous_context:
            # 限制前文长度，避免超出上下文
            truncated_prev = previous_context[-3000:] if len(previous_context) > 3000 else previous_context
            user_parts.append(f"\n【前文回顾（最后部分）】\n{truncated_prev}")
        
        user_parts.append(f"\n【写作要求】\n请生成本章正文，字数约 {max_chars} 字符。可适当用 ## 小节标题、> 对话/引用、- 列表 等格式增强可读性，段落间空一行。")
        if custom_instruction:
            user_parts.append(f"额外要求：{custom_instruction}")
        
        user_content = "\n".join(user_parts)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

    @staticmethod
    async def batch_generate(
        db: Session,
        project_id: int,
        document_id: int,
        outline_nodes: list,
        max_tokens_per_chapter: int = 2000,
        continue_on_complete: bool = True,
        custom_instruction: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """批量/多轮次生成章节内容

        基于大纲节点列表,逐章生成内容,每章完成后发送进度更新
        """
        from app.models.models import Document

        # 获取项目记忆上下文
        memory_context = AIMemoryService.build_memory_context(db, project_id)
        if not memory_context.strip():
            error_chunk = AIGenerateChunk(
                type="error",
                error_message="该项目暂无设定内容,请先在「项目设定」中填写大纲、角色或世界观后再生成。"
            )
            yield json.dumps(error_chunk.dict(), ensure_ascii=False)
            return

        # 获取当前文档内容(用于续写)
        doc = db.query(Document).filter(Document.id == document_id).first()
        accumulated_content = ""
        if doc and doc.content:
            # 提取已有文本内容
            for block in doc.content:
                if isinstance(block, dict) and block.get('content'):
                    accumulated_content += block.get('content', '') + "\n"

        total_chapters = len(outline_nodes)
        estimated_chars_per_chapter = AIWritingService._estimate_chinese_chars(max_tokens_per_chapter)

        for idx, node in enumerate(outline_nodes):
            chapter_title = node.get('title', f'章节 {idx + 1}')

            # 发送进度更新 - 开始生成
            progress = AIGenerateProgress(
                total_chapters=total_chapters,
                current_chapter=idx + 1,
                current_title=chapter_title,
                status="generating",
                generated_chars=len(accumulated_content),
                estimated_total_chars=estimated_chars_per_chapter * total_chapters,
                content_preview=accumulated_content[-200:] if accumulated_content else ""
            )
            chunk = AIGenerateChunk(
                type="progress",
                progress=progress,
                chapter_index=idx,
                chapter_title=chapter_title
            )
            yield json.dumps(chunk.dict(), ensure_ascii=False)

            # 构建 prompt
            messages = AIWritingService._build_chapter_prompt(
                memory_context=memory_context,
                outline_node=node,
                previous_context=accumulated_content,
                custom_instruction=custom_instruction,
                max_chars=estimated_chars_per_chapter
            )

            # 生成章节内容(超过 API 单次上限时自动分段续写)
            SINGLE_CALL_LIMIT = 8192
            chapter_content = []
            max_rounds = max(1, (max_tokens_per_chapter // SINGLE_CALL_LIMIT) + 1)
            tokens_per_call = min(max_tokens_per_chapter, SINGLE_CALL_LIMIT)
            try:
                for round_idx in range(max_rounds):
                    if round_idx > 0:
                        so_far = "".join(chapter_content)
                        if len(so_far) >= estimated_chars_per_chapter:
                            break
                        messages = AIWritingService._build_chapter_prompt(
                            memory_context=memory_context,
                            outline_node=node,
                            previous_context=so_far[-2000:],
                            custom_instruction=(custom_instruction or "") + f"\n请从上文断点处继续写,还需约{max(0, estimated_chars_per_chapter - len(so_far))}字,不要重复已有内容。",
                            max_chars=max(500, estimated_chars_per_chapter - len(so_far))
                        )

                    async for text_chunk in ai_client.stream_completion(
                        messages,
                        max_tokens=tokens_per_call
                    ):
                        chapter_content.append(text_chunk)
                        content_chunk = AIGenerateChunk(
                            type="content",
                            content=text_chunk,
                            chapter_index=idx,
                            chapter_title=chapter_title
                        )
                        yield json.dumps(content_chunk.dict(), ensure_ascii=False)

                full_chapter = "".join(chapter_content)
                accumulated_content += full_chapter + "\n\n"
                chapter_chars = len(full_chapter)

                # 发送章节完成通知(包含完整内容)
                complete_chunk = AIGenerateChunk(
                    type="chapter_complete",
                    chapter_index=idx,
                    chapter_title=chapter_title,
                    chapter_content=full_chapter,
                    chapter_chars=chapter_chars,
                    total_chars=len(accumulated_content)
                )
                yield json.dumps(complete_chunk.dict(), ensure_ascii=False)

                # 记录交互
                interaction = AIInteraction(
                    document_id=document_id,
                    interaction_type="batch_generate",
                    user_input=f"生成章节: {chapter_title}",
                    ai_response=full_chapter,
                    context_used={
                        "project_id": project_id,
                        "outline_node": node,
                        "max_tokens": max_tokens_per_chapter
                    }
                )
                db.add(interaction)
                db.commit()

            except Exception as e:
                error_chunk = AIGenerateChunk(
                    type="error",
                    error_message=f"生成章节 '{chapter_title}' 时出错: {str(e)}",
                    chapter_index=idx,
                    chapter_title=chapter_title
                )
                yield json.dumps(error_chunk.dict(), ensure_ascii=False)

                if not continue_on_complete:
                    break

        # 发送完成通知
        done_chunk = AIGenerateChunk(
            type="done",
            total_chars=len(accumulated_content)
        )
        yield json.dumps(done_chunk.dict(), ensure_ascii=False)

    @staticmethod
    async def analyze_literature(
        content: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        category: str = "novel"
    ) -> LiteraryAnalysisResult:
        """分析文学作品,提取结构化信息

        Args:
            content: 文学作品文本内容
            title: 作品标题(可选)
            author: 作者(可选)
            category: 作品类型

        Returns:
            LiteraryAnalysisResult: 分析结果
        """
        # 截取前 15000 字符作为分析样本(避免 token 超限)
        sample_text = content[:15000] if len(content) > 15000 else content

        system_prompt = """你是一位专业的文学分析专家。请对提供的文学作品进行深入分析,提取以下结构化信息:

1. 作品标题和简介
2. 故事大纲/章节结构
3. 主要角色设定(姓名、描述、性格、背景、目标)
4. 世界观设定(时代背景、地点、规则等)
5. 写作风格特点
6. 关键情节点
7. 核心主题/思想

请严格按 JSON 格式返回,不要添加任何解释性文字。"""

        user_prompt = f"""请分析以下文学作品:

作品类型: {category}
{title and f"标题: {title}" or ""}
{author and f"作者: {author}" or ""}

文本内容(前 {len(sample_text)} 字符):
{sample_text}

请返回以下 JSON 格式:
{{
    "title": "作品标题",
    "description": "作品简介,200字左右",
    "category": "{category}",
    "outline": [
        {{"title": "第一章标题", "description": "章节内容概要"}},
        {{"title": "第二章标题", "description": "章节内容概要"}}
    ],
    "storyline": "故事主线概述,300字左右",
    "characters": [
        {{
            "name": "角色名",
            "description": "角色描述",
            "personality": "性格特点",
            "background": "背景故事",
            "goals": "目标动机"
        }}
    ],
    "world_building": {{
        "era": "时代背景",
        "location": "主要地点",
        "rules": "世界规则/设定"
    }},
    "writing_style": "写作风格分析,100字左右",
    "key_points": ["关键情节点1", "关键情节点2"],
    "themes": ["主题1", "主题2"]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # 增加超时时间到 120 秒,文学作品分析需要更多时间
            response = await ai_client.chat_completion(
                messages,
                temperature=0.7,
                max_tokens=4000,
                timeout=120.0
            )

            # 提取 JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            # 构建结果
            characters = [Character(**c) for c in data.get("characters", [])]

            return LiteraryAnalysisResult(
                title=data.get("title", title or "未命名作品"),
                description=data.get("description", ""),
                category=data.get("category", category),
                outline=data.get("outline", []),
                storyline=data.get("storyline"),
                characters=characters,
                world_building=data.get("world_building", {}),
                writing_style=data.get("writing_style"),
                key_points=data.get("key_points", []),
                themes=data.get("themes", [])
            )

        except Exception as e:
            # 解析失败返回基础结果
            return LiteraryAnalysisResult(
                title=title or "未命名作品",
                description=f"分析出错: {str(e)}",
                category=category,
                outline=[],
                characters=[],
                world_building={},
                key_points=[],
                themes=[]
            )
