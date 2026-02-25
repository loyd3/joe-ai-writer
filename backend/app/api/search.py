from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional
from app.database import get_db
from app.api.auth import get_current_user
from app.models.models import Document, Project

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/")
async def global_search(
    q: str,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """全局搜索 - 搜索项目和文档"""
    if not q or len(q.strip()) < 2:
        return {"projects": [], "documents": [], "total": 0}
    
    search_term = f"%{q.strip()}%"
    user_id = current_user["id"]
    
    # 搜索项目
    project_query = db.query(Project).filter(
        Project.owner_id == user_id,
        or_(
            Project.title.ilike(search_term),
            Project.description.ilike(search_term)
        )
    ).limit(10)
    
    projects = [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "type": "project",
            "updated_at": p.updated_at.isoformat()
        }
        for p in project_query.all()
    ]
    
    # 搜索文档
    doc_query = db.query(Document, Project).join(
        Project, Document.project_id == Project.id
    ).filter(
        Project.owner_id == user_id,
        or_(
            Document.title.ilike(search_term),
            # 搜索文档内容 (JSON 字段)
            text("JSON_SEARCH(content, 'one', :term) IS NOT NULL")
        )
    ).params(term=q.strip()).limit(20)
    
    if project_id:
        doc_query = doc_query.filter(Document.project_id == project_id)
    
    documents = []
    for doc, proj in doc_query.all():
        # 提取匹配的内容片段
        content_text = "\n".join([block.get("content", "") for block in (doc.content or [])])
        snippet = extract_snippet(content_text, q.strip())
        
        documents.append({
            "id": doc.id,
            "title": doc.title,
            "project_id": proj.id,
            "project_title": proj.title,
            "type": "document",
            "snippet": snippet,
            "updated_at": doc.updated_at.isoformat()
        })
    
    return {
        "projects": projects,
        "documents": documents,
        "total": len(projects) + len(documents)
    }

@router.get("/suggest")
async def search_suggestions(
    q: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """搜索建议 - 自动补全"""
    if not q or len(q.strip()) < 1:
        return {"suggestions": []}
    
    search_term = f"%{q.strip()}%"
    user_id = current_user["id"]
    
    suggestions = []
    
    # 项目标题建议
    projects = db.query(Project).filter(
        Project.owner_id == user_id,
        Project.title.ilike(search_term)
    ).limit(5).all()
    
    for p in projects:
        suggestions.append({
            "text": p.title,
            "type": "project",
            "id": p.id
        })
    
    # 文档标题建议
    docs = db.query(Document, Project).join(
        Project, Document.project_id == Project.id
    ).filter(
        Project.owner_id == user_id,
        Document.title.ilike(search_term)
    ).limit(5).all()
    
    for doc, proj in docs:
        suggestions.append({
            "text": doc.title,
            "type": "document",
            "id": doc.id,
            "project_id": proj.id
        })
    
    return {"suggestions": suggestions}

def extract_snippet(text: str, query: str, max_length: int = 150) -> str:
    """提取包含搜索词的内容片段"""
    if not text:
        return ""
    
    # 找到搜索词位置
    idx = text.lower().find(query.lower())
    if idx == -1:
        # 如果找不到，返回前 max_length 个字符
        return text[:max_length] + "..." if len(text) > max_length else text
    
    # 计算片段起始位置
    start = max(0, idx - 50)
    end = min(len(text), idx + len(query) + 50)
    
    snippet = text[start:end]
    
    # 添加省略号
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet
