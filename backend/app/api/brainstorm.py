"""
脑洞写作 API 路由 - 增强版
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services.enhanced_brainstorm_service import EnhancedBrainstormService
from app.services.llm_service import LLMService
from app.api.dependencies import get_llm_service
import json

router = APIRouter(prefix="/brainstorm", tags=["脑洞写作"])


class GenerateIdeaRequest(BaseModel):
    mode: str = Field(default="random", description="创意模式")
    keywords: Optional[List[str]] = Field(default=None, description="关键词列表")
    count: int = Field(default=3, ge=1, le=5, description="生成数量")


class ExpandIdeaRequest(BaseModel):
    idea: dict = Field(..., description="要扩展的创意")
    expansion_type: str = Field(default="outline", description="扩展类型")
    detail_level: str = Field(default="standard", description="详细程度")


class GenerateContentRequest(BaseModel):
    idea: dict = Field(..., description="创意内容")
    content_type: str = Field(default="opening", description="内容类型")
    word_count: int = Field(default=1000, ge=500, le=5000)
    style: str = Field(default="creative", description="写作风格")


class RemixIdeasRequest(BaseModel):
    ideas: List[dict] = Field(..., description="要混合的创意列表")


def get_brainstorm_service(
    llm_service: LLMService = Depends(get_llm_service)
) -> EnhancedBrainstormService:
    return EnhancedBrainstormService(llm_service)


@router.get("/modes")
async def get_creative_modes(
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """获取创意模式列表"""
    return {
        "modes": service.get_creative_modes()
    }


@router.get("/elements")
async def get_random_elements(
    count: int = Query(4, ge=1, le=8),
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """获取随机创意元素"""
    return {
        "elements": service.get_random_elements(count)
    }


@router.post("/generate")
async def generate_ideas(
    request: GenerateIdeaRequest,
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    生成创意脑洞
    """
    try:
        result = await service.generate_idea(
            mode=request.mode,
            keywords=request.keywords,
            count=request.count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expand")
async def expand_idea(
    request: ExpandIdeaRequest,
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    扩展创意为完整方案
    """
    try:
        result = await service.expand_idea(
            idea=request.idea,
            expansion_type=request.expansion_type,
            detail_level=request.detail_level
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-stream")
async def generate_content_stream(
    request: GenerateContentRequest,
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    流式生成内容
    """
    async def event_generator():
        try:
            async for chunk in service.generate_content_stream(
                idea=request.idea,
                content_type=request.content_type,
                word_count=request.word_count,
                style=request.style
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


@router.post("/remix")
async def remix_ideas(
    request: RemixIdeasRequest,
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    混合多个创意
    """
    try:
        result = service.remix_ideas(request.ideas)
        return {
            "success": True,
            "remixed_idea": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
