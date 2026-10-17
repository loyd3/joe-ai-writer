"""
项目智能体工具层：白名单校验、暂存修改集（ChangeSet）与全文覆盖检查。

模型只能调用这里登记的工具；每次调用都经过参数精确集合校验、类型校验、
越权校验与「先读后改」校验。所有修改只作用于内存暂存（ctx），
不写库——直到用户在 transition('apply') 确认后由 service 原子发布。
"""
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import AIMemory, Document


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


def _int(v):
    """int 参数校验：显式拒绝 bool（bool 是 int 子类，True 会误通过）。"""
    return isinstance(v, int) and not isinstance(v, bool)


def _str(v):
    return isinstance(v, str)


def _any(v):
    return True


_ARG_SPECS: Dict[str, Dict[str, Any]] = {
    "list_project": {},
    "read_document": {"document_id": (_int, _REQUIRED), "offset": (_int, 0), "limit": (_int, 50)},
    "read_memory": {},
    "search_project": {"query": (_str, _REQUIRED), "offset": (_int, 0), "limit": (_int, 10)},
    "propose_document_patch": {
        "document_id": (_int, _REQUIRED),
        "block_id": (_str, _REQUIRED),
        "old_text": (_str, _REQUIRED),
        "new_text": (_str, _REQUIRED),
        "reason": (_str, _REQUIRED),
    },
    "propose_memory_patch": {
        "field": (_str, _REQUIRED),
        "before": (_any, _REQUIRED),
        "after": (_any, _REQUIRED),
        "reason": (_str, _REQUIRED),
    },
    "propose_create_document": {
        "title": (_str, _REQUIRED),
        "text": (_str, _REQUIRED),
        "reason": (_str, _REQUIRED),
    },
    "finish": {"answer": (_str, _REQUIRED)},
}


def _validate_args(tool: str, args: Any) -> Dict[str, Any]:
    if not isinstance(args, dict):
        raise ToolViolation(f"工具 {tool} 的参数必须是对象")
    spec = _ARG_SPECS.get(tool)
    if spec is None:
        raise ToolViolation(f"未知工具: {tool}")
    extra = set(args) - set(spec)
    if extra:
        raise ToolViolation(f"工具 {tool} 不支持参数: {sorted(extra)}")
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
    # 分页参数夹紧到安全范围
    for name in ("offset", "limit"):
        if name in resolved:
            resolved[name] = max(0, min(int(resolved[name]), 1000 if name == "limit" else 10**9))
    if "limit" in resolved and resolved["limit"] == 0:
        resolved["limit"] = 1
    return resolved


def _norm(value: Any) -> str:
    """跨类型稳定比较：JSON 结构按序序列化，其余转字符串。"""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if value is None:
        return "∅"
    return str(value)


class ProjectAgentContext:
    """一次 run 的执行上下文：已读暂存 + 修改集累积。全程内存态，不写库。"""

    def __init__(self, project_id: int, user_id: int):
        self.project_id = project_id
        self.user_id = user_id
        self.read_documents: Dict[int, List[dict]] = {}  # doc_id -> 暂存块（深拷贝）
        self.document_titles: Dict[int, str] = {}
        self.memory_read = False
        self.staged_memory: Dict[str, Any] = {}
        self.memory_row_id: Optional[int] = None
        self.changes: List[dict] = []
        self.finish_answer: Optional[str] = None

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
    documents = (
        db.query(Document.id, Document.title, Document.order_index)
        .filter(Document.project_id == ctx.project_id)
        .order_by(Document.order_index.asc(), Document.id.asc())
        .all()
    )
    return {
        "project_id": ctx.project_id,
        "documents": [
            {"document_id": d.id, "title": d.title, "order_index": d.order_index} for d in documents
        ],
        "memory_fields": list(MEMORY_FIELDS),
        "complete": True,
    }


def tool_read_document(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    document = _project_document(db, ctx.project_id, args["document_id"])
    blocks = [b for b in (document.content or []) if isinstance(b, dict)]
    ctx.read_documents[document.id] = json.loads(json.dumps(blocks, ensure_ascii=False))
    ctx.document_titles[document.id] = document.title or ""
    offset, limit = args["offset"], args["limit"]
    page = blocks[offset : offset + limit]
    return {
        "document_id": document.id,
        "title": document.title,
        "total_blocks": len(blocks),
        "offset": offset,
        "limit": limit,
        "complete": offset + limit >= len(blocks),
        "blocks": [
            {"id": b.get("id"), "type": b.get("type"), "content": b.get("content")} for b in page
        ],
    }


def tool_read_memory(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    memory = db.query(AIMemory).filter(AIMemory.project_id == ctx.project_id).first()
    ctx.memory_read = True
    ctx.staged_memory = {
        field: json.loads(json.dumps(getattr(memory, field), ensure_ascii=False, default=str))
        if getattr(memory, field) is not None
        else None
        for field in MEMORY_FIELDS
    }
    ctx.memory_row_id = memory.id if memory else None
    return {
        "memory_id": ctx.memory_row_id,
        "fields": ctx.staged_memory,
        "coverage": "project_memory_literal",
        "complete": True,
    }


def tool_search_project(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    query = args["query"].lower()
    matches: List[dict] = []
    documents = (
        db.query(Document)
        .filter(Document.project_id == ctx.project_id)
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
    memory = db.query(AIMemory).filter(AIMemory.project_id == ctx.project_id).first()
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


def tool_propose_memory_patch(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    if not ctx.memory_read:
        raise ToolViolation("须先 read_memory 读取设定后才能提出补丁")
    field = args["field"]
    if field not in MEMORY_FIELDS:
        raise ToolViolation(f"设定字段不在可修改白名单: {field}")
    if _norm(ctx.staged_memory.get(field)) != _norm(args["before"]):
        raise ToolViolation(f"before 与设定当前值不一致（字段 {field}）")
    ctx.staged_memory[field] = args["after"]

    change = ctx._find_change("memory_patch", field=field)
    if change is None:
        change = ctx._append_change(
            {
                "id": str(uuid.uuid4()),
                "kind": "memory_patch",
                "target_id": ctx.memory_row_id,
                "field": field,
                "title": "项目设定",
                "before": args["before"],
                "after": args["after"],
                "reason": args["reason"],
            }
        )
    else:
        change["after"] = args["after"]
        change["reason"] = args["reason"]
    return {
        "field": field,
        "staged_value": args["after"],
        "change_count": len(ctx.changes),
        "complete": True,
    }


def tool_propose_create_document(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
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


def tool_finish(ctx: ProjectAgentContext, db: Session, args: Dict[str, Any]) -> dict:
    ctx.finish_answer = args["answer"]
    return {"answer": args["answer"], "complete": True}


TOOLS = {
    "list_project": tool_list_project,
    "read_document": tool_read_document,
    "read_memory": tool_read_memory,
    "search_project": tool_search_project,
    "propose_document_patch": tool_propose_document_patch,
    "propose_memory_patch": tool_propose_memory_patch,
    "propose_create_document": tool_propose_create_document,
    "finish": tool_finish,
}


def execute_tool(ctx: ProjectAgentContext, db: Session, tool: str, args: Any) -> dict:
    """统一入口：白名单 + 参数校验 + 执行。校验失败抛 ToolViolation。"""
    if not isinstance(tool, str) or tool not in TOOLS:
        raise ToolViolation(f"未知工具: {tool}")
    resolved = _validate_args(tool, args)
    return TOOLS[tool](ctx, db, resolved)
