"""
长文本写作 API 路由 - 增强版
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services.enhanced_long_article_service import EnhancedLongArticleService
from app.services.llm_service import LLMService
from app.api.dependencies import get_llm_service
import json

router = APIRouter(prefix="/long-article", tags=["长文本写作"])


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
