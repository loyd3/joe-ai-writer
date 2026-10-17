"""独立智能体工作器：循环认领并执行排队任务。

用法（Docker 可作为独立容器运行，与 API 进程解耦）：
    cd backend && python scripts/agent_worker.py

API 进程内已有 in-process worker（main.py 启动时拉起），本脚本用于
希望把智能体执行拆到独立进程/容器的部署方式。执行语义与引擎
（claim 租约 + 围栏）完全一致，重复执行不会二次发布。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_database  # noqa: E402
from app.services.project_agent_service import agent_worker_loop  # noqa: E402


def main():
    init_database()
    print("[AgentWorker] 独立工作器已启动，等待认领任务…")
    try:
        asyncio.run(agent_worker_loop(poll_seconds=2.0))
    except KeyboardInterrupt:
        print("[AgentWorker] 已退出")


if __name__ == "__main__":
    main()
