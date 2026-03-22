"""
兼容前端旧接口的热点写作 API

前端当前在调用：
- /api/hot-topics/list
- /api/hot-topics/generate-outline
- /api/hot-topics/generate-article/stream (fetch + 读取 data: 行)
- /api/hot-topics/create-document
- /api/hot-topics/quick-write
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.models import Document, Project
from app.services.enhanced_hot_topics_service import EnhancedHotTopicsService
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService
from app.api.dependencies import get_llm_service, get_cache_service


router = APIRouter(prefix="/api/hot-topics", tags=["热点写作(compat)"])


def _guess_topic_fields(topic_title: str) -> Dict[str, str]:
    title = (topic_title or "").strip()
    keyword = title[:12] if title else "热点话题"
    return {"category": "社会", "keyword": keyword, "aspect": "社会关注"}


def _text_to_blocks(text: str):
    t = (text or "").strip()
    if not t:
        return []
    blocks = []
    for para in re.split(r'\n{2,}', t):
        para = para.strip()
        if not para:
            continue
        block_type = "heading" if para.startswith("#") else "paragraph"
        blocks.append({
            "id": uuid.uuid4().hex[:8],
            "type": block_type,
            "content": para,
            "props": {},
        })
    return blocks or [{"id": uuid.uuid4().hex[:8], "type": "paragraph", "content": t, "props": {}}]


def _normalize_outline(raw: Any, topic_title: str = "") -> Dict[str, Any]:
    """
    把 LLM 返回的各种格式（中文 key / 英文 key / 纯文本）
    统一转成前端固定结构：
      title_options, angle, target_audience, structure, keywords,
      introduction, conclusion, style
    """
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
            "_raw": str(raw),
        }

    o = dict(raw)

    # ---- title_options ----
    title_options = (
        o.get("title_options")
        or o.get("titles")
        or o.get("文章标题")
        or o.get("标题")
        or o.get("备选标题")
        or o.get("标题选项")
        or []
    )
    if isinstance(title_options, str):
        title_options = [title_options]
    if not isinstance(title_options, list) or len(title_options) == 0:
        title_options = [topic_title] if topic_title else []
    o["title_options"] = title_options

    # ---- angle ----
    o["angle"] = (
        o.get("angle")
        or o.get("topic_aspect")
        or o.get("切入角度")
        or o.get("角度")
        or o.get("写作角度")
        or "围绕热点事件的来龙去脉与影响展开分析"
    )

    # ---- target_audience ----
    o["target_audience"] = (
        o.get("target_audience")
        or o.get("目标受众")
        or o.get("受众")
        or o.get("读者群体")
        or "对该热点话题感兴趣的普通读者"
    )

    # ---- introduction ----
    o["introduction"] = (
        o.get("introduction")
        or o.get("导语")
        or o.get("文章导语")
        or o.get("引言")
        or ""
    )

    # ---- conclusion ----
    o["conclusion"] = (
        o.get("conclusion")
        or o.get("结尾")
        or o.get("结尾建议")
        or o.get("结语")
        or ""
    )

    # ---- style ----
    o["style"] = (
        o.get("style")
        or o.get("写作风格")
        or o.get("写作风格建议")
        or ""
    )

    # ---- keywords ----
    kw = o.get("keywords") or o.get("关键词") or []
    if isinstance(kw, str):
        kw = [k.strip() for k in kw.replace("，", ",").split(",") if k.strip()]
    o["keywords"] = kw if isinstance(kw, list) else []

    # ---- structure (sections) ----
    sections_raw = (
        o.get("structure")
        or o.get("sections")
        or o.get("主要章节")
        or o.get("章节")
        or o.get("文章结构")
        or []
    )
    if isinstance(sections_raw, str):
        sections_raw = []

    structure = []
    if isinstance(sections_raw, list):
        for s in sections_raw:
            if isinstance(s, str):
                structure.append({
                    "section": s,
                    "word_count": "",
                    "key_points": [],
                    "writing_tips": "",
                })
            elif isinstance(s, dict):
                name = (
                    s.get("section")
                    or s.get("title")
                    or s.get("章节标题")
                    or s.get("标题")
                    or s.get("name")
                    or "章节"
                )
                points = s.get("key_points") or s.get("points") or s.get("关键点") or s.get("要点") or []
                if isinstance(points, str):
                    points = [points]
                structure.append({
                    "section": name,
                    "word_count": s.get("word_count") or s.get("字数") or "",
                    "key_points": points if isinstance(points, list) else [],
                    "writing_tips": s.get("writing_tips") or s.get("写作建议") or "",
                })
    o["structure"] = structure

    # 把原始数据也附上，供前端 fallback 展示
    o["_raw"] = json.dumps(raw, ensure_ascii=False, indent=2)

    return o


def get_hot_topics_service(
    llm_service: LLMService = Depends(get_llm_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> EnhancedHotTopicsService:
    return EnhancedHotTopicsService(llm_service, cache_service)


@router.get("/list")
async def list_hot_topics(
    limit: int = 20,
    category: Optional[str] = None,
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service),
):
    try:
        topics = await service.get_hot_topics(category=category, limit=limit)
        return {"topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-outline")
async def generate_outline_compat(
    payload: Dict[str, Any],
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service),
):
    topic_title = payload.get("topic_title") or ""
    article_type = payload.get("article_type") or "评论"
    word_count = int(payload.get("word_count") or 1500)

    guess = _guess_topic_fields(topic_title)
    result = await service.generate_article_outline(
        topic_title=topic_title,
        topic_keyword=guess["keyword"],
        topic_aspect=guess["aspect"],
        category=guess["category"],
        article_type=article_type,
        word_count=word_count,
    )

    outline = _normalize_outline(result.get("outline") or {}, topic_title)
    return {"outline": outline}


@router.post("/generate-outline/stream")
async def generate_outline_stream_compat(
    payload: Dict[str, Any],
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service),
):
    """
    流式输出热点写作大纲（兼容前端）。

    SSE 协议：
    - data: <chunk>\n\n （大纲生成过程的原始文本）
    - data: [OUTLINE_META]{...}\n\n （结构化大纲，供前端渲染）
    - data: [DONE]\n\n
    """
    topic_title = payload.get("topic_title") or ""
    article_type = payload.get("article_type") or "评论"
    word_count = int(payload.get("word_count") or 1500)

    guess = _guess_topic_fields(topic_title)

    prompt = f"""请为以下热点话题生成一篇文章大纲：

话题标题: {topic_title}
核心关键词: {guess["keyword"]}
分析角度: {guess["aspect"]}
所属分类: {guess["category"]}
文章类型: {article_type}
目标字数: {word_count}字

请生成包含以下要素的大纲：
1. 文章标题（3个备选）
2. 文章导语
3. 主要章节（3-5个）
4. 每个章节的关键点
5. 结尾建议
6. 写作风格建议

请以JSON格式输出。"""

    async def gen():
        chunks: list[str] = []
        try:
            async for chunk in service.llm_service.generate_stream(prompt, max_tokens=1500):
                text = str(chunk)
                if text:
                    chunks.append(text)
                    safe = text.replace("\n", "")
                    yield f"data: {safe}\n\n"

        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

        # 生成结束：解析并返回结构化元数据
        try:
            raw_text = "".join(chunks)

            outline_obj: Dict[str, Any]
            try:
                json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if json_match:
                    outline_obj = json.loads(json_match.group())
                else:
                    outline_obj = service._parse_outline_text(raw_text)
            except json.JSONDecodeError:
                outline_obj = service._parse_outline_text(raw_text)
            except Exception:
                outline_obj = service._get_default_outline(topic_title, guess["keyword"], article_type)

            normalized = _normalize_outline(outline_obj or {}, topic_title)
            meta = json.dumps({"outline": normalized}, ensure_ascii=False)
            yield f"data: [OUTLINE_META]{meta}\n\n"

        except Exception as e:
            # 避免解析失败让前端永远卡住
            default_outline = service._get_default_outline(topic_title, guess["keyword"], article_type)
            normalized = _normalize_outline(default_outline or {}, topic_title)
            meta = json.dumps({"outline": normalized}, ensure_ascii=False)
            yield f"data: [OUTLINE_META]{meta}\n\n"
            yield f"data: [ERROR] {str(e)}\n\n"

        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/generate-article/stream")
async def generate_article_stream_compat(
    payload: Dict[str, Any],
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service),
):
    outline = payload.get("outline") or {}
    selected_title = (payload.get("selected_title") or "").strip()

    # 兼容：把 outline 内的信息尽量取出来
    topic_title = selected_title or outline.get("topic_title") or outline.get("title") or "热点解读"
    guess = _guess_topic_fields(topic_title)

    # 服务需要一个 outline dict：把前端 outline 原样塞进去即可
    async def gen():
        try:
            async for chunk in service.generate_article_stream(
                topic_title=topic_title,
                topic_keyword=guess["keyword"],
                topic_aspect=guess["aspect"],
                category=guess["category"],
                outline=outline,
                article_type="评论",
                word_count=1500,
                style="专业",
            ):
                text = str(chunk)
                if text:
                    yield f"data: {text}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/create-document")
async def create_document_from_hot_topics(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    project_id = int(payload.get("project_id") or 0)
    title = (payload.get("title") or "").strip()
    content = payload.get("content") or ""

    if not project_id or not title:
        raise HTTPException(status_code=400, detail="project_id 与 title 不能为空")

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user["id"])
        .first()
    )
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    doc = Document(
        title=title,
        content=_text_to_blocks(content),
        project_id=project_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document": {"id": doc.id, "title": doc.title, "project_id": doc.project_id}}


@router.post("/quick-write")
async def quick_write_and_save(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service),
    llm: LLMService = Depends(get_llm_service),
):
    topic_title = payload.get("topic_title") or ""
    article_type = payload.get("article_type") or "评论"
    word_count = int(payload.get("word_count") or 1500)
    project_id = int(payload.get("project_id") or 0)

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id 不能为空")

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user["id"])
        .first()
    )
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    guess = _guess_topic_fields(topic_title)
    outline_result = await service.generate_article_outline(
        topic_title=topic_title,
        topic_keyword=guess["keyword"],
        topic_aspect=guess["aspect"],
        category=guess["category"],
        article_type=article_type,
        word_count=word_count,
    )
    outline = _normalize_outline(outline_result.get("outline") or {}, topic_title)
    title_options = outline.get("title_options") or []
    selected_title = title_options[0] if title_options else topic_title or "热点解读"

    # 非流式快速生成全文（避免前端再跑一遍 stream）
    prompt = f"""请根据以下大纲写一篇文章。\n标题：{selected_title}\n大纲：\n{json.dumps(outline, ensure_ascii=False, indent=2)}\n\n请直接输出正文，不要包含多余说明。"""
    article = await llm.generate(
        prompt, max_tokens=max(8000, word_count * 3), timeout=300.0
    )
    article_text = article.strip()

    doc = Document(
        title=selected_title,
        content=_text_to_blocks(article_text),
        project_id=project_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "outline": outline,
        "article": article_text,
        "document": {"id": doc.id, "title": doc.title, "project_id": doc.project_id},
    }

