from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.models import Project, Document, AIMemory, AIInteraction
from app.schemas.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    DocumentCreate, DocumentUpdate, DocumentResponse,
    AIMemoryUpdate, AIMemoryResponse
)
from app.services.ai_memory_service import AIMemoryService
from app.services.fulltext_search_service import fulltext_search_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api", tags=["projects"])

# ========== Project Routes ==========
@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的所有项目（优化版，预加载关联数据）"""
    projects = db.query(Project).filter(
        Project.owner_id == current_user["id"]
    ).options(
        joinedload(Project.documents),
        joinedload(Project.ai_memory)
    ).all()
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
    """获取项目详情（检查所有权），文档列表按 order_index 排序（优化版）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).options(
        joinedload(Project.documents),
        joinedload(Project.ai_memory)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 对文档进行内存排序（避免额外查询）
    if project.documents:
        project.documents = sorted(
            project.documents,
            key=lambda d: (d.order_index, d.id)
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除项目（检查所有权）- 先删除关联数据再删除项目"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    document_ids = [doc.id for doc in project.documents]

    if document_ids:
        db.query(AIInteraction).filter(
            AIInteraction.document_id.in_(document_ids)
        ).delete(synchronize_session=False)

    db.delete(project)
    db.commit()
    
    background_tasks.add_task(
        fulltext_search_service.remove_project,
        project_id
    )
    
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

def _index_document_async(document_id: int, document_title: str, project_id: int, content: any, project_title: str = ""):
    try:
        fulltext_search_service.index_document(
            document_id=document_id,
            document_title=document_title,
            project_id=project_id,
            content=content,
            metadata={"project_title": project_title}
        )
    except Exception as e:
        print(f"[SearchIndex] 索引文档失败: {e}")


@router.post("/projects/{project_id}/documents", response_model=DocumentResponse)
def create_document(
    project_id: int,
    document: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建新文档"""
    project = check_project_owner(db, project_id, current_user["id"])
    
    db_document = Document(**document.model_dump(), project_id=project_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    if db_document.content:
        background_tasks.add_task(
            _index_document_async,
            db_document.id,
            db_document.title,
            project_id,
            db_document.content,
            project.title
        )
    
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    project = check_project_owner(db, document.project_id, current_user["id"])
    
    for field, value in document_update.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    if document.content:
        background_tasks.add_task(
            _index_document_async,
            document.id,
            document.title,
            document.project_id,
            document.content,
            project.title
        )
    
    return document

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    check_project_owner(db, document.project_id, current_user["id"])
    
    doc_id = document.id
    
    db.delete(document)
    db.commit()
    
    background_tasks.add_task(
        fulltext_search_service.remove_document,
        doc_id
    )
    
    return {"message": "Document deleted"}


@router.post("/projects/{project_id}/documents/reorder")
def reorder_documents(
    project_id: int,
    document_ids: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    批量重排序文档
    document_ids: 按新顺序排列的文档 ID 列表
    """
    check_project_owner(db, project_id, current_user["id"])
    
    # 验证所有文档都属于该项目
    documents = db.query(Document).filter(
        Document.id.in_(document_ids),
        Document.project_id == project_id
    ).all()
    
    if len(documents) != len(document_ids):
        raise HTTPException(status_code=400, detail="Invalid document IDs")
    
    # 更新 order_index
    doc_map = {doc.id: doc for doc in documents}
    for index, doc_id in enumerate(document_ids):
        if doc_id in doc_map:
            doc_map[doc_id].order_index = index
    
    db.commit()
    
    # 返回更新后的文档列表
    updated_docs = db.query(Document).filter(
        Document.project_id == project_id
    ).order_by(Document.order_index.asc(), Document.id.asc()).all()
    
    return updated_docs

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
