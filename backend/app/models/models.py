from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    ai_memory = relationship("AIMemory", back_populates="project", uselist=False, cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(JSON, default=list)  # Block-based content
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="documents")
    children = relationship("Document")

class AIMemory(Base):
    """AI 记忆系统 - 存储项目级别的上下文信息"""
    __tablename__ = "ai_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True, nullable=False)
    
    # 结构化记忆数据
    outline = Column(JSON, default=list)  # 文章大纲
    storyline = Column(Text, nullable=True)  # 故事线概述
    characters = Column(JSON, default=list)  # 角色设定列表
    world_building = Column(JSON, default=dict)  # 世界观设定
    writing_style = Column(Text, nullable=True)  # 写作风格偏好
    key_points = Column(JSON, default=list)  # 关键情节点
    notes = Column(Text, nullable=True)  # 其他备注
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="ai_memory")

class AIInteraction(Base):
    """AI 交互历史记录（与 database/init.sql 中 ai_interactions 表结构一致）"""
    __tablename__ = "ai_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    interaction_type = Column(String)  # 'guide', 'revise', 'polish', 'chat'
    user_input = Column(Text)
    ai_response = Column(Text)
    context_used = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

class Template(Base):
    """项目模板"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, default="novel")  # novel, blog, work
    icon = Column(String, default="📝")
    outline = Column(JSON, default=list)
    storyline = Column(Text, nullable=True)
    characters = Column(JSON, default=list)
    world_building = Column(JSON, default=dict)
    writing_style = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentVersion(Base):
    """文档版本历史"""
    __tablename__ = "document_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(JSON, default=list)
    version_number = Column(Integer, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document")
