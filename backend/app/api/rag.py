from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.api.auth import get_current_user
from app.api.projects import check_project_owner
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/rag", tags=["rag"])

@router.get("/search/{project_id}")
async def search_memory(
    project_id: int,
    q: str,
    types: Optional[str] = None,  # 逗号分隔的类型列表
    top_k: int = 3,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    搜索项目设定
    
    Args:
        q: 搜索查询
        types: 要搜索的类型，如 "characters,outline"，为空则搜索所有
        top_k: 返回结果数量
    """
    check_project_owner(db, project_id, current_user["id"])
    
    memory_types = None
    if types:
        memory_types = [t.strip() for t in types.split(",")]
    
    results = rag_service.search_memory(project_id, q, memory_types, top_k)
    
    return {
        "query": q,
        "project_id": project_id,
        "results": results,
        "total": sum(len(items) for items in results.values())
    }

@router.get("/context/{project_id}")
async def get_context(
    project_id: int,
    q: str,
    max_length: int = 1500,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取格式化的上下文字符串（用于调试）"""
    check_project_owner(db, project_id, current_user["id"])
    
    context = rag_service.build_context_string(project_id, q, max_length)
    
    return {
        "query": q,
        "project_id": project_id,
        "context": context,
        "length": len(context)
    }

@router.post("/reindex/{project_id}")
async def reindex_memory(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """重新索引项目的所有设定"""
    from app.services.ai_memory_service import AIMemoryService
    
    check_project_owner(db, project_id, current_user["id"])
    
    # 删除旧索引
    rag_service.delete_project_memory(project_id)
    
    # 重新索引
    memory = AIMemoryService.get_or_create_memory(db, project_id)
    AIMemoryService._index_memory_to_rag(project_id, memory)
    
    return {
        "message": "重新索引完成",
        "project_id": project_id
    }
