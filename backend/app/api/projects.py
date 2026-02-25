from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    DocumentCreate, DocumentUpdate, DocumentResponse,
    AIMemoryUpdate, AIMemoryResponse
)
from app.models.models import Project, Document, AIMemory
from app.services.ai_memory_service import AIMemoryService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api", tags=["projects"])

# ========== Project Routes ==========
@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的所有项目"""
    projects = db.query(Project).filter(Project.owner_id == current_user["id"]).all()
    return projects

@router.post("/projects", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建新项目（关联当前用户）"""
    db_project = Project(**project.model_dump(), owner_id=current_user["id"])
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # 自动创建 项目设定
    AIMemoryService.get_or_create_memory(db, db_project.id)
    db.refresh(db_project)
    
    return db_project

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取项目详情（检查所有权），文档列表按 order_index 排序"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # 显式加载文档并按 order_index 排序，避免懒加载导致顺序或数量异常
    project.documents = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.order_index.asc(), Document.id.asc())
        .all()
    )
    return project

@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新项目（检查所有权）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for field, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    return project

@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除项目（检查所有权）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}

# ========== Document Routes ==========
def check_project_owner(db: Session, project_id: int, user_id: int):
    """检查用户是否是项目所有者"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return project


def check_document_access(db: Session, document_id: int, user_id: int):
    """检查用户是否有权访问文档（通过项目所有权）"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    check_project_owner(db, document.project_id, user_id)
    return document

@router.get("/projects/{project_id}/documents", response_model=List[DocumentResponse])
def list_documents(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取项目下的所有文档（按 order_index 排序）"""
    check_project_owner(db, project_id, current_user["id"])
    documents = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.order_index.asc(), Document.id.asc())
        .all()
    )
    return documents

@router.post("/projects/{project_id}/documents", response_model=DocumentResponse)
def create_document(
    project_id: int,
    document: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建新文档"""
    check_project_owner(db, project_id, current_user["id"])
    
    db_document = Document(**document.model_dump(), project_id=project_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取文档详情"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 检查权限
    check_project_owner(db, document.project_id, current_user["id"])
    return document

@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 检查权限
    check_project_owner(db, document.project_id, current_user["id"])
    
    for field, value in document_update.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    return document

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 检查权限
    check_project_owner(db, document.project_id, current_user["id"])
    
    db.delete(document)
    db.commit()
    return {"message": "Document deleted"}

# ========== AI Memory Routes ==========
@router.get("/projects/{project_id}/memory", response_model=AIMemoryResponse)
def get_memory(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取项目的 项目设定"""
    check_project_owner(db, project_id, current_user["id"])
    memory = AIMemoryService.get_or_create_memory(db, project_id)
    return memory

@router.put("/projects/{project_id}/memory", response_model=AIMemoryResponse)
def update_memory(
    project_id: int,
    memory_update: AIMemoryUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新项目的 项目设定"""
    check_project_owner(db, project_id, current_user["id"])
    memory = AIMemoryService.update_memory(db, project_id, memory_update)
    return memory
