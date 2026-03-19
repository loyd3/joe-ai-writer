"""
增强版长文本写作服务
支持更长的文本生成、智能大纲规划和章节管理
"""
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field
from app.services.llm_service import LLMService


@dataclass
class Chapter:
    """章节数据结构"""
    id: str
    title: str
    summary: str = ""
    word_count: int = 2000
    key_points: List[str] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    scenes: List[str] = field(default_factory=list)
    content: str = ""
    status: str = "pending"  # pending, writing, completed
    order: int = 0


@dataclass
class LongArticlePlan:
    """长文本写作计划"""
    id: str
    title: str
    subtitle: str = ""
    total_word_count: int = 10000
    chapter_count: int = 5
    style: str = "专业"
    genre: str = "评论"
    theme: str = ""
    target_audience: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    characters: List[Dict] = field(default_factory=list)
    world_building: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class EnhancedLongArticleService:
    """增强版长文本写作服务"""

    # 文章类型定义
    ARTICLE_TYPES = {
        "novel": {"name": "小说", "min_words": 10000, "max_words": 500000, "default_words": 50000},
        "commentary": {"name": "评论", "min_words": 2000, "max_words": 20000, "default_words": 5000},
        "report": {"name": "报告", "min_words": 3000, "max_words": 50000, "default_words": 10000},
        "story": {"name": "故事", "min_words": 3000, "max_words": 100000, "default_words": 8000},
        "essay": {"name": "散文", "min_words": 2000, "max_words": 20000, "default_words": 5000},
        "script": {"name": "剧本", "min_words": 5000, "max_words": 100000, "default_words": 15000},
        "thesis": {"name": "论文", "min_words": 5000, "max_words": 100000, "default_words": 15000}
    }

    # 写作风格
    WRITING_STYLES = [
        "专业严谨", "轻松幽默", "深情细腻", "犀利批判",
        "温暖治愈", "悬疑紧张", "史诗宏大", "简洁明快"
    ]

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self._plans: Dict[str, LongArticlePlan] = {}

    def get_article_types(self) -> List[Dict[str, Any]]:
        """获取文章类型列表"""
        return [
            {"id": key, **value}
            for key, value in self.ARTICLE_TYPES.items()
        ]

    def get_writing_styles(self) -> List[str]:
        """获取写作风格列表"""
        return self.WRITING_STYLES

    async def create_plan(
        self,
        title: str,
        article_type: str = "novel",
        total_word_count: Optional[int] = None,
        style: str = "专业严谨",
        theme: str = "",
        target_audience: str = "",
        requirements: str = ""
    ) -> LongArticlePlan:
        """
        创建长文本写作计划
        """
        type_info = self.ARTICLE_TYPES.get(article_type, self.ARTICLE_TYPES["novel"])

        # 确定字数
        if total_word_count is None:
            total_word_count = type_info["default_words"]
        else:
            total_word_count = max(type_info["min_words"], min(type_info["max_words"], total_word_count))

        # 计算章节数
        chapter_count = max(3, min(20, total_word_count // 3000))

        plan = LongArticlePlan(
            id=f"plan_{datetime.now().timestamp()}",
            title=title,
            total_word_count=total_word_count,
            chapter_count=chapter_count,
            style=style,
            genre=type_info["name"],
            theme=theme,
            target_audience=target_audience
        )

        # 生成大纲
        await self._generate_outline(plan, requirements)

        # 保存计划
        self._plans[plan.id] = plan

        return plan

    async def _generate_outline(self, plan: LongArticlePlan, requirements: str):
        """生成文章大纲"""
        prompt = f"""请为以下长文本创作生成详细大纲：

标题: {plan.title}
类型: {plan.genre}
总字数: {plan.total_word_count}字
章节数: {plan.chapter_count}章
写作风格: {plan.style}
主题: {plan.theme}
目标读者: {plan.target_audience}

特殊要求: {requirements}

请生成：
1. 副标题建议
2. 每章的标题和概要（{plan.chapter_count}章）
3. 每章建议字数分配
4. 关键情节点或论述点
5. 主要人物设定（如果是小说/故事）
6. 世界观或背景设定

请以JSON格式输出，包含以下结构：
{{
    "subtitle": "副标题",
    "chapters": [
        {{
            "title": "章节标题",
            "summary": "章节概要",
            "word_count": 字数,
            "key_points": ["要点1", "要点2"],
            "characters": ["出场人物"],
            "scenes": ["场景描述"]
        }}
    ],
    "characters": [
        {{
            "name": "人物名",
            "role": "角色定位",
            "traits": "性格特点",
            "arc": "人物弧线"
        }}
    ],
    "world_building": {{
        "setting": "背景设定",
        "rules": "世界规则",
        "atmosphere": "氛围基调"
    }}
}}"""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=2500)

            # 解析JSON
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = self._parse_outline_text(response)
            except json.JSONDecodeError:
                data = self._parse_outline_text(response)

            # 更新计划
            plan.subtitle = data.get("subtitle", "")

            # 创建章节
            chapters_data = data.get("chapters", [])
            plan.chapters = []

            for i, ch_data in enumerate(chapters_data[:plan.chapter_count]):
                chapter = Chapter(
                    id=f"ch_{i}_{datetime.now().timestamp()}",
                    title=ch_data.get("title", f"第{i+1}章"),
                    summary=ch_data.get("summary", ""),
                    word_count=ch_data.get("word_count", plan.total_word_count // plan.chapter_count),
                    key_points=ch_data.get("key_points", []),
                    characters=ch_data.get("characters", []),
                    scenes=ch_data.get("scenes", []),
                    order=i
                )
                plan.chapters.append(chapter)

            plan.characters = data.get("characters", [])
            plan.world_building = data.get("world_building", {})

        except Exception as e:
            # 生成默认大纲
            self._generate_default_outline(plan)

    def _parse_outline_text(self, text: str) -> Dict:
        """从文本解析大纲"""
        # 简化解析逻辑
        lines = text.split("\n")
        chapters = []
        current_chapter = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("第") and "章" in line:
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = {
                    "title": line,
                    "summary": "",
                    "word_count": 3000,
                    "key_points": []
                }
            elif current_chapter:
                if "概要" in line or "内容" in line:
                    current_chapter["summary"] = line
                elif line.startswith("-") or line.startswith("•"):
                    current_chapter["key_points"].append(line.strip("- •"))

        if current_chapter:
            chapters.append(current_chapter)

        return {
            "subtitle": "",
            "chapters": chapters,
            "characters": [],
            "world_building": {}
        }

    def _generate_default_outline(self, plan: LongArticlePlan):
        """生成默认大纲"""
        plan.subtitle = f"一部{plan.style}的{plan.genre}"

        words_per_chapter = plan.total_word_count // plan.chapter_count

        plan.chapters = []
        for i in range(plan.chapter_count):
            chapter = Chapter(
                id=f"ch_{i}_{datetime.now().timestamp()}",
                title=f"第{i+1}章：待命名",
                summary=f"本章推进故事/论述发展，约{words_per_chapter}字",
                word_count=words_per_chapter,
                key_points=["关键情节点/论述点1", "关键情节点/论述点2"],
                order=i
            )
            plan.chapters.append(chapter)

    async def generate_chapter_stream(
        self,
        plan_id: str,
        chapter_id: str,
        context_chapters: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成章节内容
        """
        plan = self._plans.get(plan_id)
        if not plan:
            yield {"error": "写作计划不存在"}
            return

        chapter = next((c for c in plan.chapters if c.id == chapter_id), None)
        if not chapter:
            yield {"error": "章节不存在"}
            return

        # 更新状态
        chapter.status = "writing"

        # 构建上下文
        context = self._build_chapter_context(plan, chapter, context_chapters)

        prompt = f"""请创作以下章节内容：

{context}

创作要求：
1. 字数约{chapter.word_count}字
2. 严格遵循章节概要
3. 体现{plan.style}的写作风格
4. 确保与前后文逻辑连贯
5. 关键情节点/论述点必须覆盖：{', '.join(chapter.key_points)}
6. 出场人物/元素：{', '.join(chapter.characters) if chapter.characters else '按情节需要'}
7. 重要场景：{', '.join(chapter.scenes) if chapter.scenes else '按情节需要'}

写作风格指引：
- 开头要有吸引力，快速进入主题
- 段落过渡自然流畅
- 保持叙事/论述节奏
- 适当使用描写增强画面感
- 结尾要有适当的收束或悬念

请开始创作第{chapter.order + 1}章《{chapter.title}》："""

        full_content = ""
        try:
            async for chunk in self.llm_service.generate_stream(prompt, max_tokens=chapter.word_count * 2):
                if "content" in chunk:
                    full_content += chunk["content"]
                    yield {
                        "type": "content",
                        "chapter_id": chapter_id,
                        "content": chunk["content"],
                        "progress": len(full_content) / chapter.word_count
                    }
                elif "error" in chunk:
                    yield chunk

            # 更新章节内容
            chapter.content = full_content
            chapter.status = "completed"

            yield {
                "type": "complete",
                "chapter_id": chapter_id,
                "word_count": len(full_content),
                "status": "completed"
            }

        except Exception as e:
            chapter.status = "pending"
            yield {"error": str(e)}

    def _build_chapter_context(
        self,
        plan: LongArticlePlan,
        current_chapter: Chapter,
        context_chapters: Optional[List[str]] = None
    ) -> str:
        """构建章节上下文"""
        context_parts = []

        # 基础信息
        context_parts.append(f"作品标题: {plan.title}")
        if plan.subtitle:
            context_parts.append(f"副标题: {plan.subtitle}")
        context_parts.append(f"类型: {plan.genre}")
        context_parts.append(f"风格: {plan.style}")
        if plan.theme:
            context_parts.append(f"主题: {plan.theme}")

        # 世界观
        if plan.world_building:
            wb = plan.world_building
            context_parts.append(f"\n背景设定: {wb.get('setting', '')}")
            if wb.get('rules'):
                context_parts.append(f"世界规则: {wb.get('rules')}")
            if wb.get('atmosphere'):
                context_parts.append(f"氛围基调: {wb.get('atmosphere')}")

        # 人物设定
        if plan.characters:
            context_parts.append("\n主要人物:")
            for char in plan.characters[:5]:  # 最多5个主要人物
                context_parts.append(f"- {char.get('name', '')}: {char.get('role', '')}, {char.get('traits', '')}")

        # 前情提要
        if current_chapter.order > 0:
            prev_chapters = plan.chapters[:current_chapter.order]
            context_parts.append("\n前情概要:")
            for prev in prev_chapters[-2:]:  # 最近2章
                context_parts.append(f"《{prev.title}》: {prev.summary[:100]}...")

        # 当前章节信息
        context_parts.append(f"\n当前章节: 第{current_chapter.order + 1}章《{current_chapter.title}》")
        context_parts.append(f"章节概要: {current_chapter.summary}")

        return "\n".join(context_parts)

    async def regenerate_chapter(
        self,
        plan_id: str,
        chapter_id: str,
        feedback: str = "",
        style_adjustment: str = ""
    ) -> Dict[str, Any]:
        """
        重新生成章节
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "写作计划不存在"}

        chapter = next((c for c in plan.chapters if c.id == chapter_id), None)
        if not chapter:
            return {"error": "章节不存在"}

        # 清空内容
        chapter.content = ""
        chapter.status = "pending"

        # 构建优化提示
        adjustment = f"\n优化要求: {feedback}" if feedback else ""
        if style_adjustment:
            adjustment += f"\n风格调整: {style_adjustment}"

        # 重新生成（这里返回生成器，实际调用时用 generate_chapter_stream）
        return {
            "success": True,
            "message": "章节已重置，请调用生成接口重新创作",
            "chapter_id": chapter_id,
            "adjustment": adjustment
        }

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取写作计划"""
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        return self._plan_to_dict(plan)

    def _plan_to_dict(self, plan: LongArticlePlan) -> Dict[str, Any]:
        """将计划转换为字典"""
        return {
            "id": plan.id,
            "title": plan.title,
            "subtitle": plan.subtitle,
            "total_word_count": plan.total_word_count,
            "chapter_count": plan.chapter_count,
            "style": plan.style,
            "genre": plan.genre,
            "theme": plan.theme,
            "target_audience": plan.target_audience,
            "chapters": [
                {
                    "id": c.id,
                    "title": c.title,
                    "summary": c.summary,
                    "word_count": c.word_count,
                    "key_points": c.key_points,
                    "characters": c.characters,
                    "scenes": c.scenes,
                    "status": c.status,
                    "order": c.order,
                    "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content
                }
                for c in plan.chapters
            ],
            "characters": plan.characters,
            "world_building": plan.world_building,
            "created_at": plan.created_at,
            "progress": {
                "total": len(plan.chapters),
                "completed": sum(1 for c in plan.chapters if c.status == "completed"),
                "writing": sum(1 for c in plan.chapters if c.status == "writing"),
                "pending": sum(1 for c in plan.chapters if c.status == "pending")
            }
        }

    def update_chapter(
        self,
        plan_id: str,
        chapter_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新章节信息"""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "写作计划不存在"}

        chapter = next((c for c in plan.chapters if c.id == chapter_id), None)
        if not chapter:
            return {"error": "章节不存在"}

        # 更新字段
        if "title" in updates:
            chapter.title = updates["title"]
        if "summary" in updates:
            chapter.summary = updates["summary"]
        if "word_count" in updates:
            chapter.word_count = updates["word_count"]
        if "key_points" in updates:
            chapter.key_points = updates["key_points"]
        if "characters" in updates:
            chapter.characters = updates["characters"]
        if "scenes" in updates:
            chapter.scenes = updates["scenes"]

        return {"success": True, "chapter": chapter}

    def export_article(self, plan_id: str, format: str = "txt") -> Dict[str, Any]:
        """
        导出完整文章
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "写作计划不存在"}

        # 组装完整内容
        full_text = f"# {plan.title}\n"
        if plan.subtitle:
            full_text += f"## {plan.subtitle}\n"
        full_text += f"\n"

        total_words = 0
        for chapter in plan.chapters:
            if chapter.content:
                full_text += f"\n## {chapter.title}\n\n"
                full_text += chapter.content
                full_text += "\n"
                total_words += len(chapter.content)

        return {
            "title": plan.title,
            "format": format,
            "content": full_text,
            "total_words": total_words,
            "chapter_count": len([c for c in plan.chapters if c.content]),
            "generated_at": datetime.now().isoformat()
        }
