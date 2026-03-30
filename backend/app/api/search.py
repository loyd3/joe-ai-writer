from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional
from app.database import get_db
from app.api.auth import get_current_user
from app.models.models import Document, Project
from app.services.fulltext_search_service import fulltext_search_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResultItem(BaseModel):
    document_id: int
    document_title: str
    project_id: int
    project_title: str
    chunk_index: int
    content: str
    start_offset: int
    end_offset: int
    block_id: Optional[str] = None
    block_type: Optional[str] = None
    score: float
    match_type: str
    highlights: List[List[int]] = []
    context_before: str = ""
    context_after: str = ""


class EnhancedSearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int
    query: str
    search_type: str
    stats: Optional[dict] = None


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
    
    doc_query = db.query(Document, Project).join(
        Project, Document.project_id == Project.id
    ).filter(
        Project.owner_id == user_id,
        or_(
            Document.title.ilike(search_term),
            text("JSON_SEARCH(content, 'one', :term) IS NOT NULL")
        )
    ).params(term=q.strip()).limit(20)
    
    if project_id:
        doc_query = doc_query.filter(Document.project_id == project_id)
    
    documents = []
    for doc, proj in doc_query.all():
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


@router.get("/enhanced", response_model=EnhancedSearchResponse)
async def enhanced_search(
    q: str = Query(..., min_length=2, description="搜索查询"),
    project_id: Optional[int] = Query(None, description="限定项目ID"),
    use_semantic: bool = Query(True, description="使用语义搜索"),
    use_keyword: bool = Query(True, description="使用关键词搜索"),
    top_k: int = Query(20, ge=1, le=100, description="返回结果数量"),
    min_score: float = Query(0.3, ge=0, le=1, description="最低相关度分数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    增强搜索 - 支持语义搜索和精确位置定位
    
    特性：
    - 语义搜索：理解查询意图，找到相关内容
    - 关键词搜索：精确匹配关键词
    - 精确位置：返回内容在文档中的精确位置
    - 高亮显示：标记匹配的文本片段
    """
    user_id = current_user["id"]
    
    user_projects = db.query(Project.id).filter(
        Project.owner_id == user_id
    ).all()
    user_project_ids = [p.id for p in user_projects]
    
    if project_id:
        if project_id not in user_project_ids:
            raise HTTPException(status_code=403, detail="无权访问该项目")
        project_ids = [project_id]
    else:
        project_ids = user_project_ids
    
    results = fulltext_search_service.search(
        query=q,
        user_id=user_id,
        project_ids=project_ids,
        top_k=top_k,
        use_semantic=use_semantic,
        use_keyword=use_keyword,
        min_score=min_score
    )
    
    search_results = []
    for r in results:
        project_title = ""
        if r.project_id:
            project = db.query(Project).filter(Project.id == r.project_id).first()
            if project:
                project_title = project.title
        
        search_results.append(SearchResultItem(
            document_id=r.document_id,
            document_title=r.document_title,
            project_id=r.project_id,
            project_title=project_title,
            chunk_index=r.chunk_index,
            content=r.content,
            start_offset=r.start_offset,
            end_offset=r.end_offset,
            block_id=r.block_id,
            block_type=r.block_type,
            score=round(r.score, 3),
            match_type=r.match_type,
            highlights=[list(h) for h in r.highlights],
            context_before=r.context_before,
            context_after=r.context_after
        ))
    
    search_type = []
    if use_semantic:
        search_type.append("semantic")
    if use_keyword:
        search_type.append("keyword")
    
    return EnhancedSearchResponse(
        results=search_results,
        total=len(search_results),
        query=q,
        search_type="+".join(search_type) if search_type else "none",
        stats=None
    )


@router.get("/document/{document_id}", response_model=EnhancedSearchResponse)
async def search_in_document(
    document_id: int,
    q: str = Query(..., min_length=2, description="搜索查询"),
    top_k: int = Query(10, ge=1, le=50, description="返回结果数量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    文档内搜索 - 在指定文档中搜索并返回精确位置
    
    返回所有匹配位置，包括：
    - 内容片段
    - 字符偏移量
    - 块信息（block_id, block_type）
    - 上下文
    """
    user_id = current_user["id"]
    
    doc = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == user_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")
    
    results = fulltext_search_service.search_in_document(
        query=q,
        document_id=document_id,
        top_k=top_k
    )
    
    search_results = []
    for r in results:
        search_results.append(SearchResultItem(
            document_id=r.document_id,
            document_title=doc.title,
            project_id=r.project_id,
            project_title=doc.project.title if doc.project else "",
            chunk_index=r.chunk_index,
            content=r.content,
            start_offset=r.start_offset,
            end_offset=r.end_offset,
            block_id=r.block_id,
            block_type=r.block_type,
            score=round(r.score, 3),
            match_type=r.match_type,
            highlights=[list(h) for h in r.highlights],
            context_before=r.context_before,
            context_after=r.context_after
        ))
    
    return EnhancedSearchResponse(
        results=search_results,
        total=len(search_results),
        query=q,
        search_type="keyword",
        stats=None
    )


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


@router.get("/stats")
async def search_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取搜索索引统计信息"""
    stats = fulltext_search_service.get_stats()
    return stats


@router.post("/index/document/{document_id}")
async def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """手动索引指定文档"""
    user_id = current_user["id"]
    
    doc = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == user_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")
    
    indexed_count = fulltext_search_service.index_document(
        document_id=doc.id,
        document_title=doc.title,
        project_id=doc.project_id,
        content=doc.content,
        metadata={
            "project_title": doc.project.title if doc.project else ""
        }
    )
    
    return {
        "success": True,
        "document_id": document_id,
        "indexed_chunks": indexed_count
    }


@router.post("/index/project/{project_id}")
async def index_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """手动索引项目下所有文档"""
    user_id = current_user["id"]
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权访问")
    
    documents = db.query(Document).filter(
        Document.project_id == project_id
    ).all()
    
    total_chunks = 0
    indexed_docs = 0
    
    for doc in documents:
        chunks = fulltext_search_service.index_document(
            document_id=doc.id,
            document_title=doc.title,
            project_id=project_id,
            content=doc.content,
            metadata={
                "project_title": project.title
            }
        )
        if chunks > 0:
            indexed_docs += 1
            total_chunks += chunks
    
    return {
        "success": True,
        "project_id": project_id,
        "indexed_documents": indexed_docs,
        "total_chunks": total_chunks
    }


@router.post("/index/all")
async def index_all_documents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """初始化索引当前用户所有文档"""
    user_id = current_user["id"]
    
    projects = db.query(Project).filter(
        Project.owner_id == user_id
    ).all()
    
    project_ids = [p.id for p in projects]
    project_map = {p.id: p.title for p in projects}
    
    documents = db.query(Document).filter(
        Document.project_id.in_(project_ids)
    ).all()
    
    total_chunks = 0
    indexed_docs = 0
    
    for doc in documents:
        if not doc.content:
            continue
        chunks = fulltext_search_service.index_document(
            document_id=doc.id,
            document_title=doc.title,
            project_id=doc.project_id,
            content=doc.content,
            metadata={
                "project_title": project_map.get(doc.project_id, "")
            }
        )
        if chunks > 0:
            indexed_docs += 1
            total_chunks += chunks
    
    return {
        "success": True,
        "indexed_documents": indexed_docs,
        "total_chunks": total_chunks,
        "total_projects": len(projects)
    }


@router.delete("/index/document/{document_id}")
async def remove_document_index(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除文档的搜索索引"""
    user_id = current_user["id"]
    
    doc = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == user_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")
    
    fulltext_search_service.remove_document(document_id)
    
    return {"success": True, "message": f"已删除文档 {document_id} 的索引"}


def extract_snippet(text: str, query: str, max_length: int = 150) -> str:
    """提取包含搜索词的内容片段"""
    if not text:
        return ""
    
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:max_length] + "..." if len(text) > max_length else text
    
    start = max(0, idx - 50)
    end = min(len(text), idx + len(query) + 50)
    
    snippet = text[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet
