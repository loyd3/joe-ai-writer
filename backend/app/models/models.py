"""
墨心 · 数据库 ORM 模型

==============================================================================
总览（表与职责）
------------------------------------------------------------------------------
核心创作域
  users                 账号、主题偏好、头像
  projects              作品项目（归属用户）
  documents             文档树（块编辑器 JSON 正文；可父子嵌套）
  ai_memories           项目设定 1:1（大纲/故事线/角色/世界观/文风文本等）
  writing_style_agents  用户级文风智能体（结构化 config，写作时注入 prompt）
  ai_interactions       文档维度的 AI 调用历史（润色/对话等）

辅助 / 运营
  templates             可复用的项目模板设定快照
  document_versions     文档版本快照
  system_configs        全局键值配置（如默认 AI 供应商）
  saved_brainstorms     用户收藏的脑洞概念

长文生成子系统（与「文档块编辑」并行的一条线）
  articles              长篇文章任务主表
  article_chapters      长文生成出的章节正文
  article_outlines      长文大纲多版本

关系简图
  User 1──* Project 1──* Document (*──1 parent Document)
                │      └──* AIInteraction
                ├── 1 AIMemory
                ├── * WritingStyleAgent (归属 User，跨项目复用)
                └── * Article 1──* ArticleChapter / ArticleOutline
  User 1──* SavedBrainstorm / Template / DocumentVersion(created_by)

约定
  - JSON 列存结构化数据；读写经 memory_normalize 等做兼容
  - 删除用户/项目多带 ON DELETE CASCADE（见 init.sql / FK）
  - 部分表仅由 Base.metadata.create_all 创建，init.sql 未全覆盖
==============================================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


# ---------------------------------------------------------------------------
# 账号与偏好
# ---------------------------------------------------------------------------

class User(Base):
    """用户账号：登录凭据 + UI 主题/头像。"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)  # 登录邮箱，唯一
    username = Column(String(255), unique=True, index=True)  # 显示名/登录名，唯一
    hashed_password = Column(String(255))  # 密码哈希，不明文存储
    is_active = Column(Boolean, default=True)  # False 时禁止登录
    created_at = Column(DateTime, default=datetime.utcnow)
    # 主题：preset 为 coffee | teal | indigo | custom；custom 时用 theme_custom_color
    theme_preset = Column(String(32), nullable=True)
    theme_custom_color = Column(String(32), nullable=True)  # 如 #3E4BC4
    avatar_url = Column(String(512), nullable=True)  # 头像 URL 或静态路径

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    writing_style_agents = relationship(
        "WritingStyleAgent", back_populates="owner", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 项目 / 文档 / 项目设定
# ---------------------------------------------------------------------------

class Project(Base):
    """创作项目：文档与设定的容器，归属单一用户。"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)  # 项目标题
    description = Column(Text, nullable=True)  # 简介
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 所有者
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    # 每项目至多一条项目设定（uselist=False）
    ai_memory = relationship("AIMemory", back_populates="project", uselist=False, cascade="all, delete-orphan")


class Document(Base):
    """
    文档：块编辑器正文。
    content 为 Block 数组 JSON，元素形如
      { id, type: paragraph|heading|..., content: str, props?: {} }
    parent_id 非空时为子文档（树/归档夹）；order_index 控制同级排序。
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))  # 文档标题
    content = Column(JSON, default=list)  # 块列表，见类 docstring
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # 父文档；根为 NULL
    order_index = Column(Integer, default=0)  # 同级排序，越小越靠前
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
    children = relationship("Document")  # 子文档；自引用


class AIMemory(Base):
    """
    项目设定（AI 记忆）— 与 Project 1:1。
    写入「项目设定」页；AI 写作经 build_memory_context 注入 prompt。
    writing_style 为兼容旧字段的自由文本；结构化文风以 writing_style_agents 为准。
    """
    __tablename__ = "ai_memories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True, nullable=False)

    # --- 结构化设定（JSON 形状见各字段注释；读写走 memory_normalize）---
    outline = Column(JSON, default=list)  # [{ "title", "description"? }, ...]
    storyline = Column(JSON, nullable=True)  # { "summary", "stages": [{ "title", "summary" }] }；旧数据可能是纯字符串
    characters = Column(JSON, default=list)  # [{ name, role, description, personality, background, goals, ... }]
    world_building = Column(JSON, default=dict)  # { "categories": [{ "name", "items": [{ "title", "content" }] }] }
    writing_style = Column(Text, nullable=True)  # 旧版自由文风；默认可由默认智能体同步回写
    key_points = Column(JSON, default=list)  # [{ "title", "summary" }, ...]；旧数据可能是字符串列表
    notes = Column(Text, nullable=True)  # 其它约束/备忘

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="ai_memory")


class WritingStyleAgent(Base):
    """
    用户级（系统级）文风智能体，跨项目复用。
    config 典型键：tone, pov, pace, sentence, diction, dialogue_ratio,
    detail_level, taboo[], custom_text, samples[]。
    is_default=True 的一条为写作未指定 style_agent_id 时的用户默认。
    source: preset | manual | extract
    """
    __tablename__ = "writing_style_agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # 展示名，如「冷硬极简」
    description = Column(Text, nullable=True)  # 一句话定位
    preset_key = Column(String(64), nullable=True)  # 来自内置预设时的 key；手建则为 NULL
    config = Column(JSON, default=dict)  # 结构化文风参数，见类 docstring
    is_default = Column(Boolean, default=False)  # 用户默认文风
    source = Column(String(32), nullable=True, default="manual")  # preset|manual|extract
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="writing_style_agents")


# ---------------------------------------------------------------------------
# AI 交互 / 模板 / 版本 / 系统配置
# ---------------------------------------------------------------------------

class AIInteraction(Base):
    """
    文档级 AI 交互流水（assist/chat/batch 等落库审计）。
    与 init.sql 中 ai_interactions 对应；interaction_type 如 guide/revise/polish/chat/batch_generate。
    """
    __tablename__ = "ai_interactions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    interaction_type = Column(String(64))  # 操作类型，见类 docstring
    user_input = Column(Text)  # 用户指令或选中原文摘要
    ai_response = Column(Text)  # 模型输出全文
    context_used = Column(JSON, default=dict)  # 如 { memory_used, humanized, ... }
    created_at = Column(DateTime, default=datetime.utcnow)


class Template(Base):
    """项目模板：可复用的设定快照，用于「从模板创建」类流程。"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), default="novel")  # novel | blog | work 等
    icon = Column(String(32), default="📝")
    outline = Column(JSON, default=list)  # 同 AIMemory.outline 形状
    storyline = Column(Text, nullable=True)  # 模板侧故事线（历史为 Text；记忆侧已迁 JSON）
    characters = Column(JSON, default=list)
    world_building = Column(JSON, default=dict)
    writing_style = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)  # 系统预置 vs 用户自建
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentVersion(Base):
    """文档版本快照：某次保存/回滚点的 title+content 副本。"""
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    title = Column(String(500), nullable=False)  # 该版本标题
    content = Column(JSON, default=list)  # 该版本块内容
    version_number = Column(Integer, nullable=False)  # 单调递增版本号
    change_summary = Column(Text, nullable=True)  # 变更说明（可选）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document")


class SystemConfig(Base):
    """系统级键值配置（AI 供应商、默认模型等）；value 多为 JSON 字符串。"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(255), unique=True, nullable=False, index=True)  # 如 ai_provider
    config_value = Column(Text, nullable=True)  # 常为 '{"value":"..."}'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# 长篇文章生成子系统（articles 线，独立于 documents 块编辑）
# ---------------------------------------------------------------------------

class Article(Base):
    """长文生成任务主表：按主题/目标字数规划并生成多章。"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(500), nullable=True)
    topic = Column(Text, nullable=False)  # 写作主题/命题
    target_words = Column(Integer, nullable=False)  # 目标总字数
    style = Column(String(100), default="专业")  # 文风标签（长文线自用，非 writing_style_agents）
    requirements = Column(Text, nullable=True)  # 额外要求
    outline = Column(JSON, nullable=True)  # 当前采用的大纲结构
    status = Column(String(50), default="pending")  # pending|outlined|generating|completed|failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # 完成时间

    project = relationship("Project")
    chapters = relationship("ArticleChapter", back_populates="article", cascade="all, delete-orphan")


class ArticleChapter(Base):
    """长文任务下的单章正文（纯文本 content，非块编辑 JSON）。"""
    __tablename__ = "article_chapters"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)  # 从 0 或 1 起的章节序号
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # 章节全文
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    article = relationship("Article", back_populates="chapters")


class ArticleOutline(Base):
    """长文大纲版本：同一 article 可存多版，is_active 标记当前启用。"""
    __tablename__ = "article_outlines"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    version = Column(Integer, default=1)  # 版本号
    outline_data = Column(JSON, nullable=False)  # 大纲 JSON 本体
    is_active = Column(Boolean, default=True)  # 是否当前生效
    created_at = Column(DateTime, default=datetime.utcnow)

    article = relationship("Article")


# ---------------------------------------------------------------------------
# 脑洞收藏
# ---------------------------------------------------------------------------

class SavedBrainstorm(Base):
    """用户收藏的脑洞概念，供脑洞写作页再次选用。"""
    __tablename__ = "saved_brainstorms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)  # 短标题
    category = Column(String(64), default="自定义")  # 分类标签
    concept = Column(Text, nullable=False)  # 脑洞正文/梗概
    source = Column(String(32), default="manual")  # manual | trending | random | hot
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
