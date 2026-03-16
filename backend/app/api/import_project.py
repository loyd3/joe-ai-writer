"""
项目导入 API：上传导出的项目 JSON，创建为新项目
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

from app.database import get_db
from app.api.auth import get_current_user
from app.models.models import Project, Document, AIMemory
from app.services.ai_memory_service import AIMemoryService

router = APIRouter(prefix="/api/import", tags=["import"])


class ImportProjectRequest(BaseModel):
    """导入项目请求体（与导出 JSON 结构一致）"""
    version: int = Field(1, description="数据包版本")
    project: Dict[str, Any] = Field(..., description="项目信息 title, description")
    documents: List[Dict[str, Any]] = Field(default_factory=list, description="文档列表，每项含 title, content, order_index, parent_index")
    memory: Optional[Dict[str, Any]] = Field(None, description="项目设定")


@router.post("/project")
def import_project(
    body: ImportProjectRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    导入项目包（JSON），创建为新项目。
    请求体需与「导出为项目包(JSON)」的格式一致。
    """
    title = (body.project or {}).get("title") or "导入的项目"
    description = (body.project or {}).get("description") or ""

    # 创建项目
    project = Project(
        title=title,
        description=description,
        owner_id=current_user["id"],
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # 创建项目设定
    AIMemoryService.get_or_create_memory(db, project.id)
    memory_data = body.memory or {}
    update = {
        "outline": memory_data.get("outline") or [],
        "storyline": memory_data.get("storyline") or "",
        "characters": memory_data.get("characters") or [],
        "world_building": memory_data.get("world_building") or {},
        "writing_style": memory_data.get("writing_style") or "",
        "key_points": memory_data.get("key_points") or [],
        "notes": memory_data.get("notes") or "",
    }
    from app.schemas.schemas import AIMemoryUpdate
    AIMemoryService.update_memory(db, project.id, AIMemoryUpdate(**update))

    # 按顺序创建文档，parent_index 指向同列表中前面的索引
    new_doc_ids: List[Optional[int]] = [None] * len(body.documents)
    for i, doc_item in enumerate(body.documents):
        parent_id = None
        if doc_item.get("parent_index") is not None:
            idx = doc_item["parent_index"]
            if 0 <= idx < len(new_doc_ids) and new_doc_ids[idx] is not None:
                parent_id = new_doc_ids[idx]
        doc = Document(
            project_id=project.id,
            title=doc_item.get("title") or "未命名文档",
            content=doc_item.get("content") if doc_item.get("content") is not None else [],
            order_index=doc_item.get("order_index", 0),
            parent_id=parent_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        new_doc_ids[i] = doc.id

    return {
        "success": True,
        "message": "项目导入成功",
        "project_id": project.id,
        "project_title": project.title,
        "documents_count": len(body.documents),
    }
