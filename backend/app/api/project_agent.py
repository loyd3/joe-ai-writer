"""项目智能体 API：run 的创建、查询、确认发布与撤销。

权限：仅项目属主可操作；越权一律 403/404。创建仅入队，由后台 worker 认领执行
（见 project_agent_service.agent_worker_loop 与 scripts/agent_worker.py）。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Project
from app.schemas.schemas import AgentRunCreate
from app.services import project_agent_service
from app.api.auth import get_current_user

router = APIRouter(prefix="/api", tags=["project-agent"])


def _check_project_owner(db: Session, project_id: int, user_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return project


@router.post("/projects/{project_id}/agent/runs")
def create_agent_run(
    project_id: int,
    payload: AgentRunCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """提交一条智能体指令，返回 queued 状态的 run（由 worker 异步执行）。"""
    _check_project_owner(db, project_id, current_user["id"])
    focus = payload.focus.model_dump(exclude_none=True) if payload.focus else None
    run = project_agent_service.create_run(
        db,
        current_user["id"],
        project_id,
        payload.instruction,
        payload.conversation_id,
        idempotency_key=payload.idempotency_key,
        focus=focus,
    )
    return project_agent_service.run_to_dict(run)


@router.get("/projects/{project_id}/agent/runs")
def list_agent_runs(
    project_id: int,
    conversation_id: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出项目的智能体运行（新→旧）；可按会话过滤。"""
    _check_project_owner(db, project_id, current_user["id"])
    from app.models.project_agent import AgentRun

    query = db.query(AgentRun).filter(
        AgentRun.project_id == project_id, AgentRun.user_id == current_user["id"]
    )
    if conversation_id:
        query = query.filter(AgentRun.conversation_id == conversation_id)
    runs = query.order_by(AgentRun.created_at.desc()).all()
    return [project_agent_service.run_to_dict(run) for run in runs]


@router.get("/projects/{project_id}/agent/runs/{run_id}")
def get_agent_run(
    project_id: int,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    run = project_agent_service.get_run(db, current_user["id"], project_id, run_id)
    return project_agent_service.run_to_dict(run)


@router.post("/projects/{project_id}/agent/runs/{run_id}/{verb}")
def transition_agent_run(
    project_id: int,
    run_id: str,
    verb: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """verb ∈ apply | revert | resume | cancel。apply/revert 带版本冲突校验。"""
    _check_project_owner(db, project_id, current_user["id"])
    run = project_agent_service.transition(db, current_user["id"], project_id, run_id, verb)
    return project_agent_service.run_to_dict(run)


# ---------------------------------------------------------------------------
# 系统级会话（无项目）：可先对话 / 专项写作，再 create_project 落盘
# ---------------------------------------------------------------------------

@router.post("/agent/runs")
def create_system_agent_run(
    payload: AgentRunCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """无项目智能体：提交指令，由 worker 执行；需要落库时工具内 create_project。"""
    run = project_agent_service.create_system_run(
        db,
        current_user["id"],
        payload.instruction,
        payload.conversation_id,
        idempotency_key=payload.idempotency_key,
    )
    return project_agent_service.run_to_dict(run)


@router.get("/agent/runs")
def list_system_agent_runs(
    conversation_id: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    runs = project_agent_service.list_system_runs(
        db, current_user["id"], conversation_id=conversation_id
    )
    return [project_agent_service.run_to_dict(run) for run in runs]


@router.get("/agent/runs/{run_id}")
def get_system_agent_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    run = project_agent_service.get_system_run(db, current_user["id"], run_id)
    return project_agent_service.run_to_dict(run)


@router.post("/agent/runs/{run_id}/{verb}")
def transition_system_agent_run(
    run_id: str,
    verb: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    run = project_agent_service.transition_system(db, current_user["id"], run_id, verb)
    return project_agent_service.run_to_dict(run)
