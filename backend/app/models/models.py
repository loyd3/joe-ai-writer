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

    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project")
    ai_memory = relationship("AIMemory", back_populates="project", uselist=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(JSON, default=list)  # Block-based content
    project_id = Column(Integer, ForeignKey("projects.id"))
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
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True)

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


class Event(Base):
    """事件设定 - 管理故事中的关键事件"""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    # 事件基本信息
    name = Column(String, nullable=False)  # 事件名称
    description = Column(Text, nullable=True)  # 事件描述
    chapter = Column(String, nullable=True)  # 所属章节

    # 时间信息
    timeline_position = Column(String, nullable=True)  # 时间线位置（如：第三章、倒叙等）
    order_index = Column(Integer, default=0)  # 排序索引

    # 参与角色
    involved_characters = Column(JSON, default=list)  # 参与的角色ID列表

    # 事件属性
    importance = Column(String, default="normal")  # 重要程度: minor, normal, major, critical
    event_type = Column(
        String, default="plot"
    )  # 事件类型: plot, conflict, revelation, climax, ending

    # 状态
    is_completed = Column(Boolean, default=False)  # 是否已完成写作

    # 内容
    content_notes = Column(Text, nullable=True)  # 内容备注/草稿

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")


class AIInteraction(Base):
    """AI 交互历史记录"""

    __tablename__ = "ai_interactions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    interaction_type = Column(String)  # 'guide', 'revise', 'polish', 'chat'
    user_input = Column(Text)
    ai_response = Column(Text)
    context_used = Column(JSON, default=dict)  # 使用的上下文信息
    created_at = Column(DateTime, default=datetime.utcnow)
