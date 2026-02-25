from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.api.auth import get_current_user
from app.api.projects import check_document_access
from app.models.models import Document, DocumentVersion
from app.schemas.schemas import DocumentVersionCreate, DocumentVersionResponse

router = APIRouter(prefix="/api/versions", tags=["versions"])

@router.get("/document/{document_id}", response_model=List[DocumentVersionResponse])
def list_versions(
    document_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取文档版本历史"""
    # 检查权限
    check_document_access(db, document_id, current_user["id"])
    
    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).limit(limit).all()
    
    return versions

@router.post("/document/{document_id}")
def create_version(
    document_id: int,
    data: DocumentVersionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """手动创建版本快照"""
    document = check_document_access(db, document_id, current_user["id"])
    
    # 获取当前最新版本号
    latest = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    version_number = (latest.version_number + 1) if latest else 1
    
    version = DocumentVersion(
        document_id=document_id,
        title=data.title,
        content=data.content,
        version_number=version_number,
        change_summary=data.change_summary,
        created_by=current_user["id"]
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    
    return {
        "message": "版本创建成功",
        "version_id": version.id,
        "version_number": version.version_number
    }

@router.get("/document/{document_id}/auto-save")
def auto_save_version(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """自动保存版本（用于定时自动保存）"""
    document = check_document_access(db, document_id, current_user["id"])
    
    # 获取最近的一个版本
    latest = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.created_at.desc()).first()
    
    # 如果最近版本是自动保存且时间很近（5分钟内），则更新它
    if latest and not latest.change_summary:
        time_diff = (datetime.utcnow() - latest.created_at).total_seconds()
        if time_diff < 300:  # 5分钟内
            latest.title = document.title
            latest.content = document.content
            latest.created_at = datetime.utcnow()
            db.commit()
            return {
                "message": "自动保存更新成功",
                "version_id": latest.id,
                "version_number": latest.version_number
            }
    
    # 否则创建新版本
    version_number = (latest.version_number + 1) if latest else 1
    
    version = DocumentVersion(
        document_id=document_id,
        title=document.title,
        content=document.content,
        version_number=version_number,
        change_summary=None,  # 自动保存不填写变更说明
        created_by=current_user["id"]
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    
    return {
        "message": "自动保存成功",
        "version_id": version.id,
        "version_number": version.version_number
    }

@router.get("/{version_id}")
def get_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取特定版本详情"""
    version = db.query(DocumentVersion).filter(
        DocumentVersion.id == version_id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 检查权限
    check_document_access(db, version.document_id, current_user["id"])
    
    return {
        "id": version.id,
        "document_id": version.document_id,
        "title": version.title,
        "content": version.content,
        "version_number": version.version_number,
        "change_summary": version.change_summary,
        "created_at": version.created_at.isoformat()
    }

@router.post("/{version_id}/restore")
def restore_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """恢复到指定版本"""
    version = db.query(DocumentVersion).filter(
        DocumentVersion.id == version_id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 检查权限
    document = check_document_access(db, version.document_id, current_user["id"])
    
    # 先保存当前状态为新版本
    latest = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == version.document_id
    ).order_by(DocumentVersion.version_number.desc()).first()
    
    version_number = (latest.version_number + 1) if latest else 1
    
    backup = DocumentVersion(
        document_id=version.document_id,
        title=document.title,
        content=document.content,
        version_number=version_number,
        change_summary="恢复版本前的自动备份",
        created_by=current_user["id"]
    )
    db.add(backup)
    
    # 恢复文档到指定版本
    document.title = version.title
    document.content = version.content
    document.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "版本恢复成功",
        "restored_to": version.version_number,
        "backup_version": backup.version_number
    }

@router.delete("/{version_id}")
def delete_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除版本（保留最近10个版本）"""
    version = db.query(DocumentVersion).filter(
        DocumentVersion.id == version_id
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 检查权限
    check_document_access(db, version.document_id, current_user["id"])
    
    db.delete(version)
    db.commit()
    
    return {"message": "版本已删除"}

@router.get("/document/{document_id}/compare")
def compare_versions(
    document_id: int,
    v1: int,
    v2: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """对比两个版本"""
    # 检查权限
    check_document_access(db, document_id, current_user["id"])
    
    version1 = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == v1
    ).first()
    
    version2 = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == v2
    ).first()
    
    if not version1 or not version2:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 简单对比（返回内容差异）
    content1 = "\n".join([block.get("content", "") for block in version1.content])
    content2 = "\n".join([block.get("content", "") for block in version2.content])
    
    return {
        "version1": {
            "number": version1.version_number,
            "title": version1.title,
            "created_at": version1.created_at.isoformat()
        },
        "version2": {
            "number": version2.version_number,
            "title": version2.title,
            "created_at": version2.created_at.isoformat()
        },
        "title_changed": version1.title != version2.title,
        "content_length1": len(content1),
        "content_length2": len(content2),
        "diff_summary": f"版本{v1}共{len(content1)}字，版本{v2}共{len(content2)}字"
    }
