"""
长篇文章生成服务 - 支持百万字级别的文章生成
核心功能:
1. 智能大纲生成（多级章节结构）
2. 分块生成（章节级别）
3. 上下文管理（保持连贯性）
4. 进度追踪（实时反馈）
5. 断点续写（支持暂停/恢复）
"""

from typing import Optional, AsyncGenerator, Dict, List, Any
from sqlalchemy.orm import Session
from app.models.models import Article, ArticleChapter, ArticleOutline
from app.core.ai_client import get_ai_client
from app.config.long_article_config import LongArticleConfig
import json
import re
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
        生成文章大纲（智能分配章节字数）
        :param article_id: 文章ID
        :param topic: 文章主题
        :param target_words: 目标字数
        :param style: 写作风格
        :param requirements: 额外要求
        :return: 大纲结构
        """
        # 根据目标字数智能计算章节数
        chapter_count = LongArticleConfig.get_chapter_count(target_words)

        # 构建大纲生成提示词
        prompt = self._build_outline_prompt(
            topic, target_words, chapter_count, style, requirements
        )

        # 调用AI生成大纲
        messages = [{"role": "user", "content": prompt}]
        response = await self.ai_client.chat_completion(
            messages=messages, 
            temperature=LongArticleConfig.OUTLINE_TEMPERATURE, 
            max_tokens=LongArticleConfig.OUTLINE_MAX_TOKENS
        )

        # 解析大纲
        outline_data = self._parse_outline(response)
        
        # 智能调整章节字数分配，确保总和接近目标
        self._adjust_chapter_word_distribution(outline_data, target_words)

        # 保存大纲到数据库
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.outline = json.dumps(outline_data, ensure_ascii=False)
            article.status = "outlined"
            self.db.commit()

        return outline_data

    @staticmethod
    def outline_from_story(story_data: Dict[str, Any], target_words: int) -> Dict:
        """
        将 AI 故事生成器的大纲转为长篇文章大纲格式，并嵌入 story_context 供章节生成使用。
        """
        acts = story_data.get("outline") or []
        theme = story_data.get("input_theme") or story_data.get("core_theme") or "故事"
        title = (story_data.get("title_options") or [None])[0] or theme
        genre = story_data.get("genre") or "文学叙事"
        style = story_data.get("writing_style") or {}
        style_str = style.get("tone") or genre

        def parse_words(w: Any) -> int:
            if w is None:
                return 0
            if isinstance(w, int):
                return max(0, w)
            s = re.sub(r"[^\d]", "", str(w))
            return int(s) if s else 0

        chapters = []
        for i, act in enumerate(acts):
            if isinstance(act, dict):
                act_title = act.get("title") or act.get("act") or f"第{i+1}幕"
                content = act.get("content") or ""
                key_points = [p.strip() for p in content.split("。") if p.strip()][:5]
                if not key_points and content:
                    key_points = [content[:200]]
                est = parse_words(act.get("word_count_estimate"))
                chapters.append({
                    "title": act_title,
                    "key_points": key_points or [act_title],
                    "target_words": est or max(LongArticleConfig.MIN_CHAPTER_WORDS, target_words // max(1, len(acts))),
                })
            else:
                chapters.append({
                    "title": f"第{i+1}幕",
                    "key_points": [],
                    "target_words": target_words // max(1, len(acts)),
                })

        if not chapters:
            chapter_count = LongArticleConfig.get_chapter_count(target_words)
            avg = target_words // chapter_count
            chapters = [
                {"title": f"第{i+1}章", "key_points": [], "target_words": avg}
                for i in range(chapter_count)
            ]
        else:
            LongArticleService._adjust_chapter_word_distribution_static(
                chapters, target_words
            )

        intro = story_data.get("core_theme") or theme
        if isinstance(intro, str) and len(intro) > 300:
            intro = intro[:300] + "..."

        return {
            "title": title,
            "introduction": intro,
            "topic": theme,
            "style": style_str,
            "chapters": chapters,
            "story_context": story_data,
        }

    @staticmethod
    def _adjust_chapter_word_distribution_static(chapters: List[Dict], target_words: int):
        """静态方法：调整章节字数分配"""
        if not chapters:
            return
        current_total = sum(ch.get("target_words", 8000) for ch in chapters)
        if current_total == 0:
            avg = target_words // len(chapters)
            for ch in chapters:
                ch["target_words"] = avg
        else:
            ratio = target_words / current_total
            for ch in chapters:
                ch["target_words"] = int(ch.get("target_words", 8000) * ratio)
        for ch in chapters:
            ch["target_words"] = max(
                LongArticleConfig.MIN_CHAPTER_WORDS,
                min(LongArticleConfig.MAX_CHAPTER_WORDS, ch["target_words"]),
            )

    def _adjust_chapter_word_distribution(self, outline: Dict, target_words: int):
        """智能调整章节字数分配"""
        chapters = outline.get("chapters", [])
        if not chapters:
            return
        
        # 计算当前总字数
        current_total = sum(ch.get("target_words", 8000) for ch in chapters)
        
        if current_total == 0:
            # 如果没有设置字数，平均分配
            avg_words = target_words // len(chapters)
            for ch in chapters:
                ch["target_words"] = avg_words
        else:
            # 按比例调整
            ratio = target_words / current_total
            for ch in chapters:
                ch["target_words"] = int(ch.get("target_words", 8000) * ratio)
        
        # 确保每章字数在合理范围内
        for ch in chapters:
            ch["target_words"] = max(
                LongArticleConfig.MIN_CHAPTER_WORDS, 
                min(LongArticleConfig.MAX_CHAPTER_WORDS, ch["target_words"])
            )

    async def generate_chapter(
        self,
        article_id: int,
        chapter_index: int,
        outline: Dict,
        previous_content: Optional[str] = None,
        retry_count: int = 0,
    ) -> AsyncGenerator[str, None]:
        """
        生成单个章节内容（流式，支持段落级拆分，带重试机制）
        :param article_id: 文章ID
        :param chapter_index: 章节索引
        :param outline: 完整大纲
        :param previous_content: 前一章节的内容摘要（用于保持连贯性）
        :param retry_count: 当前重试次数
        """
        try:
            chapter_info = outline["chapters"][chapter_index]
            target_words = chapter_info.get("target_words", 8000)
            
            # 如果章节目标字数超过阈值，拆分为多个段落生成
            if LongArticleConfig.should_split_to_sections(target_words):
                full_content = ""
                async for chunk in self._generate_chapter_by_sections(
                    article_id, chapter_index, outline, chapter_info, previous_content
                ):
                    full_content += chunk
                    yield chunk
                
                # 保存章节到数据库
                self._save_chapter(article_id, chapter_index, chapter_info, full_content)
            else:
                # 小章节直接生成
                prompt = self._build_chapter_prompt(
                    outline.get("topic", ""),
                    outline.get("style", "专业"),
                    chapter_info,
                    chapter_index,
                    len(outline["chapters"]),
                    previous_content,
                    story_context=outline.get("story_context"),
                )

                messages = [{"role": "user", "content": prompt}]

                full_content = ""
                async for chunk in self.ai_client.stream_completion(
                    messages=messages, 
                    temperature=LongArticleConfig.CHAPTER_TEMPERATURE, 
                    max_tokens=LongArticleConfig.CHAPTER_MAX_TOKENS
                ):
                    full_content += chunk
                    yield chunk

                self._save_chapter(article_id, chapter_index, chapter_info, full_content)
        
        except Exception as e:
            # 错误重试机制
            if retry_count < LongArticleConfig.MAX_RETRIES:
                await asyncio.sleep(LongArticleConfig.RETRY_DELAY)
                async for chunk in self.generate_chapter(
                    article_id, chapter_index, outline, previous_content, retry_count + 1
                ):
                    yield chunk
            else:
                # 超过最大重试次数，抛出异常
                raise Exception(f"章节 {chapter_index + 1} 生成失败，已重试 {retry_count} 次: {str(e)}")

    async def _generate_chapter_by_sections(
        self,
        article_id: int,
        chapter_index: int,
        outline: Dict,
        chapter_info: Dict,
        previous_content: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        按段落拆分生成章节（突破单次生成字数限制）
        """
        target_words = chapter_info.get("target_words", 8000)
        key_points = chapter_info.get("key_points", [])
        
        # 计算段落数
        section_count = LongArticleConfig.calculate_section_count(target_words)
        section_target_words = target_words // section_count
        
        # 将关键点分配到各段落
        points_per_section = max(1, len(key_points) // section_count)
        
        chapter_content = ""
        
        for section_idx in range(section_count):
            # 确定本段落的关键点
            start_point = section_idx * points_per_section
            end_point = start_point + points_per_section if section_idx < section_count - 1 else len(key_points)
            section_points = key_points[start_point:end_point] if key_points else []
            
            # 构建段落生成提示词
            prompt = self._build_section_prompt(
                outline.get("topic", ""),
                outline.get("style", "专业"),
                chapter_info["title"],
                section_idx,
                section_count,
                section_points,
                section_target_words,
                previous_content if section_idx == 0 else chapter_content[-LongArticleConfig.SECTION_CONTEXT_LENGTH:],
                story_context=outline.get("story_context"),
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            # 生成段落内容
            section_content = ""
            async for chunk in self.ai_client.stream_completion(
                messages=messages, 
                temperature=LongArticleConfig.CHAPTER_TEMPERATURE, 
                max_tokens=LongArticleConfig.SECTION_MAX_TOKENS
            ):
                section_content += chunk
                chapter_content += chunk
                yield chunk
            
            # 段落间添加换行
            if section_idx < section_count - 1:
                yield "\n\n"
                chapter_content += "\n\n"

    async def generate_full_article(
        self,
        article_id: int,
        topic: str,
        target_words: int,
        style: str = "专业",
        requirements: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        生成完整长篇文章（带进度反馈，支持多章节上下文）
        :param article_id: 文章ID
        :param topic: 文章主题
        :param target_words: 目标字数
        :param style: 写作风格
        :param requirements: 额外要求
        :yield: 进度信息 {"type": "outline|chapter|progress|complete", "data": ...}
        """
        try:
            article = self.db.query(Article).filter(Article.id == article_id).first()
            # 1. 大纲：若已有（如从故事生成器导入）则直接使用，否则调用 AI 生成
            yield {
                "type": "progress",
                "data": {"stage": "outline", "progress": 0, "message": "正在准备大纲..."},
            }

            if article and article.outline and isinstance(article.outline, dict) and article.outline.get("chapters"):
                outline = article.outline
            else:
                outline = await self.generate_outline(
                    article_id, topic, target_words, style, requirements
                )

            yield {
                "type": "outline",
                "data": outline,
            }

            # 2. 逐章节生成（支持多章节上下文；若 outline 含 story_context 则注入到章节提示）
            total_chapters = len(outline["chapters"])
            chapter_summaries = []  # 存储所有章节摘要
            context_window = 3  # 上下文窗口：使用最近3章的摘要

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

                # 构建多章节上下文
                context = self._build_multi_chapter_context(
                    chapter_summaries, context_window, i, total_chapters
                )

                # 生成章节内容
                chapter_content = ""
                async for chunk in self.generate_chapter(
                    article_id, i, outline, context
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

                # 生成章节摘要并存储
                summary = await self._generate_summary(
                    chapter_content, 
                    max_length=LongArticleConfig.SUMMARY_MAX_LENGTH
                )
                chapter_summaries.append({
                    "index": i,
                    "title": chapter_info["title"],
                    "summary": summary
                })

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

        outline = article.outline if isinstance(article.outline, dict) else json.loads(article.outline or "{}")
        
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
        story_context: Optional[Dict] = None,
    ) -> str:
        """构建章节生成提示词；若提供 story_context 则按故事设定写长文"""
        if story_context:
            prompt = """你是一位擅长长篇叙事的作家，正在根据已有故事设定撰写长篇小说章节。

【故事设定】
"""
            prompt += f"核心主题：{story_context.get('core_theme') or topic}\n"
            if story_context.get("characters"):
                prompt += "主要角色：\n"
                for c in (story_context["characters"] or [])[:8]:
                    if isinstance(c, dict):
                        prompt += f"- {c.get('name', '')}：{c.get('role', '')}；{c.get('personality') or c.get('description', '')}\n"
            if story_context.get("world_building") and isinstance(story_context["world_building"], dict):
                w = story_context["world_building"]
                prompt += f"世界观：{w.get('time_period', '')} {w.get('location', '')}；{w.get('atmosphere', '')}\n"
            if story_context.get("writing_style") and isinstance(story_context["writing_style"], dict):
                prompt += f"写作风格建议：{story_context['writing_style'].get('tone', '')}；{story_context['writing_style'].get('pov', '')}\n"
            prompt += f"""

当前任务：撰写第 {chapter_index + 1}/{total_chapters} 章

章节标题：{chapter_info['title']}
章节要点：
"""
        else:
            prompt = f"""你是一位专业的内容创作者，正在撰写一篇关于"{topic}"的长篇文章。

当前任务: 撰写第 {chapter_index + 1}/{total_chapters} 章

章节标题: {chapter_info['title']}
章节要点:
"""

        for i, point in enumerate(chapter_info.get("key_points") or [], 1):
            prompt += f"{i}. {point}\n"

        prompt += f"\n目标字数: {chapter_info.get('target_words', 8000)} 字\n"
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

【格式约定】为便于自动排版，请适当使用：小节标题单独一行以 ## 开头；对话/引用以 > 开头；列表以 - 开头；段落之间空一行。不要使用 ``` 等代码块标记。

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
            messages=messages, 
            temperature=LongArticleConfig.SUMMARY_TEMPERATURE, 
            max_tokens=LongArticleConfig.SUMMARY_MAX_TOKENS
        )
        return summary

    def _build_section_prompt(
        self,
        topic: str,
        style: str,
        chapter_title: str,
        section_index: int,
        total_sections: int,
        section_points: List[str],
        target_words: int,
        previous_context: Optional[str] = None,
        story_context: Optional[Dict] = None,
    ) -> str:
        """构建段落生成提示词；若提供 story_context 则按故事设定写"""
        if story_context:
            prompt = """你是一位擅长长篇叙事的作家，正在根据已有故事设定撰写长篇小说。

【故事设定】请严格遵循已有人物、世界观与风格。核心主题与角色设定见前文。

"""
        else:
            prompt = ""
        prompt += f"""你是一位专业的{style}作家，正在创作一篇关于"{topic}"的长篇文章。

当前任务：撰写《{chapter_title}》章节的第 {section_index + 1}/{total_sections} 段

目标字数：约 {target_words} 字

"""
        if section_points:
            prompt += f"本段要点：\n"
            for point in section_points:
                prompt += f"- {point}\n"
            prompt += "\n"

        if previous_context:
            prompt += f"前文内容（用于保持连贯）：\n...{previous_context}\n\n"

        prompt += """写作要求：
1. 内容充实，达到目标字数
2. 与前文自然衔接，保持连贯性
3. 覆盖本段的关键要点
4. 语言流畅，符合指定风格
5. 如果是首段，可以有引入性内容；如果是末段，可以有总结性内容
6. 可适当用 ## 小节、> 对话/引用、- 列表，段落间空一行。不要使用 ``` 代码块。

请直接输出段落正文内容："""

        return prompt

    def _build_multi_chapter_context(
        self,
        chapter_summaries: List[Dict],
        context_window: int,
        current_index: int,
        total_chapters: int,
    ) -> Optional[str]:
        """
        构建多章节上下文（使用最近N章的摘要）
        :param chapter_summaries: 所有章节摘要列表
        :param context_window: 上下文窗口大小
        :param current_index: 当前章节索引
        :param total_chapters: 总章节数
        :return: 上下文字符串
        """
        if not chapter_summaries:
            return None
        
        # 获取最近N章的摘要
        start_idx = max(0, len(chapter_summaries) - context_window)
        recent_summaries = chapter_summaries[start_idx:]
        
        if not recent_summaries:
            return None
        
        context = f"前文回顾（第 {current_index + 1}/{total_chapters} 章）：\n\n"
        
        for summary_info in recent_summaries:
            context += f"【第 {summary_info['index'] + 1} 章：{summary_info['title']}】\n"
            context += f"{summary_info['summary']}\n\n"
        
        return context

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
