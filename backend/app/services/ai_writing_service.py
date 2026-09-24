from typing import Optional, AsyncGenerator, List
from sqlalchemy.orm import Session
import json
import re
import asyncio
import logging
from app.core.ai_client import ai_client
from app.services.ai_memory_service import AIMemoryService
from app.services.long_text_processor import LongTextProcessor, process_long_text_stream
# from app.services.rag_service import rag_service  # RAG 功能已移除
from app.schemas.schemas import AIRequest, ChatMessage, AIGenerateProgress, AIGenerateChunk, LiteraryAnalysisResult, Character
from app.models.models import AIInteraction

logger = logging.getLogger(__name__)


class AIWritingService:
    """AI 写作服务 - 处理各种写作相关的 AI 交互"""

    # 短规则 + 正反对照：自然流畅优先，去机感但不碎句硬拗
    ANTI_AI_STYLE_RULES = """【写法】用自然、顺畅的叙述推进；场面与行动优先；语气像人在讲故事，读起来连贯省力。
句式以完整通顺为主，长短可略有变化，但不要故意堆短句、半截话、跳跃断句；段落之间要接得上。
对话口语化即可，仍要听得懂、接得住；关键抉择可略带犹豫，但别写成意识流碎片。
少用比喻；结尾自然收住即可，勿用精致比喻做首尾呼应。

【禁】成串比喻／通感；「不是A而是B」与解释动机的排比；软肋清单式转折；首尾比喻回环；「然而就在这时／突然／不禁／宛如／命运」套话；每句都为主题服务的过度工整。
另禁：为了「像人手」而刻意碎片化——连续短句、无厘头断句、前言不搭后语。

【对照——学右不学左】
机感（过文）：屏幕的光像一层苍白的雾。他想起所有失败的社交、所有被误解的沉默。协议像一扇半开的门。
机感（过碎）：空调在震。盯着键。牛奶。过期了吧。算了。点。喇叭。烦。
人手：空调外机一直震。他盯着确认键，忽然想起冰箱里那盒牛奶可能过期了，还是点了下去。楼下有人按电动车喇叭，挺烦的。

写完自检：是否通顺自然；比喻是否过多；有没有为去AI而故意写碎。"""

    # 生成后二遍：去机感，但保持自然连贯
    HUMANIZE_PROMPT = """你是文本润色员。下面是一篇已写好的中文正文。请只做「去机感、更自然」的改写，不要扩写情节、不要换结局、不要加标题或说明。

必须动手改的：
1. 删掉过多的比喻/通感；能直写就直写。
2. 拆开排比与工整对仗，改成自然散句——但仍要通顺连贯，不要改成半截话或意识流碎片。
3. 若文风过碎（短句连打、断句跳跃），把它们接成完整、好读的句子与段落。
4. 若结尾在呼应开头或用精致比喻收束，改成自然、不刻意的收法。
5. 整体语气自然流畅，像人手叙述；句长可略有变化，但以可读性为先，禁止故意堆短句。
6. 保留原有事实、人名、情节走向与大致篇幅（字数变化不超过 ±15%）。

只输出改写后的正文。"""

    SYSTEM_PROMPT = """你是一位写作助手。生成/改写正文时用自然流畅的人手叙述,削弱机感与模板腔,但不要故意写碎、写断。

在回复时,请注意:
- 保持与已有内容的风格一致性
- 尊重已有的角色设定和世界观
- 当用户请求「修改」「润色」「扩展」「续写」「调整样式」时:只输出生成好的正文内容,不要输出任何说明、理由、前缀(如「改写如下:」「修改建议:」等),直接给出结果即可
- 当用户请求「调整样式/排版」时:只调整结构与分段,严禁改写、增删或替换任何原文用词与标点语义
- 当用户请求「修改」「润色」「扩展」「续写」时,必须遵守下列写法;润色时保留原意与口吻,只去掉机感并保持通顺
- 当用户请求「指导」「总结」「头脑风暴」等建议类问题时,可以正常给出说明和建议

""" + ANTI_AI_STYLE_RULES

    # 需要做「去机感二遍」的动作（排版不碰）
    _HUMANIZE_ACTIONS = frozenset({"revise", "polish", "expand", "continue"})

    @staticmethod
    async def humanize_prose(text: str, max_chars: int = 12000) -> str:
        """生成后二遍润色：打散均匀文学感。失败则退回原文。"""
        raw = (text or "").strip()
        if len(raw) < 80:
            return text
        # 过长则只处理前段，避免超时；后段原样拼接
        head = raw[:max_chars]
        tail = raw[max_chars:] if len(raw) > max_chars else ""
        messages = [
            {"role": "system", "content": AIWritingService.HUMANIZE_PROMPT},
            {"role": "user", "content": head},
        ]
        try:
            # 略提高温度，但以自然流畅为目标（HUMANIZE_PROMPT 已禁止故意碎句）
            out = await ai_client.chat_completion(
                messages,
                temperature=0.85,
                max_tokens=min(16000, max(2048, int(len(head) * 1.5) + 500)),
                enable_network_test=False,
                retry_attempts=2,
            )
            cleaned = (out or "").strip()
            if not cleaned or cleaned.startswith("[错误]") or cleaned.startswith("[配置错误]"):
                return text
            # 去掉偶发的说明前缀
            for prefix in ("改写如下：", "改写如下:", "正文：", "正文:"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
            return cleaned + tail
        except Exception as e:
            logger.warning("humanize_prose failed: %s", e)
            return text

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
        rewrite_actions = {"revise", "polish", "expand", "continue", "format_style"}
        include_full_document = True
        if action in rewrite_actions and selected_text and selected_text.strip():
            include_full_document = False

        if include_full_document:
            messages.append({
                "role": "user",
                "content": f"当前文档内容:\n{content}"
            })

        format_markers = (
            "编辑器格式约定(用于自动排版):大标题用单独一行以 `##` 开头;小标题用单独一行以 `###` 开头;"
            "引用/对话用单独一行以 `>` 开头;列表用单独一行以 `- ` 开头;分割线用单独一行使用 `---`;"
            "段落之间空一行;不要使用 Markdown 标题 `#`,不要使用 `**`/`*` 加粗斜体,不要输出 ``` 代码块。"
        )
        format_style_rules = (
            "核心要求(必须严格遵守):\n"
            "1. 只调整结构与排版:合理分段、识别标题/小标题/列表/引用/分割线,改善层次与可读性;\n"
            "2. 严禁修改正文内容:不得增删改任何字词、句子、数字、专有名词或标点的语义;\n"
            "3. 不得润色、改写、扩写、缩写或替换同义词;原文逐字保留,仅允许因排版需要插入换行与格式标记行;\n"
            "4. 不要添加任何说明、理由或前缀,只输出排版后的正文。"
        )
        format_style_source = selected_text if (selected_text and selected_text.strip()) else content

        human_touch = (
            "写作约束:用自然流畅的人手叙述,去机感与模板腔;场面与行动优先,对话自然;"
            "以完整通顺的句子为主,不要故意堆短句、半截话或不连贯断句;"
            "禁止密集成串比喻、排比模板、宿命空话、对称升华结尾。"
        )
        # 根据操作类型构建用户请求(改写类只返回正文,不要说明或前缀)
        action_prompts = {
            'guide': "请阅读以上内容,给出具体的写作指导建议。",
            'revise': (
                f"请直接修改以下文本,不要加任何说明或前缀,只输出修改后的正文:\n{selected_text}\n\n"
                f"修改要求:{instruction or '提升表达质量,保持原意,削弱机感'}\n\n{human_touch}\n\n{format_markers}"
            ),
            'polish': (
                f"请直接润色以下文本,不要加任何说明或前缀,只输出润色后的正文:\n{selected_text}\n\n"
                f"润色目标:更像人手写的自然文笔,保留原意与口吻,去掉模板腔与空洞抒情。\n\n{human_touch}\n\n{format_markers}"
            ),
            'continue': (
                f"请根据已有内容,直接续写下一段正文,不要加任何说明或前缀。\n\n{human_touch}\n\n{format_markers}"
            ),
            'brainstorm': f"请围绕以下内容进行头脑风暴:\n{instruction or '提供创意建议'}",
            'expand': (
                f"请直接扩展以下内容的细节,不要加任何说明或前缀,只输出扩展后的正文:\n{selected_text}\n\n"
                f"扩展时用可见可闻的场面与具体动作,不要堆砌比喻或总结性抒情。\n\n{human_touch}\n\n{format_markers}"
            ),
            'summarize': "请总结以上内容的主要观点。",
            'format_style': (
                f"请对以下结构混乱的文稿做「仅排版」优化,不要加任何说明或前缀:\n{format_style_source}\n\n"
                f"{format_style_rules}\n\n{format_markers}"
            ),
        }

        user_prompt = action_prompts.get(action, instruction or "请协助改进这段文字。")

        if selected_text and action not in ['revise', 'polish', 'expand', 'format_style']:
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
                    memory_context = AIMemoryService.build_memory_context(
                        db, doc.project_id, getattr(request, "style_agent_id", None)
                    )

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
                memory_context = AIMemoryService.build_memory_context(
                    db, doc.project_id, getattr(request, "style_agent_id", None)
                )

            # 获取要处理的文本
            input_text = request.selected_text or document_content or ""

            # 估算输入 token 数
            estimated_input_tokens = len(input_text)

            # 检查是否需要长文本处理
            # 当文本长度超过阈值时,启用分段处理
            LONG_TEXT_THRESHOLD = 6000  # 字符数阈值

            if estimated_input_tokens > LONG_TEXT_THRESHOLD and request.action in ['polish', 'revise', 'expand', 'format_style']:
                # 仅在“确实能分成多段”时才启用分段流程
                # 避免出现“进入长文本模式但实际只有 1 段”导致额外延迟
                processor = LongTextProcessor(max_chunk_size=8000, overlap_size=500, context_size=200)
                preview_segments = processor.split_text(input_text)
                if len(preview_segments) > 1:
                    async for chunk in AIWritingService._process_long_text_stream(
                        db, request, input_text, memory_context, user_id
                    ):
                        yield chunk
                    return

            # 短文本：先完整生成，正文类动作再做去机感二遍，再分段吐出（避免边流边机感定型）
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

            full_response = []
            async for chunk in ai_client.stream_completion(messages, max_tokens=max_tokens):
                full_response.append(chunk)

            result = "".join(full_response)
            if request.action in AIWritingService._HUMANIZE_ACTIONS:
                result = await AIWritingService.humanize_prose(result)

            chunk_size = 400
            for i in range(0, len(result), chunk_size):
                yield result[i:i + chunk_size]

            # 记录交互
            interaction = AIInteraction(
                document_id=request.document_id,
                interaction_type=request.action,
                user_input=request.instruction or request.selected_text or "",
                ai_response=result,
                context_used={
                    "memory_used": bool(memory_context),
                    "rag_used": use_rag,
                    "humanized": request.action in AIWritingService._HUMANIZE_ACTIONS,
                }
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
        处理长文本流式请求 - 分段并发处理，整体返回

        将长文本智能分段后并发调用 AI，按原段落顺序合并并返回。
        对外表现与普通的润色/扩展/修改操作一致，前端无需特殊处理。
        """
        processor = LongTextProcessor(max_chunk_size=8000, overlap_size=500, context_size=200)

        # 分段
        segments = processor.split_text(input_text)
        total_segments = len(segments)

        # 并发控制：避免同时请求过多导致模型服务拥塞
        max_concurrency = min(4, max(1, total_segments))
        semaphore = asyncio.Semaphore(max_concurrency)
        all_responses = [""] * total_segments
        fallback_indices: list[int] = []
        max_retries = 2

        async def _process_segment(index: int, segment) -> None:
            async with semaphore:
                system_prompt = AIWritingService.SYSTEM_PROMPT
                segment_prompt = processor.build_segment_prompt(
                    segment,
                    request.action,
                    request.instruction
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"项目背景信息:\n{memory_context}"} if memory_context else None,
                    {"role": "user", "content": segment_prompt}
                ]
                messages = [m for m in messages if m is not None]

                estimated_tokens = len(segment.content) * 2 + 1000
                max_tokens = min(64000, max(4096, estimated_tokens))

                for attempt in range(max_retries + 1):
                    try:
                        segment_response = await ai_client.chat_completion(
                            messages,
                            max_tokens=max_tokens,
                            timeout=180.0,
                            enable_network_test=False,
                            retry_attempts=1
                        )
                        all_responses[index] = segment_response
                        return
                    except Exception as e:
                        is_last_try = attempt >= max_retries
                        if is_last_try:
                            logger.warning(
                                "长文本分段第 %s/%s 段请求失败，已回退为原文: %s",
                                index + 1,
                                total_segments,
                                e,
                            )
                            all_responses[index] = segment.content
                            fallback_indices.append(index)
                            return
                        await asyncio.sleep(min(2 * (attempt + 1), 5))

        await asyncio.gather(*[_process_segment(i, seg) for i, seg in enumerate(segments)])

        # 合并所有段落结果
        full_response = "\n\n".join(all_responses)

        # 记录交互
        user_input_text = request.instruction or (input_text[:500] + "..." if len(input_text) > 500 else input_text)
        interaction = AIInteraction(
            document_id=request.document_id,
            interaction_type=request.action,
            user_input=user_input_text,
            ai_response=full_response,
            context_used={
                "memory_used": bool(memory_context),
                "rag_used": False,
                "long_text_segments": total_segments,
                "long_text_fallback_segment_indices": fallback_indices,
            }
        )
        db.add(interaction)
        db.commit()

        # 按较大块流式输出，减少人为延迟与前端等待时间
        chunk_size = 500
        for i in range(0, len(full_response), chunk_size):
            chunk = full_response[i:i + chunk_size]
            yield chunk

    @staticmethod
    async def chat(
        db: Session,
        document_id: int,
        messages: list[ChatMessage],
        include_memory: bool = True,
        user_id: Optional[int] = None,
        use_rag: bool = True,
        style_agent_id: Optional[int] = None,
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
                        memory_context = AIMemoryService.build_memory_context(
                            db, doc.project_id, style_agent_id
                        )
                        if memory_context:
                            formatted_messages.append({
                                "role": "system",
                                "content": f"项目背景:\n{memory_context}"
                            })
                    else:
                        # 回退到完整上下文
                        memory_context = AIMemoryService.build_memory_context(
                            db, doc.project_id, style_agent_id
                        )
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
        "opening": "请根据以上项目设定,生成故事/文章的开头段落(约 300-500 字)。要求:自然流畅、场面先行、少比喻;句子完整连贯,忌模板腔,忌刻意碎句。",
        "continue": "请根据以上项目设定和当前文档已有内容,续写下一段(约 300-500 字)。叙述顺畅接上前文;少比喻少排比;忌宿命空话与对称收束,也忌短句连打。",
        "outline_section": "请根据以上项目设定中的大纲,任选一节或按顺序写一节正文(约 400-600 字)。自然通顺像人手;转折别太懂事;少比喻;结尾不要呼应开头;不要故意写碎。",
        "scene": "请根据以上项目设定,生成一个具体场景片段(约 300-400 字)。对话口语但连贯;最多一处比喻;少解释主题;整体好读。",
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
        style_agent_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """根据项目设定生成内容(流式)"""
        try:
            memory_context = AIMemoryService.build_memory_context(
                db, project_id, style_agent_id
            )
            if not memory_context.strip():
                yield "[错误] 该项目暂无设定内容,请先在「项目设定」中填写大纲、角色或世界观后再生成。"
                return

            system_prompt = f"""你是一位专业的写作助手。用户将提供「项目设定」和具体生成要求。
请严格依据设定中的角色、世界观、写作风格和大纲来生成内容,保持风格统一、逻辑自洽。只输出生成的正文,不要输出解释或标题。
用自然流畅的人手叙述:场面与行动优先,句子完整连贯,对话自然;不要写成整齐范文,也不要故意碎句断句。
格式约定:小节标题单独一行以 ## 开头;对话/引用以 > 开头;列表以 - 开头;段落之间空一行。不要使用 ``` 代码块。

{AIWritingService.ANTI_AI_STYLE_RULES}"""

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

            parts: List[str] = []
            async for chunk in ai_client.stream_completion(messages):
                parts.append(chunk)
            result = await AIWritingService.humanize_prose("".join(parts))
            step = 400
            for i in range(0, len(result), step):
                yield result[i:i + step]
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

    REWRITE_MODE_HINTS = {
        "full": "按最新设定完整重写本章，可大幅调整情节与表述，但保留本章标题/大纲意图。",
        "align": "在尽量保留原有情节走向与关键事件的前提下，修正与最新设定冲突的人名、设定、世界观与文风。",
        "characters": "重点按最新角色卡修正人物称呼、性格、动机与对白，情节骨架尽量不动。",
        "world": "重点按最新世界观/规则修正场景、道具与背景描写，情节骨架尽量不动。",
        "style": "重点按最新写作风格调整语气与节奏，事实与情节尽量保留。",
    }

    @staticmethod
    def _blocks_to_plain(content) -> str:
        if not content:
            return ""
        if isinstance(content, str):
            return content
        lines = []
        for block in content:
            if not isinstance(block, dict):
                continue
            bt = block.get("type", "paragraph")
            c = block.get("content", "") or ""
            if bt == "heading":
                lines.append(f"## {c}")
            elif bt == "quote":
                lines.append(f"> {c}")
            elif bt == "list":
                lines.append(f"- {c}")
            elif bt == "image":
                continue
            else:
                lines.append(str(c))
        return "\n\n".join(lines).strip()

    @staticmethod
    async def rewrite_documents_from_memory(
        db: Session,
        project_id: int,
        document_ids: Optional[List[int]] = None,
        rewrite_mode: str = "align",
        custom_instruction: Optional[str] = None,
        apply_to_documents: bool = True,
        user_id: Optional[int] = None,
        style_agent_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        按最新项目设定重写文档。产出 SSE 友好的 JSON 行事件（调用方再包 data: ）。
        事件类型: status | doc_start | content | doc_done | complete | error
        """
        from app.models.models import Document
        from app.utils.document_format import parse_formatted_text_to_blocks

        def emit(obj: dict) -> str:
            return json.dumps(obj, ensure_ascii=False)

        try:
            memory_context = AIMemoryService.build_memory_context(
                db, project_id, style_agent_id
            )
            if not memory_context.strip():
                yield emit({"type": "error", "message": "项目暂无设定，请先填写大纲/角色/世界观等"})
                return

            q = db.query(Document).filter(Document.project_id == project_id)
            if document_ids:
                q = q.filter(Document.id.in_(document_ids))
            docs = q.order_by(Document.order_index.asc(), Document.id.asc()).all()
            if not docs:
                yield emit({"type": "error", "message": "没有可重写的文档"})
                return

            mode = rewrite_mode if rewrite_mode in AIWritingService.REWRITE_MODE_HINTS else "align"
            mode_hint = AIWritingService.REWRITE_MODE_HINTS[mode]

            yield emit({
                "type": "status",
                "message": f"将按「{mode}」模式重写 {len(docs)} 篇文档",
                "total": len(docs),
            })

            system_prompt = f"""你是专业小说/文章改写助手。用户修改了项目设定，需要你根据【最新设定】重写【原文】。
只输出重写后的正文，不要解释、不要前言。
格式：小节标题单独一行以 ## 开头；对话/引用以 > 开头；列表以 - 开头；段落之间空一行。不要使用 ``` 代码块。

{AIWritingService.ANTI_AI_STYLE_RULES}"""

            rewritten = 0
            for idx, doc in enumerate(docs):
                original = AIWritingService._blocks_to_plain(doc.content)
                if not original.strip():
                    yield emit({
                        "type": "doc_done",
                        "index": idx,
                        "total": len(docs),
                        "document_id": doc.id,
                        "title": doc.title,
                        "skipped": True,
                        "message": f"跳过空文档：{doc.title}",
                    })
                    continue

                # 过长正文截断，避免撑爆上下文（保留头尾）
                src = original
                if len(src) > 12000:
                    src = src[:6000] + "\n\n……（中间省略）……\n\n" + src[-6000:]

                yield emit({
                    "type": "doc_start",
                    "index": idx,
                    "total": len(docs),
                    "document_id": doc.id,
                    "title": doc.title,
                    "message": f"正在重写（{idx + 1}/{len(docs)}）：{doc.title}",
                })

                user_parts = [
                    f"【最新项目设定】\n{memory_context}",
                    f"\n【本章标题】\n{doc.title}",
                    f"\n【改写模式】\n{mode_hint}",
                    f"\n【原文】\n{src}",
                    "\n【任务】\n请输出与最新设定一致的重写正文。",
                ]
                if custom_instruction:
                    user_parts.append(f"\n【额外要求】\n{custom_instruction}")

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "\n".join(user_parts)},
                ]

                chunks: List[str] = []
                try:
                    async for chunk in ai_client.stream_completion(messages, max_tokens=12000):
                        if chunk:
                            chunks.append(chunk)
                            yield emit({
                                "type": "content",
                                "document_id": doc.id,
                                "index": idx,
                                "chunk": chunk,
                            })
                except Exception as e:
                    yield emit({
                        "type": "error",
                        "document_id": doc.id,
                        "message": f"「{doc.title}」重写失败: {e}",
                    })
                    continue

                full = "".join(chunks).strip()
                if not full or full.startswith("[错误]") or full.startswith("[配置错误]"):
                    yield emit({
                        "type": "error",
                        "document_id": doc.id,
                        "message": f"「{doc.title}」未得到有效重写结果",
                    })
                    continue

                if apply_to_documents:
                    blocks = parse_formatted_text_to_blocks(full, f"rw{doc.id}")
                    if blocks:
                        doc.content = blocks
                        db.commit()

                rewritten += 1
                yield emit({
                    "type": "doc_done",
                    "index": idx,
                    "total": len(docs),
                    "document_id": doc.id,
                    "title": doc.title,
                    "applied": apply_to_documents,
                    "word_count": len(full),
                    "preview": full[:400],
                    "full_content": full if (not apply_to_documents and len(docs) == 1) else None,
                    "message": f"已完成：{doc.title}",
                })

            yield emit({
                "type": "complete",
                "rewritten": rewritten,
                "total": len(docs),
                "applied": apply_to_documents,
                "message": f"全部完成：成功重写 {rewritten}/{len(docs)} 篇",
            })
        except Exception as e:
            yield emit({"type": "error", "message": str(e)})

    @staticmethod
    async def rebuild_project_from_memory(
        db: Session,
        project_id: int,
        chapter_count: Optional[int] = None,
        words_per_chapter: int = 1500,
        custom_instruction: Optional[str] = None,
        archive_old_docs: bool = True,
        update_outline: bool = True,
        user_id: Optional[int] = None,
        style_agent_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        设定大改场景：吸收旧稿要点 → 按最新设定重梳大纲 → 生成新章节文档。
        事件: status | outline_ready | archive_done | doc_start | content | doc_done | complete | error
        """
        from app.models.models import Document
        from app.utils.document_format import parse_formatted_text_to_blocks

        def emit(obj: dict) -> str:
            return json.dumps(obj, ensure_ascii=False)

        try:
            memory_context = AIMemoryService.build_memory_context(
                db, project_id, style_agent_id
            )
            if not memory_context.strip():
                yield emit({"type": "error", "message": "项目暂无设定，请先填写角色/世界观/故事线等"})
                return

            old_docs = (
                db.query(Document)
                .filter(Document.project_id == project_id, Document.parent_id.is_(None))
                .order_by(Document.order_index.asc(), Document.id.asc())
                .all()
            )
            # 也包含有 parent 的正文（非归档夹）
            all_docs = (
                db.query(Document)
                .filter(Document.project_id == project_id)
                .order_by(Document.order_index.asc(), Document.id.asc())
                .all()
            )

            # 汇总旧稿（标题 + 摘要片段）——跳过归档夹及其子文档
            archive_ids = {
                d.id for d in all_docs
                if (d.title or "").startswith("【归档】")
            }
            digest_parts = []
            for d in all_docs:
                if d.id in archive_ids or (d.parent_id and d.parent_id in archive_ids):
                    continue
                if (d.title or "").startswith("【归档】"):
                    continue
                plain = AIWritingService._blocks_to_plain(d.content)
                if not plain.strip():
                    digest_parts.append(f"- 《{d.title}》：空")
                    continue
                snippet = plain[:400].replace("\n", " ")
                if len(plain) > 800:
                    snippet += " … " + plain[-200:].replace("\n", " ")
                digest_parts.append(f"- 《{d.title}》（约{len(plain)}字）：{snippet}")

            old_digest = "\n".join(digest_parts) if digest_parts else "（尚无旧稿，按设定全新开写）"
            memory = AIMemoryService.get_or_create_memory(db, project_id)
            existing_outline = memory.outline or []
            n_chapters = chapter_count or (
                len(existing_outline) if isinstance(existing_outline, list) and len(existing_outline) >= 2
                else max(5, min(len(all_docs) or 5, 12))
            )

            yield emit({
                "type": "status",
                "step": "outline",
                "message": f"正在根据新设定重新梳理大纲（约 {n_chapters} 章）…",
            })

            outline_prompt = f"""你是资深网文/小说主编。项目设定刚刚大改，需要基于【最新设定】重新梳理章节大纲，并尽量吸收【旧稿要点】中仍然成立的情节。

【最新项目设定】
{memory_context}

【旧稿要点】（可能与新设定冲突，冲突处以新设定为准）
{old_digest}

【要求】
1. 输出恰好 {n_chapters} 个章节
2. 每章含 title、description（本章冲突与推进，2～4 句）
3. 角色名、世界观必须符合最新设定
4. 旧稿里有价值的剧情可改写后保留，废弃设定相关内容丢掉
5. 只输出 JSON，不要其他文字：
{{"outline":[{{"title":"第1章 xxx","description":"..."}},...],"storyline_summary":"一句话主线"}}
"""
            if custom_instruction:
                outline_prompt += f"\n【额外要求】\n{custom_instruction}\n"

            outline_raw = await ai_client.chat_completion(
                [{"role": "user", "content": outline_prompt}],
                max_tokens=4000,
                timeout=180.0,
            )
            new_outline: List[dict] = []
            storyline_summary = ""
            try:
                text = outline_raw or ""
                m = re.search(r"\{.*\}", text, re.DOTALL)
                if m:
                    obj = json.loads(m.group())
                    storyline_summary = (obj.get("storyline_summary") or "").strip()
                    arr = obj.get("outline") or []
                    for item in arr:
                        if isinstance(item, dict) and (item.get("title") or item.get("description")):
                            new_outline.append({
                                "title": (item.get("title") or "未命名章节").strip(),
                                "description": (item.get("description") or item.get("content") or "").strip(),
                            })
            except Exception as e:
                logger.warning(f"rebuild outline parse failed: {e}")

            if not new_outline:
                # 兜底：用旧大纲标题或占位
                if isinstance(existing_outline, list) and existing_outline:
                    for i, item in enumerate(existing_outline[:n_chapters]):
                        if isinstance(item, dict):
                            new_outline.append({
                                "title": item.get("title") or f"第{i+1}章",
                                "description": item.get("description") or "",
                            })
                if not new_outline:
                    new_outline = [
                        {"title": f"第{i+1}章", "description": "按最新设定推进剧情"}
                        for i in range(n_chapters)
                    ]

            if update_outline:
                memory.outline = new_outline
                if storyline_summary:
                    sl = memory.storyline
                    if isinstance(sl, dict):
                        sl = {**sl, "summary": storyline_summary}
                    elif isinstance(sl, str) or sl is None:
                        sl = {"summary": storyline_summary, "stages": []}
                    memory.storyline = sl
                db.commit()

            yield emit({
                "type": "outline_ready",
                "outline": new_outline,
                "message": f"新大纲已梳理完成，共 {len(new_outline)} 章"
                + ("，已写回项目设定" if update_outline else ""),
            })

            # 归档或删除旧文档（仅顶层正文，不含归档夹）
            to_archive = [
                d for d in all_docs
                if d.parent_id is None and not (d.title or "").startswith("【归档】")
            ]
            if to_archive:
                if archive_old_docs:
                    archive = Document(
                        title="【归档】设定变更前旧稿",
                        content=[{
                            "id": "archive_note",
                            "type": "paragraph",
                            "content": "以下为设定变更前的旧章节，仅供对照，不参与新连载结构。",
                            "props": {},
                        }],
                        project_id=project_id,
                        parent_id=None,
                        order_index=9990,
                    )
                    db.add(archive)
                    db.commit()
                    db.refresh(archive)
                    for i, d in enumerate(to_archive):
                        d.parent_id = archive.id
                        d.order_index = i
                    db.commit()
                    yield emit({
                        "type": "archive_done",
                        "archived": len(to_archive),
                        "message": f"已将 {len(to_archive)} 篇旧文档归档到「设定变更前旧稿」",
                    })
                else:
                    for d in to_archive:
                        db.delete(d)
                    db.commit()
                    yield emit({
                        "type": "archive_done",
                        "archived": 0,
                        "deleted": len(to_archive),
                        "message": f"已删除 {len(to_archive)} 篇旧文档",
                    })

            system_prompt = f"""你是专业小说写手。请严格按【最新项目设定】与【本章大纲】撰写正文。
只输出正文，不要章节号说明。
格式：可用 ## 小节标题；对话用 > ；列表用 - ；段落空一行。不要用 ```。

{AIWritingService.ANTI_AI_STYLE_RULES}"""

            previous_summary = ""
            created = []
            for idx, chapter in enumerate(new_outline):
                ch_title = chapter.get("title") or f"第{idx+1}章"
                ch_desc = chapter.get("description") or ""
                yield emit({
                    "type": "doc_start",
                    "index": idx,
                    "total": len(new_outline),
                    "title": ch_title,
                    "message": f"正在生成新章节（{idx+1}/{len(new_outline)}）：{ch_title}",
                })

                user_content = f"""【最新项目设定】
{memory_context}

【本章】{ch_title}
【本章大纲】{ch_desc}
【前文摘要】{previous_summary or '（开篇）'}
【目标字数】约 {words_per_chapter} 字
请撰写本章正文。"""
                if custom_instruction:
                    user_content += f"\n【额外要求】{custom_instruction}"

                chunks: List[str] = []
                try:
                    async for chunk in ai_client.stream_completion(
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        max_tokens=max(4000, words_per_chapter * 3),
                        timeout=300.0,
                    ):
                        if chunk:
                            chunks.append(chunk)
                            yield emit({
                                "type": "content",
                                "index": idx,
                                "chunk": chunk,
                            })
                except Exception as e:
                    yield emit({
                        "type": "error",
                        "message": f"生成「{ch_title}」失败: {e}",
                    })
                    content = f"（生成失败：{e}）\n\n本章要点：{ch_desc}"
                else:
                    content = "".join(chunks).strip() or f"（空）\n\n{ch_desc}"

                blocks = parse_formatted_text_to_blocks(content, f"rb{idx}")
                doc = Document(
                    title=ch_title,
                    content=blocks or [{"id": f"rb{idx}", "type": "paragraph", "content": content, "props": {}}],
                    project_id=project_id,
                    parent_id=None,
                    order_index=idx,
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                created.append({"id": doc.id, "title": doc.title})
                previous_summary = (content[:280] + "…") if len(content) > 280 else content

                yield emit({
                    "type": "doc_done",
                    "index": idx,
                    "total": len(new_outline),
                    "document_id": doc.id,
                    "title": ch_title,
                    "word_count": len(content),
                    "message": f"已生成：{ch_title}",
                })

            yield emit({
                "type": "complete",
                "documents": created,
                "outline": new_outline,
                "message": f"重建完成：新大纲 {len(new_outline)} 章，已生成 {len(created)} 篇文档",
            })
        except Exception as e:
            logger.exception("rebuild_project_from_memory failed")
            yield emit({"type": "error", "message": str(e)})

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
            "6. 使用自然流畅的中文,句子完整连贯;比喻宁少勿多;勿故意堆短句或跳跃断句",
            "7. 关键抉择可有犹豫,但叙述仍要顺;不要写成精确戳中全部软肋的剧本",
            "",
            AIWritingService.ANTI_AI_STYLE_RULES,
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
        style_agent_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """批量/多轮次生成章节内容

        基于大纲节点列表,逐章生成内容,每章完成后发送进度更新
        """
        from app.models.models import Document

        # 获取项目记忆上下文
        memory_context = AIMemoryService.build_memory_context(
            db, project_id, style_agent_id
        )
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
                # 去机感二遍：最终写入/回传用润色稿；流式 content 仍是初稿（前端以 chapter_complete 为准）
                full_chapter = await AIWritingService.humanize_prose(full_chapter)
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
