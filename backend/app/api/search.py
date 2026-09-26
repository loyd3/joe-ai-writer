from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String, func
from typing import List, Optional
from app.database import get_db
from app.api.auth import get_current_user
from app.models.models import Document, Project
from app.services.fulltext_search_service import fulltext_search_service, SearchResult
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


def _escape_like(term: str) -> str:
    """转义 SQL LIKE 通配符，避免用户输入 %/_ 改变匹配语义。"""
    return (
        (term or "")
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _load_user_documents(
    db: Session,
    user_id: int,
    project_id: Optional[int] = None,
    document_id: Optional[int] = None,
    query: Optional[str] = None,
    limit: int = 500,
) -> List[dict]:
    """加载当前用户可见文档，供数据库级关键词检索。

    - 指定 document_id：只加载该文档
    - 指定 project_id：加载该项目全部文档（保证项目内不漏）
    - 全局：SQL 预筛 + 最近更新文档补齐
    """
    base = (
        db.query(Document, Project)
        .join(Project, Document.project_id == Project.id)
        .filter(Project.owner_id == user_id)
    )
    if project_id is not None:
        base = base.filter(Document.project_id == project_id)
    if document_id is not None:
        base = base.filter(Document.id == document_id)

    rows = []
    seen = set()

    # 单文档 / 单项目：全量加载，避免漏检
    if document_id is not None or project_id is not None:
        for doc, proj in base.order_by(Document.updated_at.desc()).all():
            seen.add(doc.id)
            rows.append((doc, proj))
    else:
        if query:
            safe = _escape_like(query.strip())
            term = f"%{safe}%"
            prefilter = base.filter(
                or_(
                    Document.title.ilike(term, escape="\\"),
                    cast(Document.content, String).ilike(term, escape="\\"),
                )
            ).order_by(Document.updated_at.desc()).limit(limit)
            for doc, proj in prefilter.all():
                seen.add(doc.id)
                rows.append((doc, proj))

        # 预筛不足：补最近文档，覆盖 CAST 扫不到的嵌套块结构
        if len(rows) < min(120, limit):
            recent = base.order_by(Document.updated_at.desc()).limit(limit).all()
            for doc, proj in recent:
                if doc.id in seen:
                    continue
                seen.add(doc.id)
                rows.append((doc, proj))
                if len(rows) >= limit:
                    break

    docs = []
    for doc, proj in rows:
        docs.append({
            "document_id": doc.id,
            "document_title": doc.title or "",
            "project_id": proj.id,
            "project_title": proj.title or "",
            "content": doc.content or [],
        })
    return docs


def _merge_search_results(
    primary: List[SearchResult],
    fallback: List[SearchResult],
    top_k: int,
) -> List[SearchResult]:
    """合并索引结果与 DB 兜底结果，同文档同块去重，保留高分。"""
    best: dict = {}
    for r in primary + fallback:
        block_key = (r.block_id or "").strip()
        if block_key:
            soft_key = (r.document_id, f"block:{block_key}")
        else:
            # 无 block_id 时用内容前缀去重，避免索引 chunk 与 DB 块重复
            soft_key = (r.document_id, f"text:{(r.content or '')[:80]}")
        prev = best.get(soft_key)
        if prev is None or r.score > prev.score:
            best[soft_key] = r
    merged = list(best.values())
    merged.sort(key=lambda x: x.score, reverse=True)
    return merged[:top_k]


def _to_items(results: List[SearchResult], project_title_fallback: str = "") -> List[SearchResultItem]:
    items = []
    for r in results:
        items.append(SearchResultItem(
            document_id=r.document_id,
            document_title=r.document_title,
            project_id=r.project_id,
            project_title=r.project_title or project_title_fallback,
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
            context_after=r.context_after,
        ))
    return items


@router.get("/")
async def global_search(
    q: str,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """全局搜索 - 搜索项目和文档（标题 + 正文，不依赖向量索引）"""
    if not q or len(q.strip()) < 2:
        return {"projects": [], "documents": [], "total": 0}
    
    query = q.strip()
    safe_q = _escape_like(query)
    search_term = f"%{safe_q}%"
    user_id = current_user["id"]
    
    project_query = db.query(Project).filter(
        Project.owner_id == user_id,
        or_(
            Project.title.ilike(search_term, escape="\\"),
            Project.description.ilike(search_term, escape="\\")
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

    # 标题快速命中 + JSON 正文模糊（MySQL JSON_SEARCH 需带通配符）
    doc_filters = [
        Document.title.ilike(search_term, escape="\\"),
        cast(Document.content, String).ilike(search_term, escape="\\"),
    ]
    # MySQL JSON_SEARCH 支持 % _ 通配；失败时 CAST 兜底已覆盖
    try:
        doc_filters.append(
            func.json_search(Document.content, "one", f"%{safe_q}%").isnot(None)
        )
    except Exception:
        pass

    doc_query = db.query(Document, Project).join(
        Project, Document.project_id == Project.id
    ).filter(
        Project.owner_id == user_id,
        or_(*doc_filters)
    ).limit(40)
    
    if project_id:
        doc_query = doc_query.filter(Document.project_id == project_id)
    
    documents = []
    seen_ids = set()
    for doc, proj in doc_query.all():
        seen_ids.add(doc.id)
        content_text = fulltext_search_service._chunks_to_text(doc.content or [])
        snippet = extract_snippet(content_text, query)
        if not snippet and query.lower() in (doc.title or "").lower():
            snippet = doc.title or ""
        
        documents.append({
            "id": doc.id,
            "title": doc.title,
            "project_id": proj.id,
            "project_title": proj.title,
            "type": "document",
            "snippet": snippet,
            "updated_at": doc.updated_at.isoformat()
        })

    # CAST/JSON 仍可能漏检复杂块结构：再扫一遍用户文档做精确关键词补全
    if len(documents) < 20:
        extra_docs = _load_user_documents(db, user_id, project_id=project_id, query=query)
        db_hits = fulltext_search_service.search_documents_content(
            query=query,
            documents=extra_docs,
            top_k=20,
        )
        for hit in db_hits:
            if hit.document_id in seen_ids:
                continue
            seen_ids.add(hit.document_id)
            documents.append({
                "id": hit.document_id,
                "title": hit.document_title,
                "project_id": hit.project_id,
                "project_title": hit.project_title,
                "type": "document",
                "snippet": extract_snippet(hit.content, query) or hit.content[:150],
                "updated_at": "",
            })
            if len(documents) >= 20:
                break
    
    return {
        "projects": projects,
        "documents": documents,
        "total": len(projects) + len(documents)
    }


@router.get("/enhanced", response_model=EnhancedSearchResponse)
async def enhanced_search(
    q: str = Query(..., min_length=1, description="搜索查询"),
    project_id: Optional[int] = Query(None, description="限定项目ID"),
    use_semantic: bool = Query(True, description="使用语义搜索"),
    use_keyword: bool = Query(True, description="使用关键词搜索"),
    top_k: int = Query(20, ge=1, le=100, description="返回结果数量"),
    min_score: float = Query(0.15, ge=0, le=1, description="最低相关度分数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    增强搜索 - 向量索引 + 数据库关键词兜底

    索引未建好 / 语义模型不可用时，仍可从数据库正文检索到内容。
    """
    user_id = current_user["id"]
    query = q.strip()
    if len(query) < 1:
        return EnhancedSearchResponse(results=[], total=0, query=q, search_type="none")
    
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
    
    index_results = fulltext_search_service.search(
        query=query,
        user_id=user_id,
        project_ids=project_ids,
        top_k=top_k,
        use_semantic=use_semantic,
        use_keyword=use_keyword,
        min_score=min_score
    )

    # 始终用数据库正文做关键词兜底，解决「没索引 / 索引过期 / 语义阈值」漏检
    db_docs = _load_user_documents(
        db, user_id, project_id=project_id, query=query
    )
    db_results = fulltext_search_service.search_documents_content(
        query=query,
        documents=db_docs,
        top_k=top_k,
    ) if use_keyword else []

    results = _merge_search_results(index_results, db_results, top_k)

    # 补全缺失的 project_title
    project_map = {
        p.id: p.title
        for p in db.query(Project).filter(Project.id.in_(project_ids)).all()
    } if project_ids else {}
    for r in results:
        if not r.project_title and r.project_id in project_map:
            r.project_title = project_map[r.project_id]
    
    search_type = []
    if use_semantic:
        search_type.append("semantic")
    if use_keyword:
        search_type.append("keyword")
    if db_results:
        search_type.append("db")
    
    return EnhancedSearchResponse(
        results=_to_items(results),
        total=len(results),
        query=query,
        search_type="+".join(search_type) if search_type else "none",
        stats=None
    )


@router.get("/document/{document_id}", response_model=EnhancedSearchResponse)
async def search_in_document(
    document_id: int,
    q: str = Query(..., min_length=1, description="搜索查询"),
    top_k: int = Query(10, ge=1, le=50, description="返回结果数量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    文档内搜索 - 索引命中 + 数据库正文兜底
    """
    user_id = current_user["id"]
    query = q.strip()
    
    doc = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == user_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")
    
    index_results = fulltext_search_service.search_in_document(
        query=query,
        document_id=document_id,
        top_k=top_k
    )

    db_results = fulltext_search_service.search_documents_content(
        query=query,
        documents=[{
            "document_id": doc.id,
            "document_title": doc.title or "",
            "project_id": doc.project_id,
            "project_title": doc.project.title if doc.project else "",
            "content": doc.content or [],
        }],
        top_k=top_k,
    )
    results = _merge_search_results(index_results, db_results, top_k)
    
    return EnhancedSearchResponse(
        results=_to_items(results, project_title_fallback=doc.project.title if doc.project else ""),
        total=len(results),
        query=query,
        search_type="keyword+db",
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
