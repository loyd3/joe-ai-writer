from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    AIMemoryUpdate,
    AIMemoryResponse,
)
from app.models.models import Project, Document, AIMemory
from app.services.ai_memory_service import AIMemoryService
from app.services.user_service import get_or_create_default_user

router = APIRouter(prefix="/api", tags=["projects"])


# ========== Project Routes ==========
@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """获取所有项目"""
    projects = db.query(Project).all()
    return projects


@router.post("/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """创建新项目"""
    default_user = get_or_create_default_user(db)
    db_project = Project(**project.model_dump(), owner_id=default_user.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # 自动创建 AI 记忆
    AIMemoryService.get_or_create_memory(db, db_project.id)
    db.refresh(db_project)

    return db_project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """更新项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """删除项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


# ========== Document Routes ==========
@router.get("/projects/{project_id}/documents", response_model=List[DocumentResponse])
def list_documents(project_id: int, db: Session = Depends(get_db)):
    """获取项目下的所有文档"""
    documents = db.query(Document).filter(Document.project_id == project_id).all()
    return documents


@router.post("/projects/{project_id}/documents", response_model=DocumentResponse)
def create_document(project_id: int, document: DocumentCreate, db: Session = Depends(get_db)):
    """创建新文档"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_document = Document(**document.model_dump(), project_id=project_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """获取文档详情"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int, document_update: DocumentUpdate, db: Session = Depends(get_db)
):
    """更新文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in document_update.model_dump(exclude_unset=True).items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)
    return document


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """删除文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()
    return {"message": "Document deleted"}


# ========== AI Memory Routes ==========
@router.get("/projects/{project_id}/memory", response_model=AIMemoryResponse)
def get_memory(project_id: int, db: Session = Depends(get_db)):
    """获取项目的 AI 记忆"""
    memory = AIMemoryService.get_or_create_memory(db, project_id)
    return memory


@router.put("/projects/{project_id}/memory", response_model=AIMemoryResponse)
def update_memory(project_id: int, memory_update: AIMemoryUpdate, db: Session = Depends(get_db)):
    """更新项目的 AI 记忆"""
    memory = AIMemoryService.update_memory(db, project_id, memory_update)
    return memory
