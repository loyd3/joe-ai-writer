"""
写作能力适配层：供项目智能体调用的「只生成、不落库」接口。

复用现有 Copywriting / HotTopics / Brainstorm / AIStory 服务逻辑，
返回统一结构，由 agent 工具暂存草稿后再 propose_* 写入项目。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from app.services.ai_story_generator_service import AIStoryGeneratorService
from app.services.brainstorm_writing_service import BrainstormWritingService
from app.services.copywriting_service import CopywritingService
from app.services.enhanced_hot_topics_service import EnhancedHotTopicsService
from app.services.hot_topics_writing_service import HotTopicsWritingService
from app.services.llm_service import llm_service as default_llm
from app.services.cache_service import CacheService


def _guess_topic_fields(topic_title: str) -> Dict[str, str]:
    title = (topic_title or "").strip()
    keyword = title[:12] if title else "热点话题"
    return {"category": "社会", "keyword": keyword, "aspect": "社会关注"}


def _normalize_hot_outline(raw: Any, topic_title: str = "") -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "title_options": [topic_title] if topic_title else [],
            "angle": "围绕热点事件展开分析",
            "target_audience": "对该话题感兴趣的读者",
            "structure": [],
            "keywords": [],
            "introduction": str(raw) if raw else "",
            "conclusion": "",
            "style": "",
            "topic": topic_title,
            "target_word_count": 1500,
            "tone": "专业",
        }
    o = dict(raw)
    title_options = (
        o.get("title_options") or o.get("titles") or o.get("文章标题") or o.get("标题") or []
    )
    if isinstance(title_options, str):
        title_options = [title_options]
    if not isinstance(title_options, list) or not title_options:
        title_options = [topic_title] if topic_title else []
    o["title_options"] = title_options
    o["angle"] = o.get("angle") or o.get("切入角度") or "围绕热点展开"
    o["target_audience"] = o.get("target_audience") or o.get("目标受众") or "普通读者"
    o["introduction"] = o.get("introduction") or o.get("导语") or ""
    o["conclusion"] = o.get("conclusion") or o.get("结尾") or ""
    o["style"] = o.get("style") or o.get("风格") or ""
    o["keywords"] = o.get("keywords") or o.get("关键词") or []
    structure = o.get("structure") or o.get("sections") or o.get("章节") or []
    if not isinstance(structure, list):
        structure = []
    # 兼容 BrainstormWritingService / Enhanced 两种章节形态
    norm_structure = []
    for section in structure:
        if not isinstance(section, dict):
            continue
        if "section" in section or "key_points" in section:
            norm_structure.append(section)
            continue
        norm_structure.append(
            {
                "section": section.get("name") or section.get("title") or "章节",
                "key_points": section.get("points") or section.get("key_points") or [],
                "word_count": section.get("word_count") or 300,
            }
        )
    o["structure"] = norm_structure
    o["topic"] = topic_title or o.get("topic") or ""
    raw_wc = o.get("target_word_count") or o.get("word_count") or 1500
    try:
        o["target_word_count"] = max(100, min(int(raw_wc), 8000))
    except (TypeError, ValueError):
        o["target_word_count"] = 1500
    o["tone"] = o.get("tone") or o.get("style") or "专业"
    return o


def _hot_service() -> EnhancedHotTopicsService:
    return EnhancedHotTopicsService(default_llm, CacheService())


async def list_hot_topics(
    *,
    limit: int = 20,
    category: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    result = await _hot_service().get_hot_topics(
        category=category, limit=min(max(limit, 1), 50), force_refresh=refresh
    )
    topics = result.get("topics") or []
    slim = []
    for t in topics[:limit]:
        if not isinstance(t, dict):
            continue
        slim.append(
            {
                "title": t.get("title") or t.get("name") or "",
                "heat": t.get("heat") or t.get("hot") or 0,
                "source": t.get("source") or "",
                "category": t.get("category") or "",
            }
        )
    return {
        "kind": "hot_topics_list",
        "topics": slim,
        "is_fallback": bool(result.get("is_fallback")),
        "message": result.get("message") or "",
        "meta": {"data_source": result.get("data_source") or "fallback"},
    }


async def hot_topic_generate(
    *,
    topic_title: str,
    article_type: str = "评论",
    word_count: int = 1500,
    style: str = "专业",
    additional_requirements: str = "",
) -> Dict[str, Any]:
    topic_title = (topic_title or "").strip()
    if not topic_title:
        raise ValueError("topic_title 不能为空")
    guess = _guess_topic_fields(topic_title)
    service = _hot_service()
    outline_raw = await service.generate_article_outline(
        topic_title=topic_title,
        topic_keyword=guess["keyword"],
        topic_aspect=guess["aspect"],
        category=guess["category"],
        article_type=article_type,
        word_count=word_count,
    )
    outline = _normalize_hot_outline(outline_raw.get("outline") or outline_raw, topic_title)
    outline["target_word_count"] = word_count
    outline["tone"] = style
    outline["topic"] = topic_title
    content = await HotTopicsWritingService.generate_article(
        outline,
        selected_title=(outline.get("title_options") or [topic_title])[0],
        additional_requirements=additional_requirements or None,
    )
    if not isinstance(content, str) or not content.strip() or content.startswith("[错误]") or content.startswith("[配置错误]"):
        raise ValueError(content or "热点文章生成失败")
    title = (outline.get("title_options") or [topic_title])[0]
    return {
        "kind": "hot_topic_article",
        "title": title,
        "content": content.strip(),
        "outline": outline,
        "meta": {"topic_title": topic_title, "article_type": article_type, "word_count": word_count},
    }


async def copywriting_generate(
    *,
    product: str = "",
    target_audience: str = "",
    copy_objective: str = "广告",
    selling_points: str = "",
    pain_points: str = "",
    evidence_cases: str = "",
    cta: str = "",
    tone: str = "专业且有说服力",
    word_count: int = 900,
    additional_requirements: str = "",
) -> Dict[str, Any]:
    result = await CopywritingService.generate_copywriting(
        default_llm,
        product=product,
        target_audience=target_audience,
        copy_objective=copy_objective,
        selling_points=selling_points,
        pain_points=pain_points,
        evidence_cases=evidence_cases,
        cta=cta,
        tone=tone,
        word_count=int(word_count or 900),
        additional_requirements=additional_requirements,
    )
    title = str(result.get("title") or product or "营销文案").strip()
    content = str(result.get("content") or "").strip()
    if not content:
        raise ValueError("文案生成结果为空")
    return {
        "kind": "copywriting",
        "title": title,
        "content": content,
        "meta": {
            "keywords": result.get("keywords") or [],
            "product": product,
            "copy_objective": copy_objective,
        },
    }


def list_brainstorm_ideas(*, category: Optional[str] = None, limit: int = 12) -> Dict[str, Any]:
    categories = BrainstormWritingService.get_categories()
    if category:
        ideas = [BrainstormWritingService.generate_random_brainstorm(category) for _ in range(min(limit, 12))]
    else:
        trending = BrainstormWritingService.get_trending_brainstorms(limit=limit)
        ideas = trending or [
            BrainstormWritingService.generate_random_brainstorm() for _ in range(min(limit, 8))
        ]
    slim = []
    for idea in ideas[:limit]:
        if not isinstance(idea, dict):
            continue
        slim.append(
            {
                "title": idea.get("title") or "",
                "category": idea.get("category") or "",
                "concept": idea.get("concept") or idea.get("description") or "",
                "heat": idea.get("heat") or 0,
            }
        )
    return {
        "kind": "brainstorm_ideas",
        "categories": categories,
        "ideas": slim,
        "meta": {},
    }


async def brainstorm_write(
    *,
    title: str = "",
    category: str = "脑洞",
    concept: str = "",
    style: str = "幽默风趣",
    word_count: str = "medium",
) -> Dict[str, Any]:
    brainstorm = {
        "title": (title or "").strip() or f"关于{concept or category}的脑洞",
        "category": category or "脑洞",
        "concept": concept or "",
    }
    outline = await BrainstormWritingService.generate_outline(
        brainstorm, style=style, word_count=word_count
    )
    article = await BrainstormWritingService.generate_article(
        brainstorm, outline=outline, style=style, word_count=word_count
    )
    if isinstance(article, dict):
        content = str(article.get("content") or article.get("article") or "").strip()
        art_title = str(article.get("title") or outline.get("title") or brainstorm["title"]).strip()
    else:
        content = str(article or "").strip()
        art_title = str(outline.get("title") or brainstorm["title"]).strip()
    if not content:
        raise ValueError("脑洞文章生成结果为空")
    return {
        "kind": "brainstorm_article",
        "title": art_title,
        "content": content,
        "outline": outline if isinstance(outline, dict) else {},
        "meta": {"category": category, "style": style, "word_count": word_count},
    }


async def story_generate(
    *,
    theme: str,
    genre: Optional[str] = None,
    word_count: int = 5000,
    chapter_count: Optional[int] = None,
    additional_requirements: Optional[str] = None,
) -> Dict[str, Any]:
    theme = (theme or "").strip()
    if not theme:
        raise ValueError("theme 不能为空")
    story_data = await AIStoryGeneratorService.generate_full_story(
        theme=theme,
        genre=genre,
        word_count=int(word_count or 5000),
        chapter_count=chapter_count,
        additional_requirements=additional_requirements,
    )
    if not isinstance(story_data, dict) or story_data.get("error"):
        raise ValueError(
            (story_data or {}).get("error")
            if isinstance(story_data, dict)
            else "故事设定生成失败"
        )
    titles = story_data.get("title_options") or []
    title = titles[0] if isinstance(titles, list) and titles else theme
    return {
        "kind": "story_settings",
        "title": title if isinstance(title, str) else theme,
        "story_data": story_data,
        "meta": {
            "theme": theme,
            "genre": genre,
            "word_count": word_count,
            "chapter_count": chapter_count,
        },
    }


def story_to_memory_fields(story_data: Dict[str, Any]) -> Dict[str, Any]:
    """story_data → 可写入 AIMemory 的字段子集。"""
    return AIStoryGeneratorService.convert_to_project_memory(story_data)


def new_draft_id() -> str:
    return f"draft_{uuid.uuid4().hex[:12]}"


def preview_text(text: str, limit: int = 400) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[:limit] + "…"
