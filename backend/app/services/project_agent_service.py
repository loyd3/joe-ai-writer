"""
项目智能体服务：run 生命周期（创建/认领/执行/转换）与修改集的原子发布、逆向撤销。

约束（由 test_project_agent.py 锁定）：
- execute_run 以 claim 围栏执行：取消/租约过期/被接管/项目归属变更均不得继续；
- 模型只提出受控操作（工具白名单见 project_agent_tools），所有修改暂存于内存，
  用户确认（apply）后以短事务原子发布，任一版本冲突则整体拒绝（409）；
- 撤销是新的逆向修改集，不覆盖应用之后的人工修改。
"""
import asyncio
import inspect
import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.models import AIMemory, Document, DocumentVersion, Project, SystemConfig
from app.models.project_agent import AgentRun
from app.services.agent_engine import RunClaim, claim_run, release_lease, renew_lease
from app.services.project_agent_tools import (
    MEMORY_FIELDS,
    ProjectAgentContext,
    ToolViolation,
    _find_block,
    _norm,
    execute_tool,
)

MAX_STEPS = 32  # 单次运行最多工具调用数，防止失控循环
MAX_EVENTS = 500
MAX_CONSECUTIVE_TEXT_TURNS = 3  # 漏发工具动作可纠正，但不允许无限空转

SYSTEM_PROMPT = """你是「墨心」写作项目的项目智能体，以对话方式与用户协作。你能看到项目正文与设定，但只能提出受控操作，由用户在确认后才真正写入。

## 交互方式（重要）
- 像正常对话一样交流：每轮先用自然语言回复用户——说明你要做什么、进展如何、结果如何；需要澄清时要先提问。
- 需要操作工具时，在本轮回复末尾的 ```json 代码块中给出一个动作（仅此一个代码块）：
```json
{"tool": "工具名", "args": { ... }}
```
- 纯文字仅为进度说明，不会结束任务。说要读取、核查、拆分或扩写时，必须实际调用对应工具并继续执行，不要停在计划上。
- 需要用户澄清、无需操作的聊天或最终答复，也必须调用 finish(answer)，在 answer 中说明问题或结论。
- 用户看不到工具的原始返回，要用自己的话总结关键信息。

## 可用工具
- list_project()：列出项目内全部文档与可修改的设定字段。
- read_document(document_id, offset=0, limit=50)：分页读取文档正文块。被截断时 data.complete=false，须继续翻页直到 complete=true。
- read_memory()：读取全部项目设定。
- search_project(query, offset=0, limit=10)：对全部项目文档与设定做字面量检索，返回命中与覆盖声明。
- propose_document_patch(document_id, block_id, old_text, new_text, reason)：提出正文补丁（暂存，不直接写入）。old_text 必须在目标块中恰好出现一次，否则会被拒绝；同一处可多次补丁，会合并为一条修改。
- propose_memory_patch(field, before, after, reason)：提出设定补丁（暂存）。field 只能是 read_memory 返回的字段；before 必须与当前值一致。
- propose_create_document(title, text, reason)：提案新建一篇文档（暂存）。
- finish(answer)：完成本次任务，answer 为面向用户的总结。

## 规则
1. 必须先读取（read_document / read_memory）才能对对应目标提出补丁。
2. 修改正文前先 search_project 做全文核查（如改名要找出所有出现处），避免遗漏或误改同名内容。
3. 每次补丁尽量小而精确；指令涉及多处时逐处提出补丁。
4. 全部完成后调用 finish；没有提出任何修改也可以 finish。"""


def _extract_fenced_json(text: str) -> Optional[str]:
    """从模型输出中提取 ```json 代码块内容；没有代码块返回 None。"""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return match.group(1).strip() if match else None


def _parse_action_and_message(raw: Any):
    """
    解析模型输出 → (action, message)。

    兼容两种形态：
    - 纯 JSON 动作（历史/测试形态）：整段是 {"tool": ..., "args": ...}
    - 对话形态：自然语言 + 末尾 ```json 代码块动作
    返回 (None, message) 表示本轮只是闲聊/说明（say 轮）。
    代码块存在但 JSON 非法 → 抛 ToolViolation（视为模型输出错误）。
    """
    if not isinstance(raw, str):
        raise ToolViolation("模型输出必须是字符串")
    text = raw.strip()
    if not text:
        raise ToolViolation("模型输出为空")
    # 形态一：整段纯 JSON
    if text.startswith("{"):
        try:
            action = json.loads(text)
        except Exception:
            action = None
        if isinstance(action, dict):
            if not isinstance(action.get("tool"), str):
                raise ToolViolation("模型输出缺少 tool 字段")
            return action, None
    # 形态二：自然语言 + fenced 动作
    fenced = _extract_fenced_json(text)
    if fenced is not None:
        try:
            action = json.loads(fenced)
        except Exception as e:
            raise ToolViolation(f"动作代码块不是合法 JSON: {e}")
        if not isinstance(action, dict) or not isinstance(action.get("tool"), str):
            raise ToolViolation("动作代码块缺少 tool 字段")
        message = (text[: text.find("```")].strip() or None)
        return action, message
    if "```" in text:
        raise ToolViolation("动作代码块未闭合，回复被中止")
    # 形态三：纯自然语言（say 轮）
    return None, text


# ---------------------------------------------------------------------------
# 创建 / 查询
# ---------------------------------------------------------------------------

def _snapshot_model_config(db) -> Dict[str, Any]:
    """创建时快照当前模型配置（便于审计与复现）；失败时退回空 dict。"""
    try:
        config: Dict[str, Any] = {}
        for key in ("ai_provider", "ai_model", "ai_base_url"):
            row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if row and row.config_value:
                try:
                    config[key] = json.loads(row.config_value).get("value", row.config_value)
                except Exception:
                    config[key] = row.config_value
        return config
    except Exception:
        return {}


def create_run(
    db,
    user_id: int,
    project_id: int,
    instruction: str,
    conversation_id: Optional[str],
    idempotency_key: Optional[str] = None,
) -> AgentRun:
    """创建一次运行（queued）。幂等键重复时直接返回已存在的 run，不二次建任务。"""
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    if conversation_id:
        conversation = (
            db.query(AgentRun)
            .filter(
                AgentRun.conversation_id == conversation_id,
                AgentRun.project_id == project_id,
                AgentRun.user_id == user_id,
                AgentRun.scope == "project",
            )
            .first()
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    if idempotency_key:
        # The database key is globally unique; reject collisions outside this scope
        # rather than returning another project's run or leaking an integrity error.
        existing = db.query(AgentRun).filter(AgentRun.idempotency_key == idempotency_key).first()
        if existing is not None:
            if (existing.user_id != user_id or existing.project_id != project_id
                    or existing.scope != "project"
                    or (conversation_id and existing.conversation_id != conversation_id)):
                raise HTTPException(status_code=409, detail="Idempotency key scope conflict")
            return existing
    run = AgentRun(
        project_id=project_id,
        user_id=user_id,
        instruction=instruction,
        conversation_id=conversation_id or str(uuid.uuid4()),
        status="queued",
        model_config=_snapshot_model_config(db),
        idempotency_key=idempotency_key,
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.query(AgentRun).filter(AgentRun.idempotency_key == idempotency_key).first()
        if existing is None:
            raise
        # Reuse the same validation path after a concurrent insert won the key.
        return create_run(db, user_id, project_id, instruction, conversation_id, idempotency_key)
    db.refresh(run)
    return run


def get_run(db, user_id: int, project_id: int, run_id: str) -> AgentRun:
    run = db.get(AgentRun, run_id)
    project = db.get(Project, project_id)
    if (run is None or run.project_id != project_id or run.user_id != user_id
            or run.scope != "project" or project is None or project.owner_id != user_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _looks_like_action_envelope(text: str) -> bool:
    """Recognize JSON/action prefixes without rejecting ordinary bracket prose."""
    stripped = text.lstrip()
    if stripped.startswith("{"):
        remainder = stripped[1:].lstrip()
        return not remainder or remainder.startswith(('"', "'", "}"))
    if stripped.startswith("["):
        remainder = stripped[1:].lstrip()
        return not remainder or remainder.startswith(("{", "[", '"', "'", "]"))
    return False


def _safe_assistant_content(content: Any, streaming: bool = False) -> str:
    """Only expose prose, never the model's action envelope (even mid-stream)."""
    if not isinstance(content, str):
        return ""
    text = content.strip()
    if "UNTRUSTED_OBSERVATION" in text or _looks_like_action_envelope(text):
        return ""
    text = text.split("```", 1)[0]
    if streaming:
        # A fence can span deltas: withhold its first one or two backticks too.
        text = text.rstrip().rstrip("`")
    return text.strip()


def _public_messages(run: AgentRun) -> List[dict]:
    result = []
    for message in run.messages or []:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            continue
        streaming = bool(message.get("streaming", False))
        content = message.get("content", "")
        if message["role"] == "assistant":
            content = _safe_assistant_content(content, streaming)
        if not isinstance(content, str) or not content.strip():
            continue
        result.append({"role": message["role"], "content": content,
                       "step": message.get("step", 0), "streaming": streaming})
    return result


def run_to_dict(run: AgentRun) -> Dict[str, Any]:
    """与前端 project-agent.ts 的 ProjectAgentRun 对齐的序列化。"""
    return {
        "id": run.id,
        "conversation_id": run.conversation_id,
        "instruction": run.instruction,
        "status": run.status,
        "answer": _safe_assistant_content(run.answer),
        "error": run.error,
        "events": [
            {**event, "message": _safe_assistant_content(event.get("message"))}
            if event.get("type") == "finish" else dict(event)
            for event in run.events or [] if isinstance(event, dict)
        ],
        "messages": _public_messages(run),
        "changes": run.changes or [],
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


# ---------------------------------------------------------------------------
# 模型调用（可注入；生产默认走 ai_client）
# ---------------------------------------------------------------------------

async def default_model(messages, **kwargs) -> str:
    """生产模型：流式输出，token 经 on_delta 回调增量持久化（对话式体验）。"""
    from app.core.ai_client import ai_client

    on_delta = kwargs.get("on_delta")
    chunks: List[str] = []
    async for chunk in ai_client.stream_completion(
        messages,
        temperature=kwargs.get("temperature"),
        max_tokens=kwargs.get("max_tokens"),
    ):
        if not chunk:
            continue
        chunks.append(chunk)
        if on_delta is not None:
            try:
                on_delta(chunk)
            except Exception:
                pass  # 增量落盘失败不影响生成本身
    text = "".join(chunks).strip()
    if not text or text.startswith("[错误]") or text.startswith("[配置错误]"):
        raise RuntimeError(text or "[错误] 模型未返回内容")
    return text


async def _call_model(model, messages, **kwargs) -> str:
    result = model(messages, temperature=0.5, max_tokens=4096, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


# ---------------------------------------------------------------------------
# 执行循环
# ---------------------------------------------------------------------------

def _append_event(run: AgentRun, type_: str, message: str):
    events = list(run.events or [])
    events.append({"sequence": len(events) + 1, "type": type_, "message": message[:500]})
    run.events = events[-MAX_EVENTS:]


def _dump_changes(ctx: ProjectAgentContext) -> List[dict]:
    return json.loads(json.dumps(ctx.changes, ensure_ascii=False, default=str))


def _collect_input_versions(db, project_id: int) -> Dict[str, Any]:
    versions: Dict[str, Any] = {}
    for row in db.query(Document.id, Document.updated_at).filter(Document.project_id == project_id):
        versions[f"document:{row.id}"] = row.updated_at.isoformat() if row.updated_at else None
    memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
    versions["memory"] = memory.updated_at.isoformat() if memory and memory.updated_at else None
    return versions


MAX_CONTEXT_MESSAGES = 24  # 继承同会话历史消息的上限
MAX_CONTEXT_CHARS = 24000  # 继承上下文的字符上限
STREAM_FLUSH_INTERVAL = 1.2  # 流式回复增量落盘的最小间隔（秒）


def _load_conversation_messages(db, run: AgentRun) -> List[Dict[str, str]]:
    """同一会话中、本次 run 之前的历史消息，供模型像连续对话一样延续上下文。"""
    prior = (
        db.query(AgentRun)
        .filter(
            AgentRun.conversation_id == run.conversation_id,
            AgentRun.project_id == run.project_id,
            AgentRun.user_id == run.user_id,
            AgentRun.scope == "project",
            AgentRun.id != run.id,
            AgentRun.created_at <= run.created_at,
            AgentRun.status.in_(("proposed", "completed", "applied", "reverted", "failed", "cancelled")),
        )
        .order_by(AgentRun.created_at.asc(), AgentRun.id.asc())
        .all()
    )
    history: List[Dict[str, str]] = []
    for prev in prior:
        history.append({"role": "user", "content": prev.instruction})
        status_note = {
            "proposed": "仅为提案，未应用；不能作为项目已修改的事实。",
            "applied": "修改已应用；当前内容仍需重新读取核实。",
            "reverted": "修改已撤销，不能作为当前项目事实。",
            "completed": "对话已完成，没有应用任何修改。",
        }.get(prev.status, "未成功完成，不继承其中的执行结论或修改声明。")
        status_message = {"role": "system", "content": f"历史运行状态：{prev.status}。{status_note}"}
        history.append(status_message)
        if prev.status not in ("proposed", "applied", "reverted", "completed"):
            continue
        turn_contents = set()
        for m in _public_messages(prev):
            if m["role"] != "assistant" or m["streaming"]:
                continue
            if m["content"] not in turn_contents:
                history.append(status_message)
                history.append({"role": "assistant", "content": m["content"]})
                turn_contents.add(m["content"])
        answer = _safe_assistant_content(prev.answer)
        if answer and answer not in turn_contents:
            history.append(status_message)
            history.append({"role": "assistant", "content": answer})
    # 只保留尾部，控制上下文长度
    trimmed: List[Dict[str, str]] = []
    total = 0
    index = len(history) - 1
    while index >= 0:
        # Keep each assistant claim and its authoritative run-status warning
        # together, including at the size boundary.
        unit = history[index - 1:index + 1] if history[index]["role"] == "assistant" else [history[index]]
        size = sum(len(m["content"]) for m in unit)
        if total + size > MAX_CONTEXT_CHARS or len(trimmed) + len(unit) > MAX_CONTEXT_MESSAGES:
            break
        total += size
        trimmed.extend(reversed(unit))
        index -= len(unit)
    return list(reversed(trimmed))


def _build_chat_messages(
    instruction: str, history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    return (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": instruction}]
    )


async def execute_run(session_factory: sessionmaker, claim: Optional[RunClaim], model=None) -> None:
    """按认领执行一个 run。围栏：状态/租约/归属任一变化即静默退出或判失败。"""
    if claim is None:
        return
    model = model or default_model

    # ---- 围栏检查 + 初始化（短事务） ----
    with session_factory() as db:
        run = db.get(AgentRun, claim.run_id)
        if run is None:
            return
        now = datetime.utcnow()
        if (
            run.status != "running"
            or run.lease_owner != claim.owner
            or run.lease_until is None
            or run.lease_until < now
        ):
            return  # 已取消 / 租约过期 / 已被接管
        project = db.get(Project, run.project_id) if run.project_id else None
        if project is None or project.owner_id != run.user_id:
            run.status = "failed"
            run.error = "项目归属已变化，执行被中止"
            release_lease(run)
            _append_event(run, "error", run.error)
            db.commit()
            return
        run_id = run.id
        project_id = run.project_id
        user_id = run.user_id
        instruction = run.instruction
        run.input_versions = _collect_input_versions(db, project_id)
        run.changes = []
        run.events = []
        history = _load_conversation_messages(db, run)
        transcript: List[dict] = [{"role": "user", "content": instruction, "step": 0}]
        run.messages = json.loads(json.dumps(transcript, ensure_ascii=False))
        _append_event(run, "start", f"开始执行：{instruction[:100]}")
        db.commit()

    ctx = ProjectAgentContext(project_id=project_id, user_id=user_id)
    messages = _build_chat_messages(instruction, history)

    def fail(message: str, clear_changes: bool):
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if current is None or current.lease_owner != claim.owner:
                return
            current.status = "failed"
            current.error = message[:1000]
            if clear_changes:
                current.changes = []
            release_lease(current)
            _append_event(current, "error", message[:500])
            db.commit()

    def persist_progress(type_: str, message: str) -> bool:
        """落盘事件/修改集并续租；run 已被取消或接管时返回 False。"""
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if (current is None or current.lease_until is None
                    or current.lease_until < datetime.utcnow()
                    or not renew_lease(db, current, claim.owner)):
                return False
            current.changes = _dump_changes(ctx)
            _append_event(current, type_, message)
            db.commit()
            return True

    def persist_transcript() -> bool:
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if (current is None or current.lease_until is None
                    or current.lease_until < datetime.utcnow()
                    or not renew_lease(db, current, claim.owner)):
                return False
            current.messages = json.loads(json.dumps(transcript, ensure_ascii=False, default=str))
            db.commit()
            return True

    def upsert_assistant(step: int, content: str, streaming: bool = False):
        """同一步的 assistant 消息去重更新（流式增量与最终文本共用一条）。"""
        for m in transcript:
            if m.get("role") == "assistant" and m.get("step") == step:
                m["content"] = content
                m["streaming"] = streaming
                return
        transcript.append({"role": "assistant", "content": content, "step": step, "streaming": streaming})

    def finalize_turn(step: int, answer: str, said: Optional[str] = None):
        """Complete explicit finish-tool turns through a fenced write."""
        upsert_assistant(step, _safe_assistant_content(said or answer), streaming=False)
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            now = datetime.utcnow()
            if (current is None or current.status != "running"
                    or current.lease_owner != claim.owner or current.lease_until is None
                    or current.lease_until < now):
                return
            project = db.get(Project, project_id)
            if project is None or project.owner_id != user_id:
                current.status = "failed"
                current.error = "项目归属已变化，执行被中止"
                current.changes = []
                _append_event(current, "error", current.error)
            else:
                current.messages = json.loads(json.dumps(transcript, ensure_ascii=False))
                current.answer = answer
                current.changes = _dump_changes(ctx)
                current.status = "proposed" if ctx.changes else "completed"
                _append_event(current, "finish", _safe_assistant_content(answer) or "完成")
            release_lease(current)
            db.commit()

    # ---- 工具循环（仅显式 finish 可成功结束，纯文字继续推进） ----
    consecutive_text_turns = 0
    for step in range(1, MAX_STEPS + 1):
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if current is None or current.status != "running" or current.lease_owner != claim.owner:
                return  # 执行中被取消/接管

        stream_state = {"chunks": [], "last_flush": 0.0}

        def _flush_stream(_step: int, _state: dict, final: bool) -> bool:
            content = _safe_assistant_content("".join(_state["chunks"]), streaming=not final)
            if not content and not final:
                return True
            upsert_assistant(_step, content, streaming=not final)
            return persist_transcript()

        def on_delta(chunk: str, _step: int = step, _state: dict = stream_state):
            _state["chunks"].append(chunk)
            if time.monotonic() - _state["last_flush"] >= STREAM_FLUSH_INTERVAL:
                if _flush_stream(_step, _state, final=False):
                    _state["last_flush"] = time.monotonic()

        try:
            raw = await _call_model(model, messages, on_delta=on_delta)
            action, said = _parse_action_and_message(raw)
        except ToolViolation as e:
            fail(str(e), clear_changes=True)
            return
        except Exception as e:
            fail(f"模型调用失败: {e}", clear_changes=False)
            return

        if action is None:
            upsert_assistant(step, _safe_assistant_content(said), streaming=False)
            if not persist_transcript():
                return
            consecutive_text_turns += 1
            if consecutive_text_turns >= MAX_CONSECUTIVE_TEXT_TURNS:
                fail("模型连续未提供工具动作，任务未完成；请重试或检查模型工具指令遵循能力", clear_changes=False)
                return
            messages.append({"role": "assistant", "content": said or ""})
            messages.append({
                "role": "system",
                "content": "刚才仅为文字说明，任务尚未结束。请依据用户目标继续执行，"
                           "在回复末尾提供一个 JSON 工具动作；需要阅读就调用 read_document，"
                           "需要修改就实际提出提案。只有任务确已完成或必须等待用户澄清时，"
                           "才调用 finish，并给出结果或具体问题。",
            })
            continue

        consecutive_text_turns = 0
        # 本轮自然语言回复定稿（替换流式期间的增量文本）
        if said:
            upsert_assistant(step, _safe_assistant_content(said), streaming=False)
            if not persist_transcript():
                return

        tool, args = action["tool"], action.get("args", {})
        if not isinstance(args, dict):
            fail("工具参数必须是对象", clear_changes=True)
            return
        try:
            with session_factory() as db:
                data = execute_tool(ctx, db, tool, args)
        except ToolViolation as e:
            fail(str(e), clear_changes=True)
            return
        except Exception as e:
            fail(f"工具执行异常: {e}", clear_changes=False)
            return

        # 模型上下文保留实际动作；对用户展示仍仅通过 transcript 输出自然语言。
        messages.append({"role": "assistant", "content": raw})
        observation = {
            "marker": "UNTRUSTED_OBSERVATION",
            "tool": tool,
            "args": args,
            "step": step,
            "data": data,
        }
        messages.append(
            {"role": "user", "content": json.dumps(observation, ensure_ascii=False, default=str)}
        )

        if tool == "finish":
            finalize_turn(step, ctx.finish_answer or "", said)
            return

        summary = {"tool": tool, "change_count": len(ctx.changes)}
        if not persist_progress("tool", f"{tool} {json.dumps(summary, ensure_ascii=False)}"):
            return

    fail(f"超过最大步数（{MAX_STEPS}），任务中止", clear_changes=False)


# ---------------------------------------------------------------------------
# transition：apply / revert / cancel / resume
# ---------------------------------------------------------------------------

def _bump_updated_at(obj):
    """与 projects.py 保存路径一致的微秒级补偿，保证修订号严格递增。"""
    previous = getattr(obj, "updated_at", None)
    if previous is not None and previous.tzinfo is not None:
        previous = previous.astimezone(timezone.utc).replace(tzinfo=None)
    now = datetime.utcnow()
    obj.updated_at = max(now, previous + timedelta(microseconds=1)) if previous else now


def _owned_document(db, run: AgentRun, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.project_id != run.project_id:
        raise HTTPException(status_code=409, detail=f"文档 {document_id} 不存在或已被移出项目")
    return document


def _live_block(document: Document, block_id: str) -> Optional[dict]:
    for block in document.content or []:
        if isinstance(block, dict) and block.get("id") == block_id:
            return block
    return None


def _snapshot_version(db, document: Document, run: AgentRun, summary: str):
    """应用/撤销前为文档留一个可恢复的版本快照。"""
    latest = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )
    db.add(
        DocumentVersion(
            document_id=document.id,
            title=document.title or "",
            content=json.loads(json.dumps(document.content or [], ensure_ascii=False)),
            version_number=(latest.version_number + 1) if latest else 1,
            change_summary=summary[:200],
            created_by=run.user_id,
        )
    )


def _get_memory(db, run: AgentRun) -> AIMemory:
    memory = db.query(AIMemory).filter(AIMemory.project_id == run.project_id).first()
    if memory is None:
        raise HTTPException(status_code=409, detail="项目设定不存在，无法应用修改")
    return memory


# --- apply ---

def _check_change_apply(db, run: AgentRun, change: dict):
    kind = change.get("kind")
    if kind == "document_patch":
        document = _owned_document(db, run, change["document_id"])
        block = _live_block(document, change["block_id"])
        current = block.get("content") if block else None
        if current != change["before"]:
            raise HTTPException(
                status_code=409,
                detail=f"《{change.get('title') or document.title}》在提案后被修改，存在版本冲突",
            )
    elif kind == "memory_patch":
        memory = _get_memory(db, run)
        if _norm(getattr(memory, change["field"], None)) != _norm(change["before"]):
            raise HTTPException(status_code=409, detail=f"设定字段 {change['field']} 已被修改，存在版本冲突")
    elif kind == "create_document":
        return
    else:
        raise HTTPException(status_code=409, detail=f"未知修改类型: {kind}")


def _apply_change(db, run: AgentRun, change: dict):
    kind = change.get("kind")
    if kind == "document_patch":
        document = _owned_document(db, run, change["document_id"])
        blocks = json.loads(json.dumps(document.content or [], ensure_ascii=False))
        block = _find_block(blocks, change["block_id"])
        _snapshot_version(db, document, run, f"智能体应用：{change.get('reason', '')}")
        block["content"] = change["after"]
        document.content = blocks
        _bump_updated_at(document)
    elif kind == "memory_patch":
        memory = _get_memory(db, run)
        setattr(memory, change["field"], change["after"])
        _bump_updated_at(memory)
    elif kind == "create_document":
        from app.utils.document_format import parse_formatted_text_to_blocks

        after = change["after"] or {}
        max_order = (
            db.query(Document)
            .filter(Document.project_id == run.project_id)
            .order_by(Document.order_index.desc())
            .first()
        )
        document = Document(
            project_id=run.project_id,
            title=after.get("title", "未命名"),
            content=parse_formatted_text_to_blocks(
                after.get("text", ""), f"agent{uuid.uuid4().hex[:8]}"
            ),
            order_index=(max_order.order_index + 1) if max_order else 0,
        )
        db.add(document)
        db.flush()
        change["target_id"] = document.id


def _apply(db, run: AgentRun):
    if run.status == "applied":
        return  # 幂等：重复 apply 安全
    if run.status != "proposed":
        raise HTTPException(status_code=409, detail=f"当前状态 {run.status} 不可应用修改")
    # 深拷贝：_apply_change 会原地修改 change（如回填 create 的 target_id），
    # 若直接引用 run.changes 的实时 JSON 对象，赋值时会因值相等而被 ORM 判定未变更
    changes = json.loads(json.dumps(run.changes or [], ensure_ascii=False, default=str))
    for change in changes:
        _check_change_apply(db, run, change)  # 第一遍全量校验，任一冲突即拒绝且不变更任何目标
    for change in changes:
        _apply_change(db, run, change)
    run.changes = json.loads(json.dumps(changes, ensure_ascii=False, default=str))
    run.status = "applied"
    _append_event(run, "apply", f"已应用 {len(changes)} 项修改")
    db.commit()


# --- revert ---

def _check_change_revert(db, run: AgentRun, change: dict):
    kind = change.get("kind")
    if kind == "document_patch":
        document = _owned_document(db, run, change["document_id"])
        block = _live_block(document, change["block_id"])
        current = block.get("content") if block else None
        if current != change["after"]:
            raise HTTPException(
                status_code=409,
                detail=f"《{change.get('title') or document.title}》在应用后被人工修改，拒绝覆盖，无法撤销",
            )
    elif kind == "memory_patch":
        memory = _get_memory(db, run)
        if _norm(getattr(memory, change["field"], None)) != _norm(change["after"]):
            raise HTTPException(status_code=409, detail=f"设定字段 {change['field']} 已被修改，无法撤销")
    elif kind == "create_document":
        document = db.get(Document, change.get("target_id")) if change.get("target_id") else None
        if document is None:
            return  # 文档已不存在（可能被删除），视为已回滚
        after = change.get("after") or {}
        if document.title != after.get("title"):
            raise HTTPException(status_code=409, detail="该文档在创建后被人工修改，拒绝删除，无法撤销")
    else:
        raise HTTPException(status_code=409, detail=f"未知修改类型: {kind}")


def _revert_change(db, run: AgentRun, change: dict):
    kind = change.get("kind")
    if kind == "document_patch":
        document = _owned_document(db, run, change["document_id"])
        blocks = json.loads(json.dumps(document.content or [], ensure_ascii=False))
        block = _find_block(blocks, change["block_id"])
        _snapshot_version(db, document, run, f"智能体撤销：{change.get('reason', '')}")
        block["content"] = change["before"]
        document.content = blocks
        _bump_updated_at(document)
    elif kind == "memory_patch":
        memory = _get_memory(db, run)
        setattr(memory, change["field"], change["before"])
        _bump_updated_at(memory)
    elif kind == "create_document":
        document = db.get(Document, change.get("target_id")) if change.get("target_id") else None
        if document is not None:
            db.delete(document)


def _revert(db, run: AgentRun):
    if run.status == "reverted":
        return  # 幂等
    if run.status != "applied":
        raise HTTPException(status_code=409, detail=f"当前状态 {run.status} 不可撤销")
    # 深拷贝，原因同 _apply：避免原地修改后 JSON 值相等导致 ORM 跳过 UPDATE
    changes = json.loads(json.dumps(run.changes or [], ensure_ascii=False, default=str))
    for change in changes:
        _check_change_revert(db, run, change)  # 逆向修改集不覆盖之后的人工作品
    for change in changes:
        _revert_change(db, run, change)
    run.status = "reverted"
    _append_event(run, "revert", f"已撤销 {len(changes)} 项修改")
    db.commit()


# --- cancel / resume ---

def _cancel(db, run: AgentRun):
    if run.status == "cancelled":
        return
    if run.status not in ("queued", "running", "proposed"):
        raise HTTPException(status_code=409, detail=f"当前状态 {run.status} 不可取消")
    run.status = "cancelled"
    release_lease(run)
    _append_event(run, "cancel", "任务已取消")
    db.commit()


def _resume(db, run: AgentRun):
    if run.status not in ("cancelled", "failed"):
        raise HTTPException(status_code=409, detail=f"当前状态 {run.status} 不可恢复")
    run.status = "queued"
    run.error = None
    release_lease(run)
    _append_event(run, "resume", "任务已重新排队")
    db.commit()


def transition(db, user_id: int, project_id: int, run_id: str, verb: str) -> AgentRun:
    run = get_run(db, user_id, project_id, run_id)
    if verb == "apply":
        _apply(db, run)
    elif verb == "revert":
        _revert(db, run)
    elif verb == "cancel":
        _cancel(db, run)
    elif verb == "resume":
        _resume(db, run)
    else:
        raise HTTPException(status_code=400, detail=f"未知操作: {verb}")
    db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# 工作器（FastAPI 启动时的 in-process worker；scripts/agent_worker.py 可独立运行）
# ---------------------------------------------------------------------------

async def agent_worker_loop(poll_seconds: float = 2.0):
    from app.database import SessionLocal

    while True:
        try:
            claim = claim_run(SessionLocal)
            if claim is not None:
                await execute_run(SessionLocal, claim)
        except Exception as e:  # noqa: BLE001 - 工作器永不退出
            print(f"[AgentWorker] 执行异常: {e}")
        await asyncio.sleep(poll_seconds)
