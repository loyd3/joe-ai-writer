"""
项目智能体工具层：白名单校验、暂存修改集（ChangeSet）与全文覆盖检查。

模型只能调用这里登记的工具；每次调用都经过参数精确集合校验、类型校验、
越权校验与「先读后改」校验。所有修改只作用于内存暂存（ctx），
不写库——直到用户在 transition('apply') 确认后由 service 原子发布。
"""
import asyncio
import concurrent.futures
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import AIMemory, Document
from app.services.memory_normalize import coerce_memory_field, merge_memory_field
from app.services.project_agent_phases import (
    check_propose_payload_size,
    current_phase,
    enable_narrow_mode,
    generation_forbids_settings_edits,
    instruction_forbids_unsolicited_settings,
    looks_like_generate_documents_instruction,
    requested_setting_fields,
)
from app.services import writing_adapters


class ToolViolation(Exception):
    """工具调用违反白名单/权限/一致性约束：run 立即失败且不产生任何提案。"""


# AIMemory 允许智能体补丁的字段（id/project_id/updated_at 等一律不可触碰）
MEMORY_FIELDS = [
    "outline",
    "storyline",
    "characters",
    "world_building",
    "writing_style",
    "key_points",
    "notes",
]

_REQUIRED = object()  # 参数必需标记
_DRAFT_PREVIEW_CHARS = 400
_ASYNC_TOOL_TIMEOUT_SEC = 300


def _int(v):
    """int 参数校验：显式拒绝 bool（bool 是 int 子类，True 会误通过）。"""
    return isinstance(v, int) and not isinstance(v, bool)


def _str(v):
    return isinstance(v, str)


def _bool(v):
    return isinstance(v, bool)


def _any(v):
    return True


def _run_async(coro):
    """在同步工具处理器中跑 async adapter（execute_run 已在事件循环内）。

    超时后 shutdown(wait=False)，避免 ThreadPoolExecutor 上下文在 TimeoutError
    后仍 wait=True 阻塞到 LLM 结束，使超时形同虚设。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(asyncio.run, coro)
        return future.result(timeout=_ASYNC_TOOL_TIMEOUT_SEC)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError(f"专项写作超时（>{_ASYNC_TOOL_TIMEOUT_SEC}s）") from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


_ARG_SPECS: Dict[str, Dict[str, Any]] = {
    "list_project": {},
    # 长文：先看目录/结构，勿塞正文（借鉴 Kimi「先定位再深读」）
    "document_map": {"document_id": (_int, 0), "limit": (_int, 40)},
    # 长文：抽取引擎摘要进 ctx，observation 只回短 digest（主上下文隔离）
    "digest_document": {"document_id": (_int, _REQUIRED), "max_chars": (_int, 1600)},
    # 默认每页 12 块：大文档整页塞进上下文会导致模型空响应
    "read_document": {"document_id": (_int, _REQUIRED), "offset": (_int, 0), "limit": (_int, 12)},
    # field 可空：返回全字段摘要；指定 field 时返回该字段较完整内容，便于精准改设定
    "read_memory": {"field": (_str, "")},
    "search_project": {"query": (_str, _REQUIRED), "offset": (_int, 0), "limit": (_int, 10)},
    "propose_document_patch": {
        "document_id": (_int, _REQUIRED),
        "block_id": (_str, _REQUIRED),
        "old_text": (_str, _REQUIRED),
        "new_text": (_str, _REQUIRED),
        "reason": (_str, ""),  # 模型常漏填；空则自动兜底，避免整轮失败
    },
    "propose_block_rewrite": {
        "document_id": (_int, _REQUIRED),
        "block_id": (_str, _REQUIRED),
        "new_content": (_str, _REQUIRED),
        "reason": (_str, ""),
    },
    "propose_memory_patch": {
        "field": (_str, _REQUIRED),
        "after": (_any, _REQUIRED),
        "before": (_any, None),  # 可省略：服务端用暂存值填充
        "mode": (_str, "replace"),  # replace=整字段覆盖；merge=增量合并（列表 upsert）
        "reason": (_str, ""),
    },
    "propose_create_document": {
        "title": (_str, _REQUIRED),
        "text": (_str, _REQUIRED),
        "reason": (_str, ""),
    },
    "generate_documents_from_settings": {
        "custom_instruction": (_str, ""),
        "max_tokens_per_chapter": (_int, 4000),
    },
    "propose_delete_document": {
        "document_id": (_int, _REQUIRED),
        "reason": (_str, ""),
    },
    "create_project": {
        "title": (_str, _REQUIRED),
        "description": (_str, ""),
        "reason": (_str, ""),
    },
    "list_hot_topics": {
        "limit": (_int, 20),
        "category": (_str, ""),
        "refresh": (_bool, False),
    },
    "hot_topic_write": {
        "topic_title": (_str, _REQUIRED),
        "article_type": (_str, "评论"),
        "word_count": (_int, 1500),
        "style": (_str, "专业"),
        "additional_requirements": (_str, ""),
    },
    "copywriting_write": {
        "product": (_str, ""),
        "target_audience": (_str, ""),
        "copy_objective": (_str, "广告"),
        "selling_points": (_str, ""),
        "pain_points": (_str, ""),
        "evidence_cases": (_str, ""),
        "cta": (_str, ""),
        "tone": (_str, "专业且有说服力"),
        "word_count": (_int, 900),
        "additional_requirements": (_str, ""),
    },
    "list_brainstorm_ideas": {
        "category": (_str, ""),
        "limit": (_int, 12),
    },
    "brainstorm_write": {
        "title": (_str, ""),
        "category": (_str, "脑洞"),
        "concept": (_str, ""),
        "style": (_str, "幽默风趣"),
        "word_count": (_str, "medium"),
    },
    "story_generate": {
        "theme": (_str, _REQUIRED),
        "genre": (_str, ""),
        "word_count": (_int, 5000),
        "chapter_count": (_int, 0),
        "additional_requirements": (_str, ""),
    },
    "propose_writing_draft": {
        "draft_id": (_str, _REQUIRED),
        "reason": (_str, ""),
        "title": (_str, ""),
    },
    "propose_story_settings": {
        "draft_id": (_str, _REQUIRED),
        "reason": (_str, ""),
    },
    "finish": {"answer": (_str, "")},  # answer 可缺省：用当轮自然语言回复兜底，避免常见的空参调用直接失败
}

_DEFAULT_REASONS = {
    "propose_document_patch": "正文补丁",
    "propose_block_rewrite": "整块改写",
    "propose_memory_patch": "更新项目设定",
    "propose_create_document": "新建文档",
    "propose_delete_document": "删除文档",
    "propose_writing_draft": "写入专项写作草稿",
    "propose_story_settings": "写入故事设定",
    "create_project": "用户请求创建项目",
}


# 模型常瞎加的无害多余参数；丢掉即可，勿整轮失败
_IGNORABLE_EXTRA_ARGS = frozenset({
    "reason", "mode", "full", "complete", "force", "verbose", "stream",
    "offset", "limit", "max_chars", "preview", "detailed", "detail",
})


def _validate_args(tool: str, args: Any) -> Dict[str, Any]:
    if not isinstance(args, dict):
        raise ToolViolation(f"工具 {tool} 的参数必须是对象")
    args = dict(args)
    # finish / reason 常被模型写成 null 或缺省 —— 先归一化再校验
    if tool == "finish" or "reason" in (_ARG_SPECS.get(tool) or {}):
        if tool == "finish":
            raw_answer = args.get("answer")
            if raw_answer is None:
                args["answer"] = ""
            elif not isinstance(raw_answer, str):
                args["answer"] = str(raw_answer)
        if "reason" in args:
            raw_reason = args.get("reason")
            if raw_reason is None:
                args["reason"] = ""
            elif not isinstance(raw_reason, str):
                args["reason"] = str(raw_reason)
    # read_memory：field 别名 / 非字符串容错（避免「不支持参数 field」类假失败）
    if tool == "read_memory":
        if "field" not in args:
            for alias in ("name", "memory_field", "key", "字段"):
                if alias in args:
                    args["field"] = args.pop(alias)
                    break
        if "field" in args and not isinstance(args["field"], str):
            args["field"] = "" if args["field"] is None else str(args["field"])
    if tool not in _ARG_SPECS:
        raise ToolViolation(f"未知工具: {tool}")
    spec = dict(_ARG_SPECS[tool])
    # 防御：即便规格表异常，read_memory 也必须接受 field
    if tool == "read_memory" and "field" not in spec:
        spec["field"] = (_str, "")
    extra = set(args) - set(spec)
    benign = extra & _IGNORABLE_EXTRA_ARGS
    real_extra = extra - _IGNORABLE_EXTRA_ARGS
    for key in benign:
        args.pop(key, None)
    if real_extra:
        raise ToolViolation(f"工具 {tool} 不支持参数: {sorted(real_extra)}")
    resolved = {}
    for name, (checker, default) in spec.items():
        if name not in args:
            if default is _REQUIRED:
                raise ToolViolation(f"工具 {tool} 缺少参数: {name}")
            resolved[name] = default
            continue
        value = args[name]
        if not checker(value):
            raise ToolViolation(f"工具 {tool} 参数 {name} 类型错误")
        resolved[name] = value
    # reason 空串兜底，避免模型漏填导致整轮失败
    if "reason" in resolved and isinstance(resolved["reason"], str):
        stripped = resolved["reason"].strip()
        resolved["reason"] = stripped or _DEFAULT_REASONS.get(tool, "智能体提案")
    # 分页参数夹紧到安全范围（read_document 更严，防止一次塞爆上下文）
    for name in ("offset", "limit"):
        if name in resolved:
            cap = 20 if (tool == "read_document" and name == "limit") else (
                1000 if name == "limit" else 10**9
            )
            resolved[name] = max(0, min(int(resolved[name]), cap))
    if "limit" in resolved and resolved["limit"] == 0:
        resolved["limit"] = 1
    # 写作字数/章节夹紧，避免模型传入极端值撑爆 token
    if "word_count" in resolved and _int(resolved["word_count"]):
        if tool == "story_generate":
            resolved["word_count"] = max(500, min(int(resolved["word_count"]), 20000))
        elif tool in ("hot_topic_write", "copywriting_write"):
            resolved["word_count"] = max(100, min(int(resolved["word_count"]), 8000))
    if tool == "story_generate" and "chapter_count" in resolved and _int(resolved["chapter_count"]):
        cc = int(resolved["chapter_count"])
        resolved["chapter_count"] = 0 if cc <= 0 else min(cc, 50)
    return resolved


def _norm(value: Any) -> str:
    """跨类型稳定比较：JSON 结构按序序列化，其余转字符串。"""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if value is None:
        return "∅"
    return str(value)


class ProjectAgentContext:
    """一次 run 的执行上下文：已读暂存 + 修改集累积。全程内存态，不写库。

    project_id 可为 None（系统级会话）：可先专项写作/create_project，再建项后提案。
    create_project 会即时落库并回填 project_id；文档/设定修改仍走 changes 提案。
    """

    def __init__(self, project_id: Optional[int], user_id: int):
        self.project_id = project_id
        self.user_id = user_id
        self.scope = "project" if project_id else "system"
        self.read_documents: Dict[int, List[dict]] = {}  # doc_id -> 暂存块（深拷贝）
        self.document_titles: Dict[int, str] = {}
        self.focus_document_id: Optional[int] = None  # 当前打开的文档；「这篇」即此 id
        self.focus_block_ids: Optional[List[str]] = None  # 选中/目标块；有则禁止通读
        self.memory_read = False
        self.staged_memory: Dict[str, Any] = {}
        self.memory_row_id: Optional[int] = None
        self.changes: List[dict] = []
        self.finish_answer: Optional[str] = None
        # 专项写作草稿：完整正文/设定存在这里，observation 只给预览 + draft_id
        self.writing_drafts: Dict[str, dict] = {}
        # 复杂指令后台分步：work_plan 由 service 推断；narrow_mode 在截断后强制收窄
        self.work_plan: List[dict] = []
        self.work_plan_index: int = 0
        self.narrow_mode: bool = False
        self.instruction: str = ""
        # 连续读正文计数：防止「先通读全部章节」把上下文撑空
        self.read_document_pages: int = 0
        self.read_document_ids: List[int] = []
        # 长文摘要（主上下文只见短 digest；全文不进 messages）
        self.document_digests: Dict[int, dict] = {}
        self.document_maps: Dict[int, dict] = {}

    # --- 修改集（每个目标至多一条 change，多次补丁合并为 before→after） ---
    def _find_change(self, kind: str, **keys) -> Optional[dict]:
        for change in self.changes:
            if change["kind"] != kind:
                continue
            if all(change.get(k) == v for k, v in keys.items()):
                return change
        return None

    def _append_change(self, change: dict) -> dict:
        self.changes.append(change)
        return change


def _require_project(ctx: ProjectAgentContext) -> int:
    if not ctx.project_id:
        raise ToolViolation(
            "当前尚未绑定项目。请先 create_project(title=...) 创建项目，"
            "或请用户打开一个已有项目后再试。"
        )
    return int(ctx.project_id)


def _project_document(db: Session, project_id: int, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.project_id != project_id:
        raise ToolViolation(f"文档 {document_id} 不存在或不属于当前项目")
    return document


def _find_block(blocks: List[dict], block_id: str) -> dict:
    for block in blocks:
        if isinstance(block, dict) and block.get("id") == block_id:
            return block
    raise ToolViolation(f"找不到块: {block_id}")


# ---------------------------------------------------------------------------
# 工具实现：返回 observation data（将由 service 包成 UNTRUSTED_OBSERVATION）
# ---------------------------------------------------------------------------

def tool_list_project(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    project_id = _require_project(ctx)
    documents = (
        db.query(Document.id, Document.title, Document.order_index)
        .filter(Document.project_id == project_id)
        .order_by(Document.order_index.asc(), Document.id.asc())
        .all()
    )
    result: Dict[str, Any] = {
        "project_id": project_id,
        "documents": [
            {"document_id": d.id, "title": d.title, "order_index": d.order_index} for d in documents
        ],
        "memory_fields": list(MEMORY_FIELDS),
        "complete": True,
    }
    focus_id = ctx.focus_document_id
    if focus_id:
        title = ctx.document_titles.get(focus_id) or next(
            (d.title for d in documents if d.id == focus_id), ""
        )
        result["focus_document_id"] = focus_id
        result["focus_title"] = title
        result["message"] = (
            f"用户当前打开的就是 document_id={focus_id}"
            + (f"《{title}》" if title else "")
            + "。「这篇/当前文档/焦点段落」都指这一篇。"
            + (
                "正文已预读，请直接 propose_block_rewrite / propose_document_patch，不要再追问是哪一篇。"
                if focus_id in ctx.read_documents
                else "请 read_document 读取该 id 后改稿，不要再追问是哪一篇。"
            )
        )
    return result


_OBS_BLOCK_CHARS = 700  # 观察里每块截断长度；完整正文仍在 ctx 供 rewrite


def _clip_obs_text(text: Any, limit: int = _OBS_BLOCK_CHARS) -> Any:
    if not isinstance(text, str):
        return text
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _is_heading_block(block: dict) -> bool:
    btype = str(block.get("type") or "").lower()
    if "heading" in btype or btype in ("h1", "h2", "h3", "h4", "title"):
        return True
    props = block.get("props") if isinstance(block.get("props"), dict) else {}
    level = props.get("level")
    return isinstance(level, int) and level >= 1


def _block_char_count(blocks: List[dict]) -> int:
    total = 0
    for block in blocks:
        content = block.get("content") if isinstance(block, dict) else None
        if isinstance(content, str):
            total += len(content)
    return total


def _extract_headings(blocks: List[dict], limit: int = 40) -> List[dict]:
    headings: List[dict] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or not _is_heading_block(block):
            continue
        text = (block.get("content") or "").strip()
        if not text:
            continue
        props = block.get("props") if isinstance(block.get("props"), dict) else {}
        headings.append(
            {
                "block_id": block.get("id"),
                "offset": index,
                "level": props.get("level") or 2,
                "text": text[:120],
            }
        )
        if len(headings) >= limit:
            break
    return headings


def _build_extractive_digest(
    title: str, blocks: List[dict], max_chars: int = 1600
) -> dict:
    """无模型抽取引擎摘要：标题层级 + 段落首句，控制进主上下文的体积。"""
    headings = _extract_headings(blocks, limit=30)
    lines: List[str] = []
    used = 0
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        content = (block.get("content") or "").strip()
        if not content:
            continue
        if _is_heading_block(block):
            line = f"【{content[:80]}】"
        else:
            # 取首句/前 100 字，避免把整段塞进 digest
            cut = content.find("。")
            if 0 < cut < 100:
                piece = content[: cut + 1]
            else:
                piece = content[:100] + ("…" if len(content) > 100 else "")
            line = piece
        if used + len(line) + 1 > max_chars:
            remain = len(blocks) - index
            if remain > 0:
                lines.append(f"…（其后约 {remain} 块已省略；改稿请 read_document 定点深读）")
            break
        lines.append(line)
        used += len(line) + 1
    return {
        "title": title,
        "block_count": len(blocks),
        "char_count": _block_char_count(blocks),
        "headings": headings,
        "digest": "\n".join(lines) if lines else "（空文档）",
    }


def _map_one_document(document: Document, heading_limit: int = 40) -> dict:
    blocks = [b for b in (document.content or []) if isinstance(b, dict)]
    return {
        "document_id": document.id,
        "title": document.title or "",
        "parent_id": document.parent_id,
        "order_index": document.order_index or 0,
        "block_count": len(blocks),
        "char_count": _block_char_count(blocks),
        "headings": _extract_headings(blocks, limit=heading_limit),
    }


def tool_document_map(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """项目/单篇目录地图：只返回结构，不返回正文（长文定位入口）。"""
    project_id = _require_project(ctx)
    document_id = int(args.get("document_id") or 0)
    heading_limit = int(args.get("limit") or 40)
    heading_limit = max(5, min(heading_limit, 80))

    if document_id:
        document = _project_document(db, project_id, document_id)
        mapped = _map_one_document(document, heading_limit=heading_limit)
        ctx.document_maps[document.id] = mapped
        ctx.document_titles[document.id] = document.title or ""
        return {
            "coverage": "single_document",
            "document": mapped,
            "complete": True,
            "message": (
                f"《{mapped['title'] or document_id}》目录已就绪（{mapped['block_count']} 块 / "
                f"约 {mapped['char_count']} 字）。需要细节时 digest_document 或 "
                f"read_document(offset=标题对应 offset)；禁止通读全文。"
            ),
        }

    documents = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.order_index.asc(), Document.id.asc())
        .all()
    )
    # 全项目地图：每篇标题数更紧，避免目录本身撑爆上下文
    per_doc_heading_cap = 12 if len(documents) > 8 else heading_limit
    items = []
    for document in documents:
        mapped = _map_one_document(document, heading_limit=per_doc_heading_cap)
        ctx.document_maps[document.id] = mapped
        ctx.document_titles[document.id] = document.title or ""
        items.append(mapped)
    total_chars = sum(item["char_count"] for item in items)
    return {
        "coverage": "project",
        "document_count": len(items),
        "total_chars": total_chars,
        "documents": items,
        "complete": True,
        "message": (
            f"项目目录已就绪：{len(items)} 篇，合计约 {total_chars} 字。"
            "长文策略：document_map → digest_document（抽关键章）→ "
            "定点 read_document / propose_*；不要连续 read_document 通读。"
        ),
    }


def tool_digest_document(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """章节抽取引擎摘要：全文不进主上下文（类 Kimi 子任务隔离）；改稿仍须定点 read_document。"""
    project_id = _require_project(ctx)
    document = _project_document(db, project_id, args["document_id"])
    max_chars = int(args.get("max_chars") or 1600)
    max_chars = max(400, min(max_chars, 4000))
    blocks = [b for b in (document.content or []) if isinstance(b, dict)]
    ctx.document_titles[document.id] = document.title or ""
    digest = _build_extractive_digest(document.title or "", blocks, max_chars=max_chars)
    digest["document_id"] = document.id
    ctx.document_digests[document.id] = digest
    return {
        "document_id": document.id,
        "title": digest["title"],
        "block_count": digest["block_count"],
        "char_count": digest["char_count"],
        "headings": digest["headings"],
        "digest": digest["digest"],
        "complete": True,
        "message": (
            f"《{digest['title'] or document.id}》摘要已生成（全文约 {digest['char_count']} 字未进入对话）。"
            "主上下文只保留本摘要。要改某一段：用 headings 的 offset 调用 read_document，"
            "再 propose_block_rewrite；禁止用摘要冒充全文通读。"
        ),
    }


# 未提案前最多读几页正文；超出则拒读并要求先改设定/改当前页
_MAX_READ_PAGES_WITHOUT_CHANGE = 3
_MAX_DISTINCT_DOCS_WITHOUT_CHANGE = 2


def tool_read_document(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    document = _project_document(db, _require_project(ctx), args["document_id"])
    # 梳理设定类任务：已有 work_plan 且当前步不是读正文时，拦截通读
    plan = getattr(ctx, "work_plan", None) or []
    if plan and not ctx.changes:
        from app.services.project_agent_phases import current_phase

        step = current_phase(ctx)
        if step and step.get("kind") in ("read_memory", "propose_memory_patch"):
            raise ToolViolation(
                "当前任务是梳理设定（storyline/outline），禁止通读章节正文。"
                "请 read_memory(field=...) 或直接 propose_memory_patch；"
                "章节正文等用户点名某一篇后再改。"
            )
    distinct = set(ctx.read_document_ids or [])
    if (
        not ctx.changes
        and (
            ctx.read_document_pages >= _MAX_READ_PAGES_WITHOUT_CHANGE
            or (document.id not in distinct and len(distinct) >= _MAX_DISTINCT_DOCS_WITHOUT_CHANGE)
        )
    ):
        raise ToolViolation(
            f"已连续阅读 {ctx.read_document_pages} 页/"
            f"{len(distinct)} 篇文档却尚未提出任何修改。"
            "禁止继续通读。请立刻 propose_memory_patch 或对本页块 propose_block_rewrite，"
            "或 finish 说明需要用户缩小范围。"
        )

    blocks = [b for b in (document.content or []) if isinstance(b, dict)]
    ctx.read_documents[document.id] = json.loads(json.dumps(blocks, ensure_ascii=False))
    ctx.document_titles[document.id] = document.title or ""
    ctx.read_document_pages = int(getattr(ctx, "read_document_pages", 0) or 0) + 1
    if document.id not in (ctx.read_document_ids or []):
        ctx.read_document_ids = list(ctx.read_document_ids or []) + [document.id]
    offset, limit = args["offset"], args["limit"]
    page = blocks[offset : offset + limit]
    complete = offset + limit >= len(blocks)
    tip = (
        "本页已读完。请立即对本页需要润色的块调用 propose_block_rewrite（每次 1～3 块），"
        "不要先通读全文。改完若还有后文，再 read_document 提高 offset。"
        if not complete
        else "已到文末。请对本页需要改的块 propose_block_rewrite，然后 finish。"
    )
    return {
        "document_id": document.id,
        "title": document.title,
        "total_blocks": len(blocks),
        "offset": offset,
        "limit": limit,
        "complete": complete,
        "next_offset": None if complete else offset + limit,
        "message": tip,
        "blocks": [
            {
                "id": b.get("id"),
                "type": b.get("type"),
                "content": _clip_obs_text(b.get("content")),
            }
            for b in page
        ],
    }


def _memory_field_overview(value: Any) -> Dict[str, Any]:
    """全量 read_memory 时的字段概览，避免一次塞爆上下文。"""
    if value is None:
        return {"empty": True, "preview": None}
    if isinstance(value, str):
        text = value.strip()
        return {
            "empty": not text,
            "chars": len(text),
            "preview": text if len(text) <= 240 else text[:240] + "…",
        }
    if isinstance(value, list):
        return {
            "empty": len(value) == 0,
            "count": len(value),
            "preview": value[:3],
        }
    if isinstance(value, dict):
        blob = json.dumps(value, ensure_ascii=False, default=str)
        return {
            "empty": not value,
            "chars": len(blob),
            "preview": value if len(blob) <= 400 else {"_truncated": True, "keys": list(value.keys())[:12]},
        }
    blob = json.dumps(value, ensure_ascii=False, default=str)
    return {"empty": False, "preview": blob[:240] + ("…" if len(blob) > 240 else "")}


# 单字段观察上限：完整值留 staged_memory，避免把大 storyline 塞进主对话导致空响应
_MAX_MEMORY_FIELD_OBS_CHARS = 2200


def tool_read_memory(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    memory = db.query(AIMemory).filter(AIMemory.project_id == _require_project(ctx)).first()
    ctx.memory_read = True
    ctx.staged_memory = {
        field: json.loads(
            json.dumps(
                coerce_memory_field(field, getattr(memory, field) if memory else None),
                ensure_ascii=False,
                default=str,
            )
        )
        for field in MEMORY_FIELDS
    }
    ctx.memory_row_id = memory.id if memory else None

    raw_field = (args.get("field") or "").strip()
    field = _coerce_memory_field_name(raw_field) if raw_field else None
    if raw_field and not field:
        raise ToolViolation(
            f"未知设定字段: {raw_field}。可选: {', '.join(MEMORY_FIELDS)}"
        )

    if field:
        value = ctx.staged_memory.get(field)
        try:
            blob = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            blob = str(value)
        full_chars = len(blob)
        if full_chars > _MAX_MEMORY_FIELD_OBS_CHARS:
            # 大字段只回摘要；完整值已在 ctx.staged_memory，merge 不必再通读
            return {
                "memory_id": ctx.memory_row_id,
                "field": field,
                "value": _memory_field_overview(value),
                "full_chars": full_chars,
                "coverage": "single_field_digest",
                "complete": True,
                "message": (
                    f"字段 {field} 约 {full_chars} 字，完整值已在服务端暂存，对话里只给概览。"
                    f"请直接 propose_memory_patch(field=\"{field}\", mode=\"merge\", after=改动项)；"
                    "before 可省略。禁止再索要「完整 storyline/outline 全文」。"
                ),
            }
        return {
            "memory_id": ctx.memory_row_id,
            "field": field,
            "value": value,
            "coverage": "single_field",
            "complete": True,
            "message": (
                f"已读取字段 {field}。请用 propose_memory_patch"
                f"(field=\"{field}\", mode=\"merge\"|\"replace\", after=...) 更新；"
                "before 可省略。"
            ),
        }

    overview = {f: _memory_field_overview(ctx.staged_memory.get(f)) for f in MEMORY_FIELDS}
    return {
        "memory_id": ctx.memory_row_id,
        "fields": overview,
        "available_fields": list(MEMORY_FIELDS),
        "coverage": "overview",
        "complete": True,
        "message": (
            "以上为各设定字段概览。大字段不必再 read_memory 取全文；"
            "直接 propose_memory_patch(mode=\"merge\") 只传新增/改动项即可。"
        ),
    }


def tool_search_project(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    project_id = _require_project(ctx)
    query = args["query"].lower()
    matches: List[dict] = []
    documents = (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.order_index.asc(), Document.id.asc())
        .all()
    )
    for document in documents:
        for block in document.content or []:
            if not isinstance(block, dict):
                continue
            content = block.get("content")
            if isinstance(content, str) and query in content.lower():
                matches.append(
                    {
                        "document_id": document.id,
                        "title": document.title,
                        "block_id": block.get("id"),
                        "excerpt": content[:200],
                    }
                )
    memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
    if memory:
        for field in MEMORY_FIELDS:
            value = getattr(memory, field)
            text = _norm(value)
            if value is not None and query in text.lower():
                matches.append({"memory": True, "field": field, "excerpt": text[:200]})
    offset, limit = args["offset"], args["limit"]
    return {
        "query": args["query"],
        "total": len(matches),
        "offset": offset,
        "limit": limit,
        # 全项目文档 + 设定的字面量检索（非语义），供覆盖检查声明
        "coverage": "all_project_documents_and_memory_literal",
        "complete": offset + limit >= len(matches),
        "matches": matches[offset : offset + limit],
    }


def tool_propose_document_patch(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    _require_project(ctx)
    document_id = args["document_id"]
    if document_id not in ctx.read_documents:
        raise ToolViolation(f"须先 read_document 读取文档 {document_id} 后才能提出补丁")
    blocks = ctx.read_documents[document_id]
    block = _find_block(blocks, args["block_id"])
    content = block.get("content")
    old_text = args["old_text"]
    if not isinstance(content, str):
        raise ToolViolation("目标块没有可修改的文本内容")
    if not old_text:
        raise ToolViolation("old_text 不能为空")
    occurrences = content.count(old_text)
    if occurrences == 0:
        raise ToolViolation(f"old_text 在目标块中不存在（暂存内容可能已被之前的补丁改变）")
    if occurrences > 1:
        raise ToolViolation(f"old_text 在目标块中出现 {occurrences} 次，存在歧义，请扩大上下文")
    new_content = content.replace(old_text, args["new_text"], 1)
    block["content"] = new_content

    change = ctx._find_change("document_patch", document_id=document_id, block_id=args["block_id"])
    if change is None:
        change = ctx._append_change(
            {
                "id": str(uuid.uuid4()),
                "kind": "document_patch",
                "target_id": document_id,
                "document_id": document_id,
                "block_id": args["block_id"],
                "title": ctx.document_titles.get(document_id, ""),
                "before": content,
                "after": new_content,
                "reason": args["reason"],
            }
        )
    else:
        change["after"] = new_content
        change["reason"] = args["reason"]
    return {
        "document_id": document_id,
        "block_id": args["block_id"],
        "staged_content": new_content,
        "change_count": len(ctx.changes),
        "complete": True,
    }


def tool_propose_block_rewrite(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """整块重写：润色/改写/扩写一段时用，避免精确抠 old_text。"""
    _require_project(ctx)
    document_id = args["document_id"]
    if document_id not in ctx.read_documents:
        raise ToolViolation(f"须先 read_document 读取文档 {document_id} 后才能提出重写")
    blocks = ctx.read_documents[document_id]
    block = _find_block(blocks, args["block_id"])
    content = block.get("content")
    if not isinstance(content, str):
        raise ToolViolation("目标块没有可修改的文本内容")
    new_content = args["new_content"]
    if not isinstance(new_content, str) or not new_content.strip():
        raise ToolViolation("new_content 不能为空")
    if content == new_content:
        raise ToolViolation("new_content 与原文相同，无需重写")
    block["content"] = new_content

    change = ctx._find_change("document_patch", document_id=document_id, block_id=args["block_id"])
    if change is None:
        change = ctx._append_change(
            {
                "id": str(uuid.uuid4()),
                "kind": "document_patch",
                "target_id": document_id,
                "document_id": document_id,
                "block_id": args["block_id"],
                "title": ctx.document_titles.get(document_id, ""),
                "before": content,
                "after": new_content,
                "reason": args["reason"],
            }
        )
    else:
        change["after"] = new_content
        change["reason"] = args["reason"]
    return {
        "document_id": document_id,
        "block_id": args["block_id"],
        "staged_content": new_content,
        "rewrite": True,
        "change_count": len(ctx.changes),
        "complete": True,
    }


def _settings_edit_blocked(ctx: ProjectAgentContext, field: Optional[str] = None) -> Optional[dict]:
    """指令没要求改设定，或没点名这个字段时，不写入项目设定。"""
    instruction = getattr(ctx, "instruction", "") or ""
    if generation_forbids_settings_edits(instruction):
        message = (
            "本轮只按现有大纲和设定生成文章，不修改大纲或任何项目设定。"
            "请调用 generate_documents_from_settings()，完成后 finish。"
        )
    else:
        allowed = requested_setting_fields(instruction)
        if instruction_forbids_unsolicited_settings(instruction):
            message = (
                "当前指令是检查或讨论，没有要求修改项目设定。"
                "只汇报结果，不要改大纲、人物、故事线或其他设定。"
            )
        elif field and allowed and field not in allowed:
            message = (
                f"当前指令没有要求修改 {field}。只改指令点名的设定字段，然后回到原任务。"
            )
        else:
            return None
    return {
        "complete": True,
        "skipped": True,
        "change_count": len(ctx.changes),
        "message": message,
    }


def tool_propose_memory_patch(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    field = _coerce_memory_field_name(args.get("field")) or args.get("field")
    blocked = _settings_edit_blocked(ctx, field if isinstance(field, str) else None)
    if blocked:
        return blocked
    _require_project(ctx)
    # 未读过设定时自动预读，避免「忘了 read_memory」整轮失败
    if not ctx.memory_read:
        tool_read_memory(ctx, db, {})
    if field not in MEMORY_FIELDS:
        raise ToolViolation(f"设定字段不在可修改白名单: {field}。可选: {', '.join(MEMORY_FIELDS)}")
    mode = (args.get("mode") or "replace").strip().lower()
    if mode not in ("replace", "merge"):
        raise ToolViolation('mode 仅支持 "replace" 或 "merge"')

    current = ctx.staged_memory.get(field)
    baseline = json.loads(json.dumps(current, ensure_ascii=False, default=str))
    corrected = False
    before = args.get("before")
    if before is None:
        args["before"] = baseline
        corrected = True
    elif _norm(current) != _norm(before):
        # 结构化字段很长，模型回显难一致；以服务端暂存为冲突基线
        args["before"] = baseline
        corrected = True

    raw_after = args["after"]
    if mode == "merge":
        merged = merge_memory_field(field, current, raw_after)
        args["after"] = coerce_memory_field(field, merged)
    else:
        coerced = coerce_memory_field(field, raw_after)
        # 故事线若只传字符串，默认视为更新 summary，保留已有 stages（避免误清空）
        if (
            field == "storyline"
            and isinstance(raw_after, str)
            and isinstance(current, dict)
            and (current.get("stages") or [])
        ):
            coerced = {
                "summary": str((coerced or {}).get("summary") or raw_after),
                "stages": current.get("stages") or [],
            }
        args["after"] = coerced
    ctx.staged_memory[field] = args["after"]

    change = ctx._find_change("memory_patch", field=field)
    if change is None:
        change = ctx._append_change(
            {
                "id": str(uuid.uuid4()),
                "kind": "memory_patch",
                "target_id": ctx.memory_row_id,
                "field": field,
                "title": _MEMORY_FIELD_TITLES.get(field, f"项目设定 · {field}"),
                "before": args["before"],
                "after": args["after"],
                "reason": args["reason"],
                "mode": mode,
            }
        )
    else:
        # 同一字段多次补丁：before 保持首次基线，after 累积到最新
        change["after"] = args["after"]
        change["reason"] = args["reason"]
        change["mode"] = mode
    return {
        "field": field,
        "mode": mode,
        "staged_value": args["after"],
        "corrected_before": corrected,
        "change_count": len(ctx.changes),
        "complete": True,
        "message": (
            f"已暂存 {field}（{mode}）。"
            + ("合并写入完成。" if mode == "merge" else "整字段替换完成。")
        ),
    }


def tool_propose_create_document(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    _require_project(ctx)
    if looks_like_generate_documents_instruction(getattr(ctx, "instruction", "") or ""):
        raise ToolViolation(
            "根据设定生成多篇请调用 generate_documents_from_settings()，"
            "让写作模型按本项目的角色、故事线、文风和大纲逐章生成。"
            "不要把整章正文塞进 propose_create_document。"
        )
    ctx._append_change(
        {
            "id": str(uuid.uuid4()),
            "kind": "create_document",
            "target_id": None,
            "title": args["title"],
            "before": None,
            "after": {"title": args["title"], "text": args["text"]},
            "text": args["text"],
            "reason": args["reason"],
        }
    )
    return {"title": args["title"], "change_count": len(ctx.changes), "complete": True}


def tool_propose_delete_document(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """提案删除文档：仅暂存，须用户确认后才真正删除（不会自动 apply）。"""
    project_id = _require_project(ctx)
    document_id = args["document_id"]
    document = _project_document(db, project_id, document_id)
    child_count = (
        db.query(Document)
        .filter(Document.parent_id == document_id, Document.project_id == project_id)
        .count()
    )
    if child_count:
        raise ToolViolation(
            f"《{document.title or document_id}》下还有 {child_count} 个子文档，"
            "请先删除子文档，或请用户在侧栏整理后再删。"
        )
    # 同轮已有针对该文档的补丁/新建冲突时拒绝，避免半改半删
    for change in ctx.changes:
        if not isinstance(change, dict):
            continue
        kind = change.get("kind")
        if kind == "delete_document" and change.get("document_id") == document_id:
            return {
                "document_id": document_id,
                "title": document.title,
                "change_count": len(ctx.changes),
                "complete": True,
                "message": "该文档删除提案已暂存，等待用户确认。",
            }
        if kind == "document_patch" and change.get("document_id") == document_id:
            raise ToolViolation(
                f"本轮已有对文档 {document_id} 的正文修改提案，不能同时删除。"
                "请 finish 当前修改后再另开一轮删除，或取消后再删。"
            )
        if kind == "create_document" and change.get("target_id") == document_id:
            raise ToolViolation("不能删除本轮刚提案新建的文档；请取消该新建提案。")

    title = (document.title or "").strip() or f"文档 {document_id}"
    content = json.loads(json.dumps(document.content or [], ensure_ascii=False, default=str))
    ctx._append_change(
        {
            "id": str(uuid.uuid4()),
            "kind": "delete_document",
            "target_id": document_id,
            "document_id": document_id,
            "title": f"删除《{title}》",
            "before": {
                "title": document.title,
                "content": content,
                "parent_id": document.parent_id,
                "order_index": document.order_index or 0,
            },
            "after": None,
            "reason": args.get("reason") or "删除文档",
        }
    )
    # 同步标题缓存，便于后续 list 展示
    ctx.document_titles[document_id] = title
    return {
        "document_id": document_id,
        "title": title,
        "change_count": len(ctx.changes),
        "complete": True,
        "message": (
            f"已暂存删除《{title}》（document_id={document_id}）。"
            "该操作不会自动执行，须用户在对话中确认后才会删除。"
        ),
        "requires_user_confirm": True,
    }


def tool_create_project(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """即时创建项目并绑定本轮 ctx（非提案）。后续 propose_* 写入该项目。"""
    if ctx.project_id:
        raise ToolViolation(
            f"本轮已绑定 project_id={ctx.project_id}，勿重复 create_project。"
            "若要另建项目，请新开对话。"
        )
    title = (args.get("title") or "").strip()
    if not title:
        raise ToolViolation("create_project 的 title 不能为空")
    description = (args.get("description") or "").strip()
    reason = (args.get("reason") or "").strip() or "用户请求创建项目"

    from app.models.models import Project
    from app.services.ai_memory_service import AIMemoryService

    project = Project(
        title=title[:200],
        description=description[:2000] if description else None,
        owner_id=ctx.user_id,
    )
    db.add(project)
    db.flush()
    AIMemoryService.get_or_create_memory(db, project.id)
    db.commit()
    db.refresh(project)

    ctx.project_id = project.id
    ctx.scope = "system"
    ctx._append_change(
        {
            "id": str(uuid.uuid4()),
            "kind": "created_project",
            "target_id": project.id,
            "project_id": project.id,
            "title": project.title or title,
            "before": None,
            "after": {
                "project_id": project.id,
                "title": project.title,
                "description": description,
            },
            "reason": reason,
        }
    )
    return {
        "project_id": project.id,
        "title": project.title,
        "message": (
            f"已创建项目 project_id={project.id}《{project.title}》并绑定本轮。"
            "请继续专项写作或 propose_writing_draft / propose_story_settings / "
            "propose_create_document，完成后 finish。"
        ),
        "change_count": len(ctx.changes),
        "complete": True,
    }


def _store_writing_draft(ctx: ProjectAgentContext, result: Dict[str, Any]) -> dict:
    """把完整生成结果写入 ctx，observation 只回摘要 + draft_id。"""
    draft_id = writing_adapters.new_draft_id()
    kind = result.get("kind") or "writing"
    title = str(result.get("title") or "").strip()
    content = result.get("content")
    content_str = content if isinstance(content, str) else ""
    draft = {
        "draft_id": draft_id,
        "kind": kind,
        "title": title,
        "content": content_str,
        "outline": result.get("outline"),
        "story_data": result.get("story_data"),
        "meta": result.get("meta") or {},
    }
    ctx.writing_drafts[draft_id] = draft
    obs: Dict[str, Any] = {
        "draft_id": draft_id,
        "kind": kind,
        "title": title,
        "preview": writing_adapters.preview_text(content_str, _DRAFT_PREVIEW_CHARS),
        "content_chars": len(content_str),
        "message": (
            f"全文已暂存为 draft_id={draft_id}。"
            "请调用 propose_writing_draft(draft_id, reason) 写入项目文档，"
            "不要把预览当全文复制到 propose_create_document。"
        ),
        "complete": True,
    }
    if result.get("outline") is not None:
        obs["has_outline"] = True
    if result.get("story_data") is not None:
        obs["message"] = (
            f"故事设定已暂存为 draft_id={draft_id}。"
            "请调用 propose_story_settings(draft_id, reason) 拆入项目设定；"
            "如需正文可再单独写作。"
        )
        obs["has_story_data"] = True
        titles = (result.get("story_data") or {}).get("title_options") or []
        if isinstance(titles, list):
            obs["title_options"] = titles[:5]
    return obs


def _adapter_runtime_error(label: str, exc: BaseException) -> RuntimeError:
    """LLM/网络等运行时失败：勿包成 ToolViolation，避免连续失败 clear_changes。"""
    return RuntimeError(f"{label}: {exc}")


def tool_list_hot_topics(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    try:
        result = _run_async(
            writing_adapters.list_hot_topics(
                limit=args["limit"],
                category=args["category"] or None,
                refresh=bool(args["refresh"]),
            )
        )
    except Exception as exc:
        raise _adapter_runtime_error("获取热点失败", exc) from exc
    topics = result.get("topics") or []
    return {
        "kind": "hot_topics_list",
        "topics": topics,
        "count": len(topics),
        "is_fallback": result.get("is_fallback"),
        "message": result.get("message")
        or "请挑选一个话题后调用 hot_topic_write(topic_title=...)。",
        "complete": True,
        "page_hint": "/hot-topics",
    }


def tool_hot_topic_write(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    try:
        result = _run_async(
            writing_adapters.hot_topic_generate(
                topic_title=args["topic_title"],
                article_type=args["article_type"],
                word_count=args["word_count"],
                style=args["style"],
                additional_requirements=args["additional_requirements"],
            )
        )
    except Exception as exc:
        raise _adapter_runtime_error("热点写作失败", exc) from exc
    return _store_writing_draft(ctx, result)


def tool_copywriting_write(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    try:
        result = _run_async(
            writing_adapters.copywriting_generate(
                product=args["product"],
                target_audience=args["target_audience"],
                copy_objective=args["copy_objective"],
                selling_points=args["selling_points"],
                pain_points=args["pain_points"],
                evidence_cases=args["evidence_cases"],
                cta=args["cta"],
                tone=args["tone"],
                word_count=args["word_count"],
                additional_requirements=args["additional_requirements"],
            )
        )
    except Exception as exc:
        raise _adapter_runtime_error("文案生成失败", exc) from exc
    return _store_writing_draft(ctx, result)


def tool_list_brainstorm_ideas(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    try:
        result = writing_adapters.list_brainstorm_ideas(
            category=args["category"] or None,
            limit=args["limit"],
        )
    except Exception as exc:
        raise _adapter_runtime_error("获取脑洞选题失败", exc) from exc
    return {
        "kind": "brainstorm_ideas",
        "categories": result.get("categories") or [],
        "ideas": result.get("ideas") or [],
        "count": len(result.get("ideas") or []),
        "message": "请挑选一个脑洞后调用 brainstorm_write(title=..., category=..., concept=...)。",
        "complete": True,
        "page_hint": "/brainstorm-writing",
    }


def tool_brainstorm_write(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    if not (args.get("title") or args.get("concept") or "").strip():
        raise ToolViolation("brainstorm_write 需要 title 或 concept")
    try:
        result = _run_async(
            writing_adapters.brainstorm_write(
                title=args["title"],
                category=args["category"],
                concept=args["concept"],
                style=args["style"],
                word_count=args["word_count"],
            )
        )
    except Exception as exc:
        raise _adapter_runtime_error("脑洞写作失败", exc) from exc
    return _store_writing_draft(ctx, result)


def tool_story_generate(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    chapter_count = args["chapter_count"] or None
    genre = args["genre"] or None
    extra = args["additional_requirements"] or None
    try:
        result = _run_async(
            writing_adapters.story_generate(
                theme=args["theme"],
                genre=genre,
                word_count=args["word_count"],
                chapter_count=chapter_count,
                additional_requirements=extra,
            )
        )
    except Exception as exc:
        raise _adapter_runtime_error("故事设定生成失败", exc) from exc
    return _store_writing_draft(ctx, result)


def _consume_draft(ctx: ProjectAgentContext, draft_id: str) -> dict:
    draft = ctx.writing_drafts.pop(draft_id, None)
    if not draft:
        raise ToolViolation(
            f"找不到写作草稿 draft_id={draft_id}（可能已提案过），请先调用专项写作工具"
        )
    return draft


def tool_propose_writing_draft(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    _require_project(ctx)
    draft = _consume_draft(ctx, args["draft_id"])
    content = draft.get("content") or ""
    if not isinstance(content, str) or not content.strip():
        # 消费后发现无正文：把草稿放回，便于改用 propose_story_settings
        ctx.writing_drafts[args["draft_id"]] = draft
        raise ToolViolation(
            f"草稿 {args['draft_id']} 没有正文（kind={draft.get('kind')}）。"
            "故事设定请用 propose_story_settings。"
        )
    title = (args.get("title") or "").strip() or str(draft.get("title") or "未命名文稿")
    return tool_propose_create_document(
        ctx,
        db,
        {"title": title, "text": content, "reason": args["reason"]},
    )


def tool_propose_story_settings(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    blocked = _settings_edit_blocked(ctx)
    if blocked:
        return blocked
    _require_project(ctx)
    draft_id = args["draft_id"]
    draft = _consume_draft(ctx, draft_id)
    story_data = draft.get("story_data")
    if not isinstance(story_data, dict):
        ctx.writing_drafts[draft_id] = draft
        raise ToolViolation(f"草稿 {draft_id} 不含 story_data，无法写入设定")
    if not ctx.memory_read:
        tool_read_memory(ctx, db, {})
    memory_fields = writing_adapters.story_to_memory_fields(story_data)
    patched = []
    reason = args["reason"]
    for field, after in memory_fields.items():
        if field not in MEMORY_FIELDS:
            continue
        # 跳过空值，避免用空 notes/outline 覆盖已有设定
        if after is None or after == "" or after == [] or after == {}:
            continue
        before = ctx.staged_memory.get(field)
        tool_propose_memory_patch(
            ctx,
            db,
            {
                "field": field,
                "before": before,
                "after": after,
                "reason": reason,
            },
        )
        patched.append(field)
    return {
        "draft_id": draft_id,
        "patched_fields": patched,
        "change_count": len(ctx.changes),
        "complete": True,
        "message": (
            f"已将故事设定拆入提案字段：{', '.join(patched)}。"
            "注意：非空字段会替换当前暂存设定对应项。"
        ),
    }


def _outline_nodes_for_generation(ctx: ProjectAgentContext, db: Session) -> List[dict]:
    """优先用本轮暂存大纲，否则读库。故事线 stages 仅在没有大纲时兜底。"""
    outline = ctx.staged_memory.get("outline") if isinstance(ctx.staged_memory, dict) else None
    if not isinstance(outline, list) or not outline:
        memory = db.query(AIMemory).filter(AIMemory.project_id == ctx.project_id).first()
        outline = memory.outline if memory is not None else None
    nodes: List[dict] = []
    if isinstance(outline, list):
        for item in outline:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            nodes.append({
                "title": title,
                "description": str(item.get("description") or item.get("summary") or "").strip(),
            })
    if nodes:
        return nodes[:12]
    storyline = ctx.staged_memory.get("storyline") if isinstance(ctx.staged_memory, dict) else None
    if not isinstance(storyline, dict):
        memory = db.query(AIMemory).filter(AIMemory.project_id == ctx.project_id).first()
        storyline = memory.storyline if memory is not None else None
    stages = storyline.get("stages") if isinstance(storyline, dict) else None
    if isinstance(stages, list):
        for item in stages:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            nodes.append({
                "title": title,
                "description": str(item.get("summary") or item.get("description") or "").strip(),
            })
    return nodes[:12]


def _project_rules_for_chapter(
    ctx: ProjectAgentContext,
    *,
    node: dict,
    index: int,
    total: int,
    previous_summary: str,
    custom_instruction: str,
) -> str:
    """把项目设定收成写作约束。冲突时以本轮暂存设定为准。"""
    lines = [
        "写这一章时必须符合本项目的规则，由你按这些规则成文，不要另起一套设定：",
        "- 人物使用设定中的姓名、关系、性格和目标，不要换名，不要改已写明的感情走向。",
        "- 只写当前这一章，情节落在大纲和故事线的对应位置，不要跳写后文章节，不要推翻已定结局。",
        "- 文风遵循项目写作风格；有文风智能体时以该智能体为准。",
        "- 世界观、关键情节点和备注中的限制同样生效。",
        f"- 这是第 {index + 1}/{total} 章「{node.get('title') or ''}」。",
    ]
    if node.get("description"):
        lines.append(f"- 本章要完成：{node['description']}")
    staged = ctx.staged_memory if isinstance(ctx.staged_memory, dict) else {}
    bits = []
    for field, label in (
        ("characters", "角色"),
        ("storyline", "故事线"),
        ("outline", "大纲"),
        ("world_building", "世界观"),
        ("writing_style", "文风"),
        ("key_points", "情节点"),
        ("notes", "备注"),
    ):
        value = staged.get(field)
        if value in (None, "", [], {}):
            continue
        try:
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)
        text = text.strip()
        if not text:
            continue
        if len(text) > 1200:
            text = text[:1200] + "…"
        bits.append(f"【{label}】{text}")
    if bits:
        lines.append("本轮项目设定（与旧稿冲突时以这里为准）：")
        lines.extend(bits)
    if previous_summary:
        lines.append("上一章结尾，本章需接上，不要重写上一章：")
        lines.append(previous_summary[:500])
    if custom_instruction:
        lines.append("用户本轮的额外要求（不能违背上面的项目规则）：")
        lines.append(custom_instruction)
    return "\n".join(lines)


async def _generate_one_chapter_text(
    db: Session,
    *,
    project_id: int,
    document_id: int,
    node: dict,
    index: int,
    total: int,
    max_tokens: int,
    custom_instruction: str,
    user_id: Optional[int] = None,
) -> str:
    """复用设定页「创建文章」的 batch_generate：模型按项目设定写本章。"""
    from app.services.ai_writing_service import AIWritingService

    content = ""
    streamed = ""
    error = ""
    async for raw in AIWritingService.batch_generate(
        db,
        project_id=project_id,
        document_id=document_id,
        outline_nodes=[node],
        max_tokens_per_chapter=max_tokens,
        continue_on_complete=False,
        custom_instruction=custom_instruction,
        user_id=user_id,
        style_agent_id=None,
    ):
        try:
            event = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "error":
            error = event.get("error_message") or event.get("message") or "生成失败"
        elif event.get("type") == "chapter_complete" and event.get("chapter_content"):
            content = str(event.get("chapter_content") or "")
        elif event.get("type") == "content" and event.get("content") and not content:
            streamed += str(event.get("content") or "")
    if error and not content:
        raise ToolViolation(error)
    return (content or streamed).strip()


async def generate_documents_from_settings(
    session_factory,
    ctx: ProjectAgentContext,
    args: Dict[str, Any],
    on_progress=None,
) -> dict:
    """按大纲逐篇调用既有生成接口并落库。正文不返回给模型。"""
    project_id = _require_project(ctx)
    max_tokens = int(args.get("max_tokens_per_chapter") or 4000)
    max_tokens = max(800, min(max_tokens, 8000))
    custom = str(args.get("custom_instruction") or "").strip()
    with session_factory() as db:
        nodes = _outline_nodes_for_generation(ctx, db)
    if not nodes:
        raise ToolViolation("项目大纲为空。请先把章节标题写入 outline，再生成多篇。")

    from app.utils.document_format import parse_formatted_text_to_blocks

    created: List[dict] = []
    failed: List[dict] = []
    total = len(nodes)
    previous_summary = ""
    for index, node in enumerate(nodes):
        title = node["title"]
        if on_progress:
            on_progress(f"按项目规则生成 {index + 1}/{total}：{title}")
        rules = _project_rules_for_chapter(
            ctx,
            node=node,
            index=index,
            total=total,
            previous_summary=previous_summary,
            custom_instruction=custom,
        )
        with session_factory() as db:
            max_order = (
                db.query(Document)
                .filter(Document.project_id == project_id)
                .order_by(Document.order_index.desc())
                .first()
            )
            document = Document(
                project_id=project_id,
                title=title,
                content=[],
                parent_id=None,
                order_index=(max_order.order_index + 1) if max_order and max_order.order_index is not None else index,
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            doc_id = document.id
            try:
                text = await _generate_one_chapter_text(
                    db,
                    project_id=project_id,
                    document_id=doc_id,
                    node=node,
                    index=index,
                    total=total,
                    max_tokens=max_tokens,
                    custom_instruction=rules,
                    user_id=ctx.user_id,
                )
            except Exception as exc:
                from app.services.document_service import delete_document_with_dependents
                delete_document_with_dependents(db, document)
                db.commit()
                failed.append({"title": title, "error": str(exc)[:200]})
                continue
            if not text or text.startswith("[错误]") or text.startswith("[配置错误]"):
                from app.services.document_service import delete_document_with_dependents
                delete_document_with_dependents(db, document)
                db.commit()
                failed.append({"title": title, "error": (text or "未生成到有效内容")[:200]})
                continue
            blocks = parse_formatted_text_to_blocks(text, f"gen{doc_id}")
            if not blocks or blocks[0].get("type") not in ("heading", "subheading"):
                blocks.insert(0, {
                    "id": f"gen-title-{doc_id}",
                    "type": "heading",
                    "content": title,
                    "props": {"level": 2},
                })
            document.content = blocks
            db.commit()
        previous_summary = text.replace("\n", " ")[:400]
        preview = previous_summary[:80]
        ctx._append_change({
            "id": str(uuid.uuid4()),
            "kind": "create_document",
            "target_id": doc_id,
            "title": title,
            "before": None,
            "after": {"title": title, "text": preview},
            "reason": "根据设定生成",
        })
        created.append({"document_id": doc_id, "title": title, "chars": len(text)})

    if not created and failed:
        raise ToolViolation("多篇生成均未成功：" + "；".join(
            f"{item['title']}：{item['error']}" for item in failed[:4]
        ))
    return {
        "complete": True,
        "created": created,
        "failed": failed,
        "change_count": len(ctx.changes),
        "message": (
            f"已按项目的角色、故事线、文风和大纲生成 {len(created)} 篇。"
            + (f" {len(failed)} 篇失败，可再说「继续生成剩下的」。" if failed else "")
            + "正文在文档里，不要再把全文复制进对话。请 finish 列出篇名。"
        ),
    }


def tool_generate_documents_from_settings(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """同步入口（测试 / execute_tool）。执行循环改走异步版本，避免长生成占住租约。"""
    return _run_async(_generate_documents_on_session(ctx, db, args))


async def _generate_documents_on_session(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    """给已有 Session 用：测试里没有独立 sessionmaker 时走这条。"""
    class _Factory:
        def __call__(self):
            return _SessionGuard(db)

    return await generate_documents_from_settings(_Factory(), ctx, args)


class _SessionGuard:
    """让已有 Session 兼容 `with session_factory() as db`，且不在退出时关闭。"""

    def __init__(self, db: Session):
        self._db = db

    def __enter__(self):
        return self._db

    def __exit__(self, exc_type, exc, tb):
        return False


def tool_finish(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    answer = args.get("answer") if isinstance(args, dict) else ""
    if not isinstance(answer, str):
        answer = str(answer) if answer is not None else ""
    ctx.finish_answer = answer
    return {"answer": answer, "complete": True}


TOOLS = {
    "list_project": tool_list_project,
    "document_map": tool_document_map,
    "digest_document": tool_digest_document,
    "read_document": tool_read_document,
    "read_memory": tool_read_memory,
    "search_project": tool_search_project,
    "propose_document_patch": tool_propose_document_patch,
    "propose_block_rewrite": tool_propose_block_rewrite,
    "propose_memory_patch": tool_propose_memory_patch,
    "propose_create_document": tool_propose_create_document,
    "generate_documents_from_settings": tool_generate_documents_from_settings,
    "propose_delete_document": tool_propose_delete_document,
    "create_project": tool_create_project,
    "list_hot_topics": tool_list_hot_topics,
    "hot_topic_write": tool_hot_topic_write,
    "copywriting_write": tool_copywriting_write,
    "list_brainstorm_ideas": tool_list_brainstorm_ideas,
    "brainstorm_write": tool_brainstorm_write,
    "story_generate": tool_story_generate,
    "propose_writing_draft": tool_propose_writing_draft,
    "propose_story_settings": tool_propose_story_settings,
    "finish": tool_finish,
}


_MEMORY_FIELD_ALIASES = {
    "关键情节点": "key_points",
    "情节点": "key_points",
    "要点": "key_points",
    "keypoints": "key_points",
    "keypoint": "key_points",
    "人物": "characters",
    "角色": "characters",
    "人物设定": "characters",
    "角色设定": "characters",
    "故事线": "storyline",
    "剧情": "storyline",
    "大纲": "outline",
    "世界观": "world_building",
    "世界设定": "world_building",
    "文风": "writing_style",
    "备注": "notes",
}


def _coerce_memory_field_name(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    key = raw.strip()
    if not key:
        return None
    if key in MEMORY_FIELDS:
        return key
    lowered = key.lower().replace("-", "_").replace(" ", "")
    if lowered in MEMORY_FIELDS:
        return lowered
    return _MEMORY_FIELD_ALIASES.get(key) or _MEMORY_FIELD_ALIASES.get(lowered)


def _infer_memory_field_from_after(after: Any) -> Optional[str]:
    """根据 after 结构猜测设定字段（模型常漏 field，但 after 形态很典型）。"""
    if isinstance(after, list) and after:
        sample = next((x for x in after if isinstance(x, dict)), None)
        if isinstance(sample, dict):
            keys = {str(k).lower() for k in sample.keys()}
            if "name" in keys and keys & {"description", "role", "personality", "background"}:
                return "characters"
            # 文章大纲：章节标题 + 简述
            if "title" in keys and "description" in keys and "name" not in keys:
                return "outline"
            # 关键情节点：标题 + summary
            if "title" in keys and keys & {"summary", "point"} and "description" not in keys:
                return "key_points"
            if keys & {"act", "beat", "chapter", "arc"}:
                return "outline"
        return None
    return None


_MEMORY_FIELD_TITLES = {
    "outline": "文章大纲",
    "storyline": "故事线",
    "characters": "人物设定",
    "world_building": "世界观",
    "writing_style": "文风",
    "key_points": "关键情节点",
    "notes": "备注",
}


def _fill_memory_patch_args(ctx: ProjectAgentContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """补全 propose_memory_patch 漏传的 field（别名 / 队列 / after 形态 / before 唯一对齐）。"""
    out = dict(args)
    coerced = _coerce_memory_field_name(out.get("field"))
    if coerced:
        out["field"] = coerced
        return out

    step = current_phase(ctx)
    if step and step.get("kind") == "propose_memory_patch":
        plan_field = _coerce_memory_field_name(step.get("field"))
        if plan_field:
            out["field"] = plan_field
            return out

    # after 形态优先于 before 对齐：空 outline/key_points 占位常规范化成相同结构，易误匹配
    inferred = _infer_memory_field_from_after(out.get("after"))
    if inferred:
        out["field"] = inferred
        return out

    if ctx.memory_read and "before" in out:
        matches = [
            field
            for field in MEMORY_FIELDS
            if _norm(ctx.staged_memory.get(field)) == _norm(out.get("before"))
        ]
        if len(matches) == 1:
            out["field"] = matches[0]
            return out

    # 清掉无效 field，让校验给出明确错误
    if "field" in out and not coerced:
        out.pop("field", None)
    return out


def execute_tool(ctx: ProjectAgentContext, db: Session, tool: str, args: Any) -> dict:
    """统一入口：白名单 + 参数校验 + 执行。校验失败抛 ToolViolation。"""
    if not isinstance(tool, str) or tool not in TOOLS:
        raise ToolViolation(f"未知工具: {tool}")
    if tool == "propose_memory_patch" and isinstance(args, dict):
        args = _fill_memory_patch_args(ctx, args)
    resolved = _validate_args(tool, args)
    oversized = check_propose_payload_size(tool, resolved)
    if oversized:
        enable_narrow_mode(ctx)
        raise ToolViolation(oversized)
    return TOOLS[tool](ctx, db, resolved)
