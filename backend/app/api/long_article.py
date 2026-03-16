"""
长篇文章生成API路由
支持百万字级别的文章生成
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from app.database import get_db
from app.services.long_article_service import LongArticleService
from app.models.models import Article, ArticleChapter
import json

router = APIRouter(prefix="/api/long-article", tags=["long-article"])


class CreateArticleRequest(BaseModel):
    """创建长篇文章请求；可带 story_data 从 AI 故事生成器导入设定并直接生成大纲"""
    project_id: int
    topic: str = Field("", description="文章主题（从故事创建时可留空，将用故事主题）")
    target_words: int = Field(..., ge=10000, le=2000000, description="目标字数（1万-200万）")
    style: str = Field(default="专业", description="写作风格")
    requirements: Optional[str] = Field(None, description="额外要求")
    story_data: Optional[Dict[str, Any]] = Field(None, description="AI 故事生成器的完整设定，传入则用其大纲与设定生成长文")


class GenerateOutlineRequest(BaseModel):
    """生成大纲请求"""
    article_id: int
    regenerate: bool = Field(default=False, description="是否重新生成")


class ChapterInfo(BaseModel):
    """章节信息"""
    chapter_index: int
    title: str
    content: str
    word_count: int


class ArticleProgressResponse(BaseModel):
    """文章进度响应"""
    article_id: int
    status: str
    progress: int
    total_chapters: int
    completed_chapters: int
    outline: Optional[dict] = None


@router.post("/create")
async def create_article(
    request: CreateArticleRequest,
    db: Session = Depends(get_db)
):
    """
    创建长篇文章任务。若传入 story_data（来自 AI 故事生成器），则直接用故事大纲与设定，无需再生成大纲。
    """
    topic = request.topic or ""
    if request.story_data:
        topic = (
            topic
            or request.story_data.get("input_theme")
            or request.story_data.get("core_theme")
            or (request.story_data.get("title_options") or ["未命名"])[0]
        )
    if not topic:
        raise HTTPException(status_code=400, detail="请提供 topic 或 story_data")

    article = Article(
        project_id=request.project_id,
        topic=topic,
        target_words=request.target_words,
        style=request.style,
        requirements=request.requirements,
        status="pending",
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    if request.story_data:
        outline = LongArticleService.outline_from_story(request.story_data, request.target_words)
        article.outline = outline
        article.status = "outlined"
        db.commit()
        db.refresh(article)

    return {
        "article_id": article.id,
        "message": "文章任务创建成功" + ("，已使用故事设定生成大纲" if request.story_data else ""),
        "status": article.status,
        "outline": article.outline if request.story_data else None,
    }


@router.post("/generate-outline")
async def generate_outline(
    request: GenerateOutlineRequest,
    db: Session = Depends(get_db)
):
    """
    生成文章大纲
    """
    article = db.query(Article).filter(Article.id == request.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if article.outline and not request.regenerate:
        return {
            "message": "大纲已存在",
            "outline": json.loads(article.outline)
        }
    
    service = LongArticleService(db)
    outline = await service.generate_outline(
        article.id,
        article.topic,
        article.target_words,
        article.style,
        article.requirements
    )
    
    return {
        "message": "大纲生成成功",
        "outline": outline
    }


def _generate_article_stream_impl(article_id: int, db: Session):
    """流式生成完整文章的实现（POST/GET 共用）"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == "completed":
        raise HTTPException(status_code=400, detail="文章已完成生成")
    service = LongArticleService(db)

    async def event_generator():
        try:
            async for event in service.generate_full_article(
                article_id,
                article.topic,
                article.target_words,
                article.style,
                article.requirements,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate/{article_id}")
async def generate_article_stream_post(
    article_id: int,
    db: Session = Depends(get_db),
):
    """流式生成完整文章（POST）"""
    return _generate_article_stream_impl(article_id, db)


@router.get("/generate/{article_id}")
async def generate_article_stream_get(
    article_id: int,
    db: Session = Depends(get_db),
):
    """流式生成完整文章（GET，供 EventSource 使用）"""
    return _generate_article_stream_impl(article_id, db)


@router.post("/resume/{article_id}")
async def resume_article_generation(
    article_id: int,
    db: Session = Depends(get_db)
):
    """
    恢复未完成的文章生成
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if article.status == "completed":
        raise HTTPException(status_code=400, detail="文章已完成，无需恢复")
    
    service = LongArticleService(db)
    
    async def event_generator():
        try:
            async for event in service.resume_generation(article_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "data": {"message": str(e)}
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/progress/{article_id}", response_model=ArticleProgressResponse)
async def get_article_progress(
    article_id: int,
    db: Session = Depends(get_db)
):
    """
    获取文章生成进度
    """
    service = LongArticleService(db)
    try:
        progress = service.get_article_progress(article_id)
        return ArticleProgressResponse(
            article_id=article_id,
            **progress
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/chapters/{article_id}")
async def get_article_chapters(
    article_id: int,
    db: Session = Depends(get_db)
):
    """
    获取文章所有章节
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    chapters = (
        db.query(ArticleChapter)
        .filter(ArticleChapter.article_id == article_id)
        .order_by(ArticleChapter.chapter_index)
        .all()
    )
    
    return {
        "article_id": article_id,
        "title": article.title,
        "status": article.status,
        "total_chapters": len(chapters),
        "chapters": [
            {
                "chapter_index": ch.chapter_index,
                "title": ch.title,
                "content": ch.content,
                "word_count": ch.word_count,
                "created_at": ch.created_at.isoformat()
            }
            for ch in chapters
        ]
    }


@router.get("/export/{article_id}")
async def export_article(
    article_id: int,
    format: str = "txt",  # txt, md, json
    db: Session = Depends(get_db)
):
    """
    导出完整文章
    支持格式：txt, md, json
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    chapters = (
        db.query(ArticleChapter)
        .filter(ArticleChapter.article_id == article_id)
        .order_by(ArticleChapter.chapter_index)
        .all()
    )
    
    if format == "json":
        return {
            "article": {
                "id": article.id,
                "title": article.title or article.topic,
                "topic": article.topic,
                "style": article.style,
                "target_words": article.target_words,
                "status": article.status,
                "outline": json.loads(article.outline) if article.outline else None,
                "chapters": [
                    {
                        "index": ch.chapter_index,
                        "title": ch.title,
                        "content": ch.content,
                        "word_count": ch.word_count
                    }
                    for ch in chapters
                ]
            }
        }
    
    # 生成文本内容
    content_lines = []
    
    if article.title:
        content_lines.append(f"# {article.title}\n")
    else:
        content_lines.append(f"# {article.topic}\n")
    
    content_lines.append(f"\n作者：AI生成")
    content_lines.append(f"风格：{article.style}")
    content_lines.append(f"总字数：{sum(ch.word_count for ch in chapters):,} 字\n")
    content_lines.append("=" * 50 + "\n")
    
    for ch in chapters:
        if format == "md":
            content_lines.append(f"\n## {ch.title}\n")
        else:
            content_lines.append(f"\n{ch.title}\n")
            content_lines.append("-" * 40 + "\n")
        
        content_lines.append(ch.content)
        content_lines.append("\n")
    
    full_content = "\n".join(content_lines)
    
    # 返回文件下载
    from fastapi.responses import Response
    
    filename = f"{article.title or article.topic}_{article.id}.{format}"
    
    return Response(
        content=full_content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """
    删除文章及其所有章节
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    db.delete(article)
    db.commit()
    
    return {"message": "文章已删除"}


@router.get("/list")
async def list_articles(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    获取文章列表
    """
    query = db.query(Article)
    
    if project_id:
        query = query.filter(Article.project_id == project_id)
    
    if status:
        query = query.filter(Article.status == status)
    
    total = query.count()
    articles = query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "articles": [
            {
                "id": art.id,
                "title": art.title or art.topic,
                "topic": art.topic,
                "target_words": art.target_words,
                "style": art.style,
                "status": art.status,
                "created_at": art.created_at.isoformat(),
                "completed_at": art.completed_at.isoformat() if art.completed_at else None
            }
            for art in articles
        ]
    }
