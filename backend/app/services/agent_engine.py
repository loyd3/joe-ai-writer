"""
智能体编排引擎（域无关部分）：认领、租约、心跳与围栏。

claim_run / execute_run 以 session_factory（sessionmaker）为入参，
模型可注入，便于测试与独立 worker 进程复用。域相关的工具白名单与
应用语义见 project_agent_service / project_agent_tools。
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker

from app.models.project_agent import AgentRun

LEASE_SECONDS = 120  # 租约时长：工作器须周期续租，过期可被接管（崩溃恢复）


@dataclass
class RunClaim:
    """一次认领：run_id + 持有者 token。owner 不同即视为不同 claim。"""

    run_id: str
    owner: str


def claim_run(session_factory: sessionmaker) -> Optional[RunClaim]:
    """
    认领一个待执行/租约过期的 run，置为 running 并发放租约。

    认领条件：status 为 queued，或 running 但租约已过期（前者用于崩溃恢复）。
    无可认领时返回 None。同一次认领在短事务内完成，避免竞态。
    """
    with session_factory() as db:
        now = datetime.utcnow()
        run = (
            db.query(AgentRun)
            .filter(
                or_(AgentRun.status == "queued", AgentRun.status == "running"),
                or_(AgentRun.lease_until.is_(None), AgentRun.lease_until < now),
            )
            .order_by(AgentRun.created_at.asc())
            .first()
        )
        if run is None:
            return None
        claim = RunClaim(run_id=run.id, owner=str(uuid.uuid4()))
        run.status = "running"
        run.lease_owner = claim.owner
        run.lease_until = now + timedelta(seconds=LEASE_SECONDS)
        run.heartbeat_at = now
        db.commit()
        return claim


def renew_lease(db, run: AgentRun, owner: str) -> bool:
    """执行过程中续租；run 已被接管或状态变化时返回 False（调用方应停止执行）。"""
    now = datetime.utcnow()
    if run.status != "running" or run.lease_owner != owner:
        return False
    if run.lease_until is None or run.lease_until < now - timedelta(seconds=LEASE_SECONDS * 10):
        # 租约丢失过久，放弃执行，避免与接管者并发写同一 run
        return False
    run.lease_until = now + timedelta(seconds=LEASE_SECONDS)
    run.heartbeat_at = now
    return True


def release_lease(run: AgentRun):
    run.lease_owner = None
    run.lease_until = None
    run.heartbeat_at = None
