"""
智能体运行（AgentRun）：项目智能体的持久化任务记录。

设计为域无关的通用 run 表：当前仅用于项目域（scope='project'），
后续系统级智能体（项目创建/管理等）可复用同一套引擎，使用 scope='system' 且 project_id 为空。
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


class AgentRun(Base):
    """一次智能体运行：指令、事件流、暂存的修改集（ChangeSet）与执行租约。"""

    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope = Column(String(20), nullable=False, default="project")  # project | system（预留）
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 会话：同一 conversation_id 的多个 run 构成一段连续对话（会话由 runs 派生，隐式持久化）
    conversation_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()), index=True)

    instruction = Column(Text, nullable=False)  # 用户指令
    status = Column(
        String(20),
        nullable=False,
        default="queued",
        index=True,
    )  # queued|running|proposed|completed|failed|cancelled|applied|reverted
    answer = Column(Text, nullable=True)  # finish 给出的总结答复
    error = Column(Text, nullable=True)

    changes = Column(JSON, default=list)  # 暂存修改集，见 project_agent_tools.change dict
    events = Column(JSON, default=list)  # [{sequence, type, message}]
    messages = Column(JSON, default=list)  # 对话记录 [{role: user|assistant, content, step}]

    model_config = Column("model_config", JSON, default=dict)  # 创建时的模型配置快照
    input_versions = Column(JSON, default=dict)  # 执行基线快照（文档/设定的 updated_at）

    idempotency_key = Column(String(64), nullable=True, unique=True)  # 幂等键：重复提交不二次建任务
    lease_owner = Column(String(36), nullable=True)  # 工作器租约持有者（uuid）
    lease_until = Column(DateTime, nullable=True)  # 租约到期时间；过期可被其他工作器接管
    heartbeat_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_runs_status_lease", "status", "lease_until"),
    )
