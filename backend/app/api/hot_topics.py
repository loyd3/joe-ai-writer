from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.database import get_db
from app.api.auth import get_current_user, get_current_user_optional
from app.services.hot_topics_writing_service import HotTopicsWritingService
from app.services.hot_topics_service import HotTopicsService
from app.schemas.schemas import HotTopicsRequest, HotTopicsOutlineRequest, HotTopicsArticleRequest

# 热点来源平台（传统抓取）
LEGACY_PLATFORMS = [
    {"id": "weibo", "name": "微博热搜"},
    {"id": "zhihu", "name": "知乎热榜"},
    {"id": "baidu", "name": "百度热搜"},
    {"id": "toutiao", "name": "头条热榜"},
]

router = APIRouter(prefix="/api/hot-topics", tags=["hot-topics"])


@router.get("/list")
async def get_hot_topics(
    current_user: dict = Depends(get_current_user_optional)
):
    """获取网络热点列表"""
    try:
        result = await HotTopicsWritingService.get_hot_topics()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热点失败: {str(e)}")


@router.get("/platforms")
async def get_platforms(
    current_user: dict = Depends(get_current_user)
):
    """获取热点来源平台列表"""
    return {
        "success": True,
        "platforms": LEGACY_PLATFORMS,
        "total": len(LEGACY_PLATFORMS)
    }


@router.get("/search")
async def search_hot_topics(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    current_user: dict = Depends(get_current_user)
):
    """搜索热点话题（从当前热点列表中按关键词过滤）"""
    try:
        result = await HotTopicsService.fetch_all_hot_topics()
        topics = result.get("topics", [])
        keyword_lower = keyword.lower().strip()
        filtered = [
            t for t in topics
            if keyword_lower in (t.get("title") or "").lower()
        ][:limit]
        return {
            "success": True,
            "keyword": keyword,
            "results": filtered,
            "total": len(filtered)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/generate-outline")
async def generate_outline(
    request: HotTopicsOutlineRequest,
    current_user: dict = Depends(get_current_user)
):
    """根据热点话题生成文章大纲（非流式）"""
    try:
        outline = await HotTopicsWritingService.generate_outline(
            topic_title=request.topic_title,
            topic_source=request.topic_source,
            article_type=request.article_type,
            word_count=request.word_count,
            style=request.style
        )
        
        if "error" in outline:
            error_msg = outline["error"]
            # 检查是否是配置错误
            if "配置" in error_msg or "API Key" in error_msg:
                raise HTTPException(status_code=400, detail=error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        return {
            "success": True,
            "outline": outline
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成大纲失败: {str(e)}")


@router.post("/generate-outline/stream")
async def generate_outline_stream(
    request: HotTopicsOutlineRequest,
    current_user: dict = Depends(get_current_user)
):
    """根据热点话题生成文章大纲（流式）"""
    async def generate():
        async for chunk in HotTopicsWritingService.generate_outline_stream(
            topic_title=request.topic_title,
            topic_source=request.topic_source,
            article_type=request.article_type,
            word_count=request.word_count,
            style=request.style
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/generate-article")
async def generate_article(
    request: HotTopicsArticleRequest,
    current_user: dict = Depends(get_current_user)
):
    """根据大纲生成完整文章（非流式）"""
    try:
        article = await HotTopicsWritingService.generate_article(
            outline=request.outline,
            selected_title=request.selected_title,
            additional_requirements=request.additional_requirements
        )
        
        # 检查文章是否返回错误信息
        if article.startswith("[配置错误]") or article.startswith("[错误]"):
            raise HTTPException(status_code=500, detail=article)
        
        return {
            "success": True,
            "article": article,
            "title": request.selected_title or request.outline.get("title_options", ["热点文章"])[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成文章失败: {str(e)}")


@router.post("/generate-article/stream")
async def generate_article_stream(
    request: HotTopicsArticleRequest,
    current_user: dict = Depends(get_current_user)
):
    """根据大纲生成完整文章（流式）"""
    async def generate():
        async for chunk in HotTopicsWritingService.generate_article_stream(
            outline=request.outline,
            selected_title=request.selected_title,
            additional_requirements=request.additional_requirements
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/create-document")
async def create_document_from_hot_topic(
    request: HotTopicsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """将生成的文章保存为项目文档"""
    from app.models.models import Project
    
    # 检查项目权限
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user["id"]
    ).first()
    
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    
    try:
        document = await HotTopicsWritingService.create_document_from_article(
            db=db,
            project_id=request.project_id,
            title=request.title,
            content=request.content,
            outline_data=request.outline_data,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "document": {
                "id": document.id,
                "title": document.title,
                "project_id": document.project_id,
                "created_at": document.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建文档失败: {str(e)}")


@router.post("/quick-write")
async def quick_write_from_hot_topic(
    request: HotTopicsOutlineRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    一键写作：热点 → 大纲 → 文章 → 保存文档
    这是一个组合接口，适合快速生成文章
    """
    from app.models.models import Project
    
    # 检查项目权限
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user["id"]
    ).first()
    
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    
    try:
        # 1. 生成大纲
        outline = await HotTopicsWritingService.generate_outline(
            topic_title=request.topic_title,
            topic_source=request.topic_source,
            article_type=request.article_type,
            word_count=request.word_count,
            style=request.style
        )
        
        if "error" in outline:
            raise HTTPException(status_code=500, detail=f"大纲生成失败: {outline['error']}")
        
        # 2. 生成文章
        selected_title = outline.get("title_options", [request.topic_title])[0]
        article = await HotTopicsWritingService.generate_article(
            outline=outline,
            selected_title=selected_title
        )
        
        # 检查文章是否返回错误信息
        if article.startswith("[配置错误]") or article.startswith("[错误]"):
            raise HTTPException(status_code=500, detail=article)
        
        # 3. 保存为文档
        document = await HotTopicsWritingService.create_document_from_article(
            db=db,
            project_id=request.project_id,
            title=selected_title,
            content=article,
            outline_data=outline,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "outline": outline,
            "article": article,
            "document": {
                "id": document.id,
                "title": document.title,
                "project_id": document.project_id,
                "created_at": document.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一键写作失败: {str(e)}")
