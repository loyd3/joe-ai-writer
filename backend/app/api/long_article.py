"""
长文本写作 API 路由 - 增强版
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from app.services.enhanced_long_article_service import EnhancedLongArticleService
from app.services.llm_service import LLMService
from app.api.dependencies import get_llm_service
import json

router = APIRouter(prefix="/api/long-article", tags=["长文本写作"])


class CreatePlanRequest(BaseModel):
    title: str = Field(..., description="文章标题", min_length=1, max_length=200)
    article_type: str = Field(default="novel", description="文章类型")
    total_word_count: Optional[int] = Field(default=None, description="总字数")
    style: str = Field(default="专业严谨", description="写作风格")
    theme: str = Field(default="", description="主题")
    target_audience: str = Field(default="", description="目标读者")
    requirements: str = Field(default="", description="特殊要求")


class UpdateChapterRequest(BaseModel):
    title: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    word_count: Optional[int] = Field(default=None)
    key_points: Optional[List[str]] = Field(default=None)
    characters: Optional[List[str]] = Field(default=None)
    scenes: Optional[List[str]] = Field(default=None)


class RegenerateChapterRequest(BaseModel):
    feedback: str = Field(default="", description="修改反馈")
    style_adjustment: str = Field(default="", description="风格调整")


def get_long_article_service(
    llm_service: LLMService = Depends(get_llm_service)
) -> EnhancedLongArticleService:
    return EnhancedLongArticleService(llm_service)


@router.get("/types")
async def get_article_types(
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """获取文章类型列表"""
    return {
        "types": service.get_article_types()
    }


@router.get("/styles")
async def get_writing_styles(
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """获取写作风格列表"""
    return {
        "styles": service.get_writing_styles()
    }


@router.post("/plan")
async def create_plan(
    request: CreatePlanRequest,
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """
    创建长文本写作计划
    """
    try:
        plan = await service.create_plan(
            title=request.title,
            article_type=request.article_type,
            total_word_count=request.total_word_count,
            style=request.style,
            theme=request.theme,
            target_audience=request.target_audience,
            requirements=request.requirements
        )
        return {
            "success": True,
            "plan": service._plan_to_dict(plan)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/{plan_id}")
async def get_plan(
    plan_id: str,
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """
    获取写作计划详情
    """
    plan = service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="写作计划不存在")
    return {
        "success": True,
        "plan": plan
    }


@router.post("/plan/{plan_id}/chapter/{chapter_id}/generate")
async def generate_chapter(
    plan_id: str,
    chapter_id: str,
    context_chapters: Optional[List[str]] = Query(None),
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """
    流式生成章节内容
    """
    async def event_generator():
        try:
            async for chunk in service.generate_chapter_stream(
                plan_id=plan_id,
                chapter_id=chapter_id,
                context_chapters=context_chapters
            ):
                yield {
                    "event": "message",
                    "data": json.dumps(chunk, ensure_ascii=False)
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


@router.put("/plan/{plan_id}/chapter/{chapter_id}")
async def update_chapter(
    plan_id: str,
    chapter_id: str,
    request: UpdateChapterRequest,
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """
    更新章节信息
    """
    updates = request.dict(exclude_unset=True)
    result = service.update_chapter(plan_id, chapter_id, updates)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/plan/{plan_id}/chapter/{chapter_id}/regenerate")
async def regenerate_chapter(
    plan_id: str,
    chapter_id: str,
    request: RegenerateChapterRequest,
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """
    重新生成章节
    """
    result = await service.regenerate_chapter(
        plan_id=plan_id,
        chapter_id=chapter_id,
        feedback=request.feedback,
        style_adjustment=request.style_adjustment
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/plan/{plan_id}/export")
async def export_article(
    plan_id: str,
    format: str = Query("txt", description="导出格式"),
    service: EnhancedLongArticleService = Depends(get_long_article_service)
):
    """
    导出完整文章
    """
    result = service.export_article(plan_id, format)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ====================================================================
# 前端兼容接口：前端调用 /create, /generate-outline, /chapters 等
# ====================================================================

# 用 plan_id 当 article_id，存在内存里便于映射
_article_plan_map: Dict[int, str] = {}
_next_article_id = {"val": 1}


def _alloc_article_id(plan_id: str) -> int:
    aid = _next_article_id["val"]
    _next_article_id["val"] += 1
    _article_plan_map[aid] = plan_id
    return aid


def _get_plan_id(article_id: int) -> str:
    pid = _article_plan_map.get(article_id)
    if not pid:
        raise HTTPException(status_code=404, detail="文章不存在或已过期")
    return pid


@router.post("/create")
async def compat_create(
    payload: Dict[str, Any],
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：创建长文任务"""
    topic = payload.get("topic") or payload.get("title") or "未命名"
    target_words = int(payload.get("target_words") or payload.get("word_count") or 50000)
    style = payload.get("style") or "文学叙事"
    requirements = payload.get("requirements") or ""

    try:
        plan = await service.create_plan(
            title=topic,
            article_type="novel",
            total_word_count=target_words,
            style=style,
            theme=topic,
            requirements=requirements,
        )
        aid = _alloc_article_id(plan.id)
        return {
            "success": True,
            "article_id": aid,
            "plan_id": plan.id,
            "message": f"长文任务已创建，共 {plan.chapter_count} 章",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.post("/generate-outline")
async def compat_generate_outline(
    payload: Dict[str, Any],
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：获取/生成大纲"""
    article_id = int(payload.get("article_id") or 0)
    plan_id = _get_plan_id(article_id)
    plan_dict = service.get_plan(plan_id)
    if not plan_dict:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {
        "success": True,
        "outline": plan_dict.get("chapters", []),
        "plan": plan_dict,
    }


@router.get("/chapters/{article_id}")
async def compat_get_chapters(
    article_id: int,
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：获取章节列表"""
    plan_id = _get_plan_id(article_id)
    plan_dict = service.get_plan(plan_id)
    if not plan_dict:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {
        "success": True,
        "chapters": plan_dict.get("chapters", []),
    }


@router.get("/progress/{article_id}")
async def compat_get_progress(
    article_id: int,
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：获取进度"""
    plan_id = _get_plan_id(article_id)
    plan_dict = service.get_plan(plan_id)
    if not plan_dict:
        raise HTTPException(status_code=404, detail="计划不存在")
    chapters = plan_dict.get("chapters", [])
    completed = sum(1 for c in chapters if c.get("content"))
    return {
        "success": True,
        "total": len(chapters),
        "completed": completed,
        "percent": round(completed / max(len(chapters), 1) * 100, 1),
    }


@router.get("/generate/{article_id}")
async def compat_generate_stream(
    article_id: int,
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：流式生成所有章节（SSE）"""
    plan_id = _get_plan_id(article_id)
    plan_dict = service.get_plan(plan_id)
    if not plan_dict:
        raise HTTPException(status_code=404, detail="计划不存在")

    chapters = plan_dict.get("chapters", [])

    async def gen():
        for idx, ch in enumerate(chapters):
            ch_id = ch.get("id", str(idx))
            yield f"data: {json.dumps({'type': 'chapter_start', 'index': idx, 'title': ch.get('title', '')}, ensure_ascii=False)}\n\n"
            try:
                async for chunk in service.generate_chapter_stream(
                    plan_id=plan_id, chapter_id=ch_id
                ):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'chapter_done', 'index': idx}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/export/{article_id}")
async def compat_export(
    article_id: int,
    format: str = Query("txt"),
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：导出"""
    plan_id = _get_plan_id(article_id)
    result = service.export_article(plan_id, format)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/list")
async def compat_list(
    service: EnhancedLongArticleService = Depends(get_long_article_service),
):
    """前端兼容：列出所有任务"""
    items = []
    for aid, pid in _article_plan_map.items():
        plan = service.get_plan(pid)
        if plan:
            items.append({
                "article_id": aid,
                "plan_id": pid,
                "title": plan.get("title", ""),
                "total_word_count": plan.get("total_word_count", 0),
                "chapter_count": len(plan.get("chapters", [])),
            })
    return {"success": True, "articles": items}


@router.delete("/{article_id}")
async def compat_delete(article_id: int):
    """前端兼容：删除任务"""
    if article_id in _article_plan_map:
        del _article_plan_map[article_id]
    return {"success": True}
