"""
脑洞写作 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.database import get_db
from app.api.auth import get_current_user_optional
from app.services.brainstorm_writing_service import BrainstormWritingService
from app.services.hot_topics_service import HotTopicsService

router = APIRouter(prefix="/api/brainstorm", tags=["brainstorm"])


# ============ 请求/响应模型 ============

class BrainstormCategoryResponse(BaseModel):
    key: str
    name: str
    description: str


class BrainstormItem(BaseModel):
    title: str
    category: str
    heat: int
    concept: Optional[str] = None
    description: Optional[str] = None
    original_topic: Optional[str] = None
    source: Optional[str] = None


class BrainstormOutlineRequest(BaseModel):
    title: str
    category: str
    concept: Optional[str] = None
    style: str = "幽默风趣"
    word_count: str = "medium"


class BrainstormArticleRequest(BaseModel):
    title: str
    category: str
    concept: Optional[str] = None
    style: str = "幽默风趣"
    word_count: str = "medium"
    outline: Optional[Dict[str, Any]] = None


class ArticleResponse(BaseModel):
    title: str
    content: str
    word_count: int
    style: str
    generated_at: str


# ============ API 端点 ============

@router.get("/categories", response_model=List[BrainstormCategoryResponse])
async def get_brainstorm_categories():
    """获取所有脑洞分类"""
    return BrainstormWritingService.get_categories()


@router.get("/trending", response_model=List[BrainstormItem])
async def get_trending_brainstorms(limit: int = 20):
    """获取热门脑洞话题"""
    brainstorms = BrainstormWritingService.get_trending_brainstorms(limit)
    return brainstorms


@router.get("/random")
async def get_random_brainstorm(category: Optional[str] = None):
    """获取随机脑洞话题"""
    brainstorm = BrainstormWritingService.generate_random_brainstorm(category)
    return brainstorm


@router.get("/from-hot-topics")
async def get_brainstorms_from_hot_topics(limit: int = 5):
    """基于当前热点生成脑洞话题"""
    brainstorms = await BrainstormWritingService.generate_from_hot_topics(limit)
    return {
        "brainstorms": brainstorms,
        "total": len(brainstorms)
    }


@router.post("/generate-outline")
async def generate_brainstorm_outline(
    request: BrainstormOutlineRequest,
    current_user: Optional[Dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """为脑洞话题生成大纲"""
    brainstorm = {
        "title": request.title,
        "category": request.category,
        "concept": request.concept
    }
    
    outline = await BrainstormWritingService.generate_outline(
        brainstorm=brainstorm,
        style=request.style,
        word_count=request.word_count,
        db=db
    )
    
    return {
        "success": True,
        "outline": outline,
        "brainstorm": brainstorm
    }


@router.post("/generate-article")
async def generate_brainstorm_article(
    request: BrainstormArticleRequest,
    current_user: Optional[Dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """根据脑洞话题生成完整文章"""
    brainstorm = {
        "title": request.title,
        "category": request.category,
        "concept": request.concept
    }
    
    article = await BrainstormWritingService.generate_article(
        brainstorm=brainstorm,
        outline=request.outline,
        style=request.style,
        word_count=request.word_count,
        db=db
    )
    
    return {
        "success": True,
        "article": article
    }


@router.post("/quick-generate")
async def quick_generate_brainstorm_article(
    category: Optional[str] = None,
    style: str = "幽默风趣",
    word_count: str = "medium",
    current_user: Optional[Dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """快速生成：随机选择脑洞话题并生成文章"""
    # 生成随机脑洞
    brainstorm = BrainstormWritingService.generate_random_brainstorm(category)
    
    # 生成文章
    article = await BrainstormWritingService.generate_article(
        brainstorm=brainstorm,
        style=style,
        word_count=word_count,
        db=db
    )
    
    return {
        "success": True,
        "brainstorm": brainstorm,
        "article": article
    }


@router.post("/from-hot-topic/{index}")
async def generate_from_hot_topic_index(
    index: int = 0,
    style: str = "幽默风趣",
    word_count: str = "medium",
    current_user: Optional[Dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """基于指定索引的热点生成脑洞文章"""
    # 获取热点
    hot_topics_data = await HotTopicsService.fetch_all_hot_topics()
    hot_topics = hot_topics_data.get("topics", [])
    
    if not hot_topics or index >= len(hot_topics):
        raise HTTPException(
            status_code=404,
            detail="没有找到指定索引的热点"
        )
    
    # 生成脑洞
    brainstorm = BrainstormWritingService.generate_brainstorm_from_hot_topic(hot_topics[index])
    
    # 生成文章
    article = await BrainstormWritingService.generate_article(
        brainstorm=brainstorm,
        style=style,
        word_count=word_count,
        db=db
    )
    
    return {
        "success": True,
        "hot_topic": hot_topics[index],
        "brainstorm": brainstorm,
        "article": article
    }
