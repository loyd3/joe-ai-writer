"""
热点写作 API 路由 - 增强版
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services.enhanced_hot_topics_service import EnhancedHotTopicsService
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService
from app.api.dependencies import get_llm_service, get_cache_service
import json

router = APIRouter(prefix="/hot-topics", tags=["热点写作"])


class TopicAnalysisRequest(BaseModel):
    topic_title: str = Field(..., description="话题标题")
    topic_keyword: str = Field(..., description="核心关键词")
    topic_aspect: str = Field(..., description="分析角度")
    category: str = Field(..., description="所属分类")
    analysis_depth: str = Field(default="standard", description="分析深度: basic/standard/deep")


class ArticleOutlineRequest(BaseModel):
    topic_title: str = Field(..., description="话题标题")
    topic_keyword: str = Field(..., description="核心关键词")
    topic_aspect: str = Field(..., description="分析角度")
    category: str = Field(..., description="所属分类")
    article_type: str = Field(default="评论", description="文章类型")
    word_count: int = Field(default=1500, ge=500, le=5000)


class ArticleGenerateRequest(BaseModel):
    topic_title: str = Field(..., description="话题标题")
    topic_keyword: str = Field(..., description="核心关键词")
    topic_aspect: str = Field(..., description="分析角度")
    category: str = Field(..., description="所属分类")
    outline: dict = Field(..., description="文章大纲")
    article_type: str = Field(default="评论", description="文章类型")
    word_count: int = Field(default=1500, ge=500, le=5000)
    style: str = Field(default="专业", description="写作风格")


def get_hot_topics_service(
    llm_service: LLMService = Depends(get_llm_service),
    cache_service: CacheService = Depends(get_cache_service)
) -> EnhancedHotTopicsService:
    return EnhancedHotTopicsService(llm_service, cache_service)


@router.get("/categories")
async def get_categories(
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service)
):
    """获取热点分类列表"""
    return {
        "categories": service.get_categories()
    }


@router.get("/topics")
async def get_hot_topics(
    category: Optional[str] = Query(None, description="分类筛选"),
    limit: int = Query(10, ge=1, le=20, description="返回数量"),
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service)
):
    """
    获取热点话题列表
    """
    try:
        topics = await service.get_hot_topics(category=category, limit=limit)
        return {
            "success": True,
            "data": topics,
            "total": len(topics)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_topic(
    request: TopicAnalysisRequest,
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service)
):
    """
    深度分析热点话题
    """
    try:
        result = await service.analyze_topic(
            topic_title=request.topic_title,
            topic_keyword=request.topic_keyword,
            topic_aspect=request.topic_aspect,
            category=request.category,
            analysis_depth=request.analysis_depth
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outline")
async def generate_outline(
    request: ArticleOutlineRequest,
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service)
):
    """
    生成文章大纲
    """
    try:
        result = await service.generate_article_outline(
            topic_title=request.topic_title,
            topic_keyword=request.topic_keyword,
            topic_aspect=request.topic_aspect,
            category=request.category,
            article_type=request.article_type,
            word_count=request.word_count
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-stream")
async def generate_article_stream(
    request: ArticleGenerateRequest,
    service: EnhancedHotTopicsService = Depends(get_hot_topics_service)
):
    """
    流式生成热点文章
    """
    async def event_generator():
        try:
            async for chunk in service.generate_article_stream(
                topic_title=request.topic_title,
                topic_keyword=request.topic_keyword,
                topic_aspect=request.topic_aspect,
                category=request.category,
                outline=request.outline,
                article_type=request.article_type,
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
