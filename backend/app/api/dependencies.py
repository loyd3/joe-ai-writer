"""
FastAPI 依赖注入：LLM、缓存、文档/项目服务
"""
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.services.llm_service import llm_service as _llm_singleton
from app.services.cache_service import CacheService
from app.services.document_service import DocumentService
from app.services.project_service import ProjectService


def get_llm_service():
    """统一 LLM 服务（单例）"""
    return _llm_singleton


def get_cache_service():
    """内存缓存（单例）"""
    return CacheService()


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)
