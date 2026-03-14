"""
长篇文章生成服务 - 支持百万字级别的文章生成
核心功能:
1. 智能大纲生成（多级章节结构）
2. 分块生成（章节级别）
3. 上下文管理（保持连贯性）
4. 进度追踪（实时反馈）
5. 断点续写（支持暂停/恢复）
"""

from typing import Optional, AsyncGenerator, Dict, List
from sqlalchemy.orm import Session
from app.models.models import Article, ArticleChapter, ArticleOutline
from app.core.ai_client import get_ai_client
import json
from datetime import datetime
import asyncio


class LongArticleService:
    """长篇文章生成服务"""

    def __init__(self, db: Session):
        self.db = db
        self.ai_client = get_ai_client(db)

    async def generate_outline(
        self,
        article_id: int,
        topic: str,
        target_words: int,
        style: str = "专业",
        requirements: Optional[str] = None,
    ) -> Dict:
        """
        生成文章大纲
        :param article_id: 文章ID
        :param topic: 文章主题
        :param target_words: 目标字数
        :param style: 写作风格
        :param requirements: 额外要求
        :return: 大纲结构
        """
        # 计算章节数量（每章约5000-10000字）
        avg_chapter_words = 8000
        chapter_count = max(10, target_words // avg_chapter_words)

        # 构建大纲生成提示词
        prompt = self._build_outline_prompt(
            topic, target_words, chapter_count, style, requirements
        )

        # 调用AI生成大纲
        messages = [{"role": "user", "content": prompt}]
        response = await self.ai_client.chat_completion(
            messages=messages, temperature=0.7, max_tokens=4000
        )

        # 解析大纲
        outline_data = self._parse_outline(response)

        # 保存大纲到数据库
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.outline = json.dumps(outline_data, ensure_ascii=False)
            article.status = "outlined"
            self.db.commit()

        return outline_data

    async def generate_chapter(
        self,
        article_id: int,
        chapter_index: int,
        outline: Dict,
        previous_content: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        生成单个章节内容（流式）
        :param article_id: 文章ID
        :param chapter_index: 章节索引
        :param outline: 完整大纲
        :param previous_content: 前一章节的内容摘要（用于保持连贯性）
        """
        chapter_info = outline["chapters"][chapter_index]
        
        # 构建章节生成提示词
        prompt = self._build_chapter_prompt(
            outline["topic"],
            outline["style"],
            chapter_info,
            chapter_index,
            len(outline["chapters"]),
            previous_content,
        )

        messages = [{"role": "user", "content": prompt}]

        # 流式生成章节内容
        full_content = ""
        async for chunk in self.ai_client.stream_completion(
            messages=messages, temperature=0.8, max_tokens=8000
        ):
            full_content += chunk
            yield chunk

        # 保存章节到数据库
        self._save_chapter(article_id, chapter_index, chapter_info, full_content)

    async def generate_full_article(
        self,
        article_id: int,
        topic: str,
        target_words: int,
        style: str = "专业",
        requirements: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        生成完整长篇文章（带进度反馈）
        :param article_id: 文章ID
        :param topic: 文章主题
        :param target_words: 目标字数
        :param style: 写作风格
        :param requirements: 额外要求
        :yield: 进度信息 {"type": "outline|chapter|progress|complete", "data": ...}
        """
        try:
            # 1. 生成大纲
            yield {
                "type": "progress",
                "data": {"stage": "outline", "progress": 0, "message": "正在生成文章大纲..."},
            }

            outline = await self.generate_outline(
                article_id, topic, target_words, style, requirements
            )

            yield {
                "type": "outline",
                "data": outline,
            }

            # 2. 逐章节生成
            total_chapters = len(outline["chapters"])
            previous_summary = None

            for i, chapter_info in enumerate(outline["chapters"]):
                # 发送章节开始信号
                yield {
                    "type": "progress",
                    "data": {
                        "stage": "chapter",
                        "chapter_index": i,
                        "chapter_title": chapter_info["title"],
                        "progress": int((i / total_chapters) * 100),
                        "message": f"正在生成第 {i+1}/{total_chapters} 章: {chapter_info['title']}",
                    },
                }

                # 生成章节内容
                chapter_content = ""
                async for chunk in self.generate_chapter(
                    article_id, i, outline, previous_summary
                ):
                    chapter_content += chunk
                    # 实时推送章节内容
                    yield {
                        "type": "chapter_chunk",
                        "data": {
                            "chapter_index": i,
                            "chunk": chunk,
                        },
                    }

                # 生成章节摘要（用于下一章的上下文）
                previous_summary = await self._generate_summary(chapter_content)

                # 章节完成
                yield {
                    "type": "chapter_complete",
                    "data": {
                        "chapter_index": i,
                        "word_count": len(chapter_content),
                    },
                }

            # 3. 生成完成
            article = self.db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.status = "completed"
                article.completed_at = datetime.utcnow()
                self.db.commit()

            yield {
                "type": "complete",
                "data": {
                    "article_id": article_id,
                    "total_chapters": total_chapters,
                    "message": "文章生成完成！",
                },
            }

        except Exception as e:
            yield {
                "type": "error",
                "data": {"message": str(e)},
            }

    async def resume_generation(
        self, article_id: int
    ) -> AsyncGenerator[Dict, None]:
        """
        恢复未完成的文章生成
        """
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if not article or not article.outline:
            raise ValueError("文章不存在或未生成大纲")

        outline = json.loads(article.outline)
        
        # 查找已完成的章节
        completed_chapters = (
            self.db.query(ArticleChapter)
            .filter(ArticleChapter.article_id == article_id)
            .order_by(ArticleChapter.chapter_index)
            .all()
        )
        
        completed_indices = {ch.chapter_index for ch in completed_chapters}
        total_chapters = len(outline["chapters"])

        # 从未完成的章节继续
        previous_summary = None
        if completed_chapters:
            last_chapter = completed_chapters[-1]
            previous_summary = await self._generate_summary(last_chapter.content)

        for i, chapter_info in enumerate(outline["chapters"]):
            if i in completed_indices:
                continue

            yield {
                "type": "progress",
                "data": {
                    "stage": "chapter",
                    "chapter_index": i,
                    "chapter_title": chapter_info["title"],
                    "progress": int((i / total_chapters) * 100),
                    "message": f"正在生成第 {i+1}/{total_chapters} 章: {chapter_info['title']}",
                },
            }

            chapter_content = ""
            async for chunk in self.generate_chapter(
                article_id, i, outline, previous_summary
            ):
                chapter_content += chunk
                yield {
                    "type": "chapter_chunk",
                    "data": {"chapter_index": i, "chunk": chunk},
                }

            previous_summary = await self._generate_summary(chapter_content)

            yield {
                "type": "chapter_complete",
                "data": {"chapter_index": i, "word_count": len(chapter_content)},
            }

        article.status = "completed"
        article.completed_at = datetime.utcnow()
        self.db.commit()

        yield {
            "type": "complete",
            "data": {"article_id": article_id, "message": "文章生成完成！"},
        }

    def _build_outline_prompt(
        self,
        topic: str,
        target_words: int,
        chapter_count: int,
        style: str,
        requirements: Optional[str] = None,
    ) -> str:
        """构建大纲生成提示词"""
        prompt = f"""你是一位专业的内容策划师，请为以下主题生成一个详细的文章大纲。

主题: {topic}
目标字数: {target_words:,} 字
章节数量: {chapter_count} 章
写作风格: {style}
"""
        if requirements:
            prompt += f"额外要求: {requirements}\n"

        prompt += f"""
请生成一个结构化的大纲，包含以下内容：
1. 文章标题（吸引人且准确）
2. 文章简介（200字左右）
3. {chapter_count}个章节，每个章节包含：
   - 章节标题
   - 章节要点（3-5个关键点）
   - 预计字数（总和约{target_words:,}字）

请以JSON格式返回，格式如下：
{{
  "title": "文章标题",
  "introduction": "文章简介",
  "topic": "{topic}",
  "style": "{style}",
  "chapters": [
    {{
      "title": "第一章标题",
      "key_points": ["要点1", "要点2", "要点3"],
      "target_words": 8000
    }},
    ...
  ]
}}
"""
        return prompt

    def _build_chapter_prompt(
        self,
        topic: str,
        style: str,
        chapter_info: Dict,
        chapter_index: int,
        total_chapters: int,
        previous_summary: Optional[str] = None,
    ) -> str:
        """构建章节生成提示词"""
        prompt = f"""你是一位专业的内容创作者，正在撰写一篇关于"{topic}"的长篇文章。

当前任务: 撰写第 {chapter_index + 1}/{total_chapters} 章

章节标题: {chapter_info['title']}
章节要点:
"""
        for i, point in enumerate(chapter_info['key_points'], 1):
            prompt += f"{i}. {point}\n"

        prompt += f"\n目标字数: {chapter_info['target_words']} 字\n"
        prompt += f"写作风格: {style}\n"

        if previous_summary:
            prompt += f"\n前一章节摘要:\n{previous_summary}\n"
            prompt += "\n请确保本章内容与前文自然衔接。\n"

        prompt += """
写作要求:
1. 内容充实，论述深入，避免空洞
2. 逻辑清晰，结构完整
3. 语言流畅，符合指定风格
4. 适当使用案例、数据支撑观点
5. 达到目标字数要求

请直接输出章节正文内容，不要包含章节标题。
"""
        return prompt

    def _parse_outline(self, response: str) -> Dict:
        """解析AI返回的大纲"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(response)
        except Exception as e:
            raise ValueError(f"大纲解析失败: {str(e)}")

    def _save_chapter(
        self, article_id: int, chapter_index: int, chapter_info: Dict, content: str
    ):
        """保存章节到数据库"""
        chapter = ArticleChapter(
            article_id=article_id,
            chapter_index=chapter_index,
            title=chapter_info["title"],
            content=content,
            word_count=len(content),
        )
        self.db.add(chapter)
        self.db.commit()

    async def _generate_summary(self, content: str, max_length: int = 500) -> str:
        """生成内容摘要（用于上下文传递）"""
        if len(content) <= max_length:
            return content

        prompt = f"""请将以下内容总结为{max_length}字以内的摘要，保留关键信息和核心观点：

{content[:3000]}

摘要:"""

        messages = [{"role": "user", "content": prompt}]
        summary = await self.ai_client.chat_completion(
            messages=messages, temperature=0.3, max_tokens=1000
        )
        return summary

    def get_article_progress(self, article_id: int) -> Dict:
        """获取文章生成进度"""
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise ValueError("文章不存在")

        if not article.outline:
            return {
                "status": article.status,
                "progress": 0,
                "total_chapters": 0,
                "completed_chapters": 0,
            }

        outline = json.loads(article.outline)
        total_chapters = len(outline["chapters"])
        
        completed_chapters = (
            self.db.query(ArticleChapter)
            .filter(ArticleChapter.article_id == article_id)
            .count()
        )

        return {
            "status": article.status,
            "progress": int((completed_chapters / total_chapters) * 100) if total_chapters > 0 else 0,
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "outline": outline,
        }
