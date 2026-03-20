"""
AI 自动写作服务
基于大纲设定，逐章生成并插入到对应文档
"""
import json
import re
from typing import AsyncGenerator, Optional, Dict, Any, List
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.services.project_service import ProjectService


class AutoWriteService:
    """AI 自动写作服务"""

    def __init__(
        self,
        llm_service: LLMService,
        document_service: DocumentService,
        project_service: ProjectService
    ):
        self.llm_service = llm_service
        self.document_service = document_service
        self.project_service = project_service

    async def generate_chapters_stream(
        self,
        project_id: int,
        document_id: int,
        outline_nodes: List[Dict[str, Any]],
        max_tokens_per_chapter: int = 8000,
        custom_instruction: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成章节内容
        """
        total_chapters = len(outline_nodes)
        previous_summary = ""

        yield {
            "type": "start",
            "total_chapters": total_chapters,
            "message": f"开始自动写作，共 {total_chapters} 个章节"
        }

        for index, node in enumerate(outline_nodes):
            chapter_num = index + 1

            yield {
                "type": "chapter_start",
                "chapter_index": index,
                "chapter_number": chapter_num,
                "total_chapters": total_chapters,
                "title": node.get("title", f"第{chapter_num}章"),
                "message": f"开始生成第 {chapter_num}/{total_chapters} 章: {node.get('title', '')}"
            }

            # 生成章节内容
            chapter_content = ""
            async for chunk in self._generate_chapter_content_stream(
                node=node,
                chapter_index=index,
                total_chapters=total_chapters,
                max_tokens=max_tokens_per_chapter,
                custom_instruction=custom_instruction,
                previous_chapter_summary=previous_summary
            ):
                if chunk.get("type") == "content":
                    chapter_content += chunk.get("content", "")
                    yield chunk
                elif chunk.get("type") == "complete":
                    # 章节生成完成，保存到文档
                    full_content = chunk.get("full_content", chapter_content)

                    # 保存到文档
                    try:
                        await self._save_chapter_to_document(
                            project_id=project_id,
                            document_id=document_id,
                            node=node,
                            content=full_content,
                            chapter_index=index
                        )

                        # 生成摘要用于下一章
                        previous_summary = await self._generate_chapter_summary(full_content)

                        yield {
                            "type": "chapter_complete",
                            "chapter_index": index,
                            "chapter_number": chapter_num,
                            "title": node.get("title", f"第{chapter_num}章"),
                            "content_length": len(full_content),
                            "summary": previous_summary,
                            "message": f"第 {chapter_num}/{total_chapters} 章生成完成"
                        }
                    except Exception as e:
                        yield {
                            "type": "chapter_error",
                            "chapter_index": index,
                            "error": str(e),
                            "message": f"第 {chapter_num} 章保存失败: {str(e)}"
                        }

        yield {
            "type": "complete",
            "total_chapters": total_chapters,
            "message": "自动写作全部完成"
        }

    async def generate_single_chapter_stream(
        self,
        project_id: int,
        document_id: int,
        node: Dict[str, Any],
        chapter_index: int,
        total_chapters: int,
        max_tokens: int = 8000,
        custom_instruction: Optional[str] = None,
        previous_chapter_summary: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成单个章节 - 流式输出
        """
        chapter_num = chapter_index + 1

        yield {
            "type": "chapter_start",
            "chapter_index": chapter_index,
            "chapter_number": chapter_num,
            "total_chapters": total_chapters,
            "title": node.get("title", f"第{chapter_num}章"),
            "message": f"开始生成第 {chapter_num}/{total_chapters} 章"
        }

        chapter_content = ""
        async for chunk in self._generate_chapter_content_stream(
            node=node,
            chapter_index=chapter_index,
            total_chapters=total_chapters,
            max_tokens=max_tokens,
            custom_instruction=custom_instruction,
            previous_chapter_summary=previous_chapter_summary
        ):
            if chunk.get("type") == "content":
                chapter_content += chunk.get("content", "")
            yield chunk

            if chunk.get("type") == "complete":
                full_content = chunk.get("full_content", chapter_content)

                # 保存到文档
                try:
                    await self._save_chapter_to_document(
                        project_id=project_id,
                        document_id=document_id,
                        node=node,
                        content=full_content,
                        chapter_index=chapter_index
                    )

                    summary = await self._generate_chapter_summary(full_content)

                    yield {
                        "type": "chapter_complete",
                        "chapter_index": chapter_index,
                        "chapter_number": chapter_num,
                        "title": node.get("title", f"第{chapter_num}章"),
                        "content_length": len(full_content),
                        "summary": summary,
                        "message": f"第 {chapter_num}/{total_chapters} 章生成完成"
                    }
                except Exception as e:
                    yield {
                        "type": "chapter_error",
                        "chapter_index": chapter_index,
                        "error": str(e),
                        "message": f"保存失败: {str(e)}"
                    }

    async def batch_generate_stream(
        self,
        project_id: int,
        document_id: int,
        outline_nodes: List[Dict[str, Any]],
        max_tokens_per_chapter: int = 8000,
        custom_instruction: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        批量生成多个章节 - 流式输出
        """
        total_chapters = len(outline_nodes)
        previous_summary = ""

        yield {
            "type": "start",
            "total_chapters": total_chapters,
            "message": f"开始批量生成，共 {total_chapters} 个章节"
        }

        for index, node in enumerate(outline_nodes):
            async for event in self.generate_single_chapter_stream(
                project_id=project_id,
                document_id=document_id,
                node=node,
                chapter_index=index,
                total_chapters=total_chapters,
                max_tokens=max_tokens_per_chapter,
                custom_instruction=custom_instruction,
                previous_chapter_summary=previous_summary
            ):
                if event.get("type") == "chapter_complete":
                    previous_summary = event.get("summary", "")
                yield event

        yield {
            "type": "complete",
            "total_chapters": total_chapters,
            "message": "批量生成全部完成"
        }

    SINGLE_CALL_TOKEN_LIMIT = 8192

    async def _generate_chapter_content_stream(
        self,
        node: Dict[str, Any],
        chapter_index: int,
        total_chapters: int,
        max_tokens: int = 8000,
        custom_instruction: Optional[str] = None,
        previous_chapter_summary: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成单个章节内容。
        当 max_tokens 超过 API 单次上限时自动分段续写。
        """
        title = node.get("title", f"第{chapter_index + 1}章")
        description = node.get("description", "")
        key_points = node.get("keyPoints", [])
        target_word_count = node.get("targetWordCount", 1500)

        prompt = self._build_chapter_prompt(
            title=title,
            description=description,
            key_points=key_points,
            chapter_index=chapter_index,
            total_chapters=total_chapters,
            target_word_count=target_word_count,
            custom_instruction=custom_instruction,
            previous_chapter_summary=previous_chapter_summary
        )

        full_content = ""
        target_chars = int(max_tokens * 0.7)
        max_rounds = max(1, (max_tokens // self.SINGLE_CALL_TOKEN_LIMIT) + 1)
        tokens_per_call = min(max_tokens, self.SINGLE_CALL_TOKEN_LIMIT)

        try:
            for round_idx in range(max_rounds):
                current_prompt = prompt if round_idx == 0 else (
                    f"请继续创作以下章节的后续内容，直接从断点处衔接，不要重复已有内容。\n\n"
                    f"章节标题：{title}\n"
                    f"目标总字数：{target_word_count}字\n"
                    f"已写约{len(full_content)}字，还需约{max(0, target_word_count - len(full_content))}字\n\n"
                    f"--- 已有内容（末尾）---\n{full_content[-800:]}\n\n"
                    f"--- 请从此处继续 ---\n"
                )

                async for chunk in self.llm_service.generate_stream(
                    current_prompt, max_tokens=tokens_per_call
                ):
                    content = chunk if isinstance(chunk, str) else chunk.get("content", "")
                    full_content += content
                    yield {
                        "type": "content",
                        "chapter_index": chapter_index,
                        "content": content,
                        "full_content_so_far": full_content
                    }

                if len(full_content) >= target_chars:
                    break

            yield {
                "type": "complete",
                "chapter_index": chapter_index,
                "full_content": full_content
            }

        except Exception as e:
            yield {
                "type": "error",
                "chapter_index": chapter_index,
                "error": str(e)
            }

    def _build_chapter_prompt(
        self,
        title: str,
        description: str,
        key_points: List[str],
        chapter_index: int,
        total_chapters: int,
        target_word_count: int,
        custom_instruction: Optional[str] = None,
        previous_chapter_summary: Optional[str] = None
    ) -> str:
        """
        构建章节生成提示词
        """
        chapter_num = chapter_index + 1

        prompt = f"""你是一位专业的网文作家，请根据以下大纲信息创作第{chapter_num}章内容。

## 章节信息
- 章节标题: {title}
- 章节描述: {description}
- 目标字数: {target_word_count}字左右
- 当前进度: 第{chapter_num}章 / 共{total_chapters}章
"""

        if key_points:
            prompt += "\n## 必须包含的关键点\n"
            for i, point in enumerate(key_points, 1):
                prompt += f"{i}. {point}\n"

        if previous_chapter_summary:
            prompt += f"\n## 前一章摘要（用于保持连贯性）\n{previous_chapter_summary}\n"

        if custom_instruction:
            prompt += f"\n## 自定义要求\n{custom_instruction}\n"

        prompt += f"""
## 写作要求
1. 直接输出章节正文内容，不要包含"第X章"或章节标题
2. 情节要有吸引力，节奏紧凑，避免拖沓
3. 人物对话要自然，符合角色性格
4. 场景描写要生动，让读者有画面感
5. 字数控制在{target_word_count}字左右
6. 确保与前一章内容连贯（如有提供摘要）
7. 在关键点处自然展开，不要生硬堆砌

请开始创作：
"""

        return prompt

    async def _save_chapter_to_document(
        self,
        project_id: int,
        document_id: int,
        node: Dict[str, Any],
        content: str,
        chapter_index: int
    ):
        """
        将生成的章节保存到文档
        """
        # 格式化章节内容
        title = node.get("title", f"第{chapter_index + 1}章")
        formatted_content = f"\n\n## {title}\n\n{content}\n"

        # 获取当前文档内容
        doc = await self.document_service.get_document(project_id, document_id)
        if not doc:
            raise ValueError(f"文档不存在: {document_id}")

        current_content = doc.get("content", "")

        # 检查是否已有该章节，有则更新，无则追加
        chapter_marker = f"## {title}"
        if chapter_marker in current_content:
            # 更新已有章节
            pattern = f"{re.escape(chapter_marker)}.*?(?=## |$)"
            updated_content = re.sub(
                pattern,
                formatted_content.strip() + "\n\n",
                current_content,
                flags=re.DOTALL
            )
        else:
            # 追加新章节
            updated_content = current_content + formatted_content

        # 保存文档
        await self.document_service.update_document(
            project_id=project_id,
            document_id=document_id,
            content=updated_content
        )

    async def _generate_chapter_summary(self, content: str, max_length: int = 200) -> str:
        """
        生成章节摘要，用于保持章节间连贯性
        """
        prompt = f"""请对以下章节内容进行简要总结，提取关键情节和转折点，用于帮助下一章保持连贯性。控制在{max_length}字以内：

{content[:3000]}  # 只取前3000字用于摘要

请输出简要摘要："""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=300)
            return response.strip()[:max_length]
        except Exception:
            return ""
