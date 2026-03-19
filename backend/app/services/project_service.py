"""
项目服务占位（自动写作等模块依赖注入；可按需扩展）
"""
from sqlalchemy.orm import Session


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
