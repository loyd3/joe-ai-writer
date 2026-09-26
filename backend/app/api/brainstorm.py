"""
增强脑洞 API（`/brainstorm`）

==============================================================================
定位
------------------------------------------------------------------------------
基于 `EnhancedBrainstormService` 的「正式」脑洞能力：选模式、抽元素、
生成/扩展/混合创意，以及流式写开篇等内容。

与 `brainstorm_compat.py`（前缀 `/api/brainstorm`）并存：
  - 本文件：创意工作室式交互（模式 + 元素 + generate/expand/remix）
  - compat：逛脑洞卡片、收藏、短文/一键建项目（BrainstormWriting 页主路径）

装配：`main.py` → `include_router(brainstorm.router)`（无 `/api` 前缀）

==============================================================================
调用方
------------------------------------------------------------------------------
  frontend/src/components/BrainstormWriting.vue
    GET  /brainstorm/modes
    GET  /brainstorm/elements
    POST /brainstorm/generate
    POST /brainstorm/expand
    POST /brainstorm/remix
    POST /brainstorm/generate-stream   （EventSource / SSE）

依赖：EnhancedBrainstormService ← LLMService

==============================================================================
接口一览
------------------------------------------------------------------------------
GET  /modes              创意模式列表（CREATIVE_MODES）
GET  /elements?count=    随机创意元素（人物/场景/物品等）
POST /generate           按 mode + keywords 批量生成脑洞
POST /expand             把单条 idea 扩成大纲/设定等
POST /generate-stream    按 idea 流式生成正文片段（opening 等）
POST /remix              本地混合多条 idea（不调 LLM）

模式 id 示例：random | crossover | whatif | reverse | analogy |
              extreme | combination | constraint
==============================================================================
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
    """POST /generate：按模式与关键词出脑洞。"""
    mode: str = Field(default="random", description="创意模式 id，见 CREATIVE_MODES")
    keywords: Optional[List[str]] = Field(default=None, description="可选关键词列表")
    count: int = Field(default=3, ge=1, le=5, description="生成条数 1～5")


class ExpandIdeaRequest(BaseModel):
    """POST /expand：把一条创意扩成更完整方案。"""
    idea: dict = Field(..., description="要扩展的创意对象")
    expansion_type: str = Field(
        default="outline",
        description="扩展类型，如 outline / setting / characters 等（由服务层解释）",
    )
    detail_level: str = Field(
        default="standard",
        description="详细程度，如 brief | standard | detailed",
    )


class GenerateContentRequest(BaseModel):
    """POST /generate-stream：按创意流式写内容。"""
    idea: dict = Field(..., description="创意内容")
    content_type: str = Field(
        default="opening",
        description="内容类型，默认 opening（开篇）",
    )
    word_count: int = Field(default=1000, ge=500, le=5000)
    style: str = Field(default="creative", description="写作风格标签")


class RemixIdeasRequest(BaseModel):
    """POST /remix：混合多条创意。"""
    ideas: List[dict] = Field(..., description="要混合的创意列表（至少 2 条更有意义）")


def get_brainstorm_service(
    llm_service: LLMService = Depends(get_llm_service)
) -> EnhancedBrainstormService:
    """注入 EnhancedBrainstormService（包装当前 LLM）。"""
    return EnhancedBrainstormService(llm_service)


@router.get("/modes")
async def get_creative_modes(
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    获取创意模式列表。
    返回 { modes: [...] }，每项含 id/name/description/icon/color 等。
    """
    return {
        "modes": service.get_creative_modes()
    }


@router.get("/elements")
async def get_random_elements(
    count: int = Query(4, ge=1, le=8),
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    从 CREATIVE_ELEMENTS 随机抽若干元素，供前端「灵感骰子」展示。
    Query：count 1～8，默认 4。返回 { elements: [...] }。
    """
    return {
        "elements": service.get_random_elements(count)
    }


@router.post("/generate")
async def generate_ideas(
    request: GenerateIdeaRequest,
    service: EnhancedBrainstormService = Depends(get_brainstorm_service)
):
    """
    非流式：按 mode + keywords 调用 LLM 生成多条脑洞。
    Body：GenerateIdeaRequest。成功直接返回 service.generate_idea 结果；失败 500。
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
    把单条 idea 扩成大纲/设定等完整方案。
    Body：idea + expansion_type + detail_level。失败 500。
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
    流式生成正文片段（默认开篇）。
    Body：GenerateContentRequest。
    SSE（sse-starlette EventSourceResponse）：
      event=message → data 为 JSON chunk
      event=error   → data 为 {"error": "..."}
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
    本地混合多条创意（不调 LLM），返回 { success, remixed_idea }。
    Body：{ ideas: [...] }。失败 500。
    """
    try:
        result = service.remix_ideas(request.ideas)
        return {
            "success": True,
            "remixed_idea": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
