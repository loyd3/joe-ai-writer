"""复杂指令的后台分步编排：推断工作队列，每轮只推进当前一步，降低 JSON 截断概率。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# 单次提案体积上限（序列化后字符数）；超出由工具拒绝并要求拆分
MAX_MEMORY_PATCH_CHARS = 5500
MAX_CREATE_DOCUMENT_CHARS = 4500
MAX_BLOCK_REWRITE_CHARS = 5000

_COMPLEX_RE = re.compile(
    r"(丰富|深化|扩展|扩充|补充|完善|加入|新增|还要|以及|同时|并且|"
    r"人设|角色|人物|冲突|感情|暗涌|转折|故事线|大纲|世界观|"
    r"章节|新章|续写|扩写|多章|设定字段|全面)",
    re.I,
)

# 设定字段 → 用户话术线索（按执行优先级）
_FIELD_HINTS = [
    ("characters", r"人设|角色|人物|characters|闺蜜|竞争|配角"),
    ("storyline", r"故事线|剧情|冲突|感情|暗涌|转折|storyline"),
    ("outline", r"大纲|outline|结构"),
    ("world_building", r"世界观|世界设定|world"),
    ("key_points", r"要点|关键点|key_points"),
    ("writing_style", r"文风|文笔|writing_style"),
    ("notes", r"备注|notes|补充说明"),
]


def looks_complex_instruction(instruction: str) -> bool:
    text = (instruction or "").strip()
    if len(text) >= 80:
        return True
    hits = _COMPLEX_RE.findall(text)
    return len(hits) >= 2


def infer_work_plan(instruction: str) -> List[Dict[str, Any]]:
    """从用户指令推断分步队列。简单任务返回空列表（不启用编排）。"""
    text = (instruction or "").strip()
    if not looks_complex_instruction(text):
        return []

    steps: List[Dict[str, Any]] = [
        {
            "id": "read_memory",
            "kind": "read_memory",
            "hint": "先调用 read_memory，了解当前设定后再改。",
        }
    ]

    matched_fields = []
    for field, pattern in _FIELD_HINTS:
        if re.search(pattern, text, re.I):
            matched_fields.append(field)
    # 泛化「丰富设定」但未点名字段时，默认先人设再故事线
    if not matched_fields and re.search(r"设定|丰富|深化|扩展", text):
        matched_fields = ["characters", "storyline"]

    for field in matched_fields:
        steps.append(
            {
                "id": f"mem_{field}",
                "kind": "propose_memory_patch",
                "field": field,
                "hint": (
                    f"本步只调用 propose_memory_patch(field=\"{field}\", mode=\"merge\", after=改动项)；"
                    f"before 可省略；不要改其他 field，不要新建文档。"
                ),
            }
        )

    if re.search(r"章节|新章|新建.*章|续写|扩写|写一章|写两章|多章", text):
        steps.append(
            {
                "id": "create_chapter",
                "kind": "propose_create_document",
                "hint": (
                    "本步只 propose_create_document 一篇短章大纲（建议 ≤800 字），"
                    "不要一次写多章或超长正文；需要再扩写可下一轮继续。"
                ),
            }
        )

    # 至少要有「读 + 一步改」，否则不算复杂编排
    if len(steps) < 2:
        return []
    return steps


def work_plan_system_note(plan: List[Dict[str, Any]]) -> str:
    lines = [
        "【后台分步编排已启用】用户目标较复杂。请严格按队列逐步执行，每轮只做一个工具动作。",
        "禁止把多字段设定或长章节塞进同一次 JSON（极易截断失败）。",
        "队列如下：",
    ]
    for i, step in enumerate(plan, 1):
        field = step.get("field")
        extra = f" field={field}" if field else ""
        lines.append(f"{i}. [{step['kind']}{extra}] {step['hint']}")
    lines.append("完成当前步后再进入下一步；全部完成后 finish 用中文总结改了什么。")
    return "\n".join(lines)


def current_phase(ctx) -> Optional[Dict[str, Any]]:
    plan = getattr(ctx, "work_plan", None) or []
    idx = int(getattr(ctx, "work_plan_index", 0) or 0)
    if not plan or idx >= len(plan):
        return None
    return plan[idx]


def current_phase_nudge(ctx) -> Optional[str]:
    step = current_phase(ctx)
    if not step:
        return None
    idx = int(getattr(ctx, "work_plan_index", 0) or 0)
    total = len(ctx.work_plan)
    narrow = bool(getattr(ctx, "narrow_mode", False))
    head = f"【当前步骤 {idx + 1}/{total}】"
    if narrow:
        head = "【窄化模式·防截断】" + head
    return f"{head}{step['hint']} 本轮只做这一步，做完等观察返回后再继续。"


def advance_work_plan(ctx, tool: str, args: Optional[Dict[str, Any]] = None) -> bool:
    """工具成功后尝试推进队列。返回是否发生推进。"""
    plan = getattr(ctx, "work_plan", None) or []
    if not plan:
        return False
    step = current_phase(ctx)
    if not step:
        return False
    args = args or {}
    kind = step.get("kind")
    if tool != kind:
        return False
    if kind == "propose_memory_patch":
        expected = step.get("field")
        if expected and args.get("field") != expected:
            return False
    ctx.work_plan_index = int(getattr(ctx, "work_plan_index", 0) or 0) + 1
    return True


def enable_narrow_mode(ctx) -> None:
    """截断/过大提案后：收紧为「只做当前一步」，并确保队列仍指向未完成项。"""
    ctx.narrow_mode = True
    plan = getattr(ctx, "work_plan", None) or []
    if not plan:
        # 无预设队列时，给一个最小安全队列
        ctx.work_plan = [
            {
                "id": "mem_one",
                "kind": "propose_memory_patch",
                "hint": "只改 1 个设定 field；after 精简，不要塞满全文。",
            }
        ]
        ctx.work_plan_index = 0


def payload_too_large_message(kind: str, size: int, limit: int) -> str:
    return (
        f"{kind} 提案过大（约 {size} 字，上限 {limit}）。"
        "请拆成更小的补丁后重试：设定每次只改 1 个 field 且精简 after；"
        "新建章节先写短大纲；整块改写控制篇幅。"
    )


def check_propose_payload_size(tool: str, args: Dict[str, Any]) -> Optional[str]:
    """超限返回错误文案；通过返回 None。"""
    if tool == "propose_memory_patch":
        try:
            import json

            blob = json.dumps(args.get("after"), ensure_ascii=False, default=str)
        except Exception:
            blob = str(args.get("after") or "")
        if len(blob) > MAX_MEMORY_PATCH_CHARS:
            return payload_too_large_message("设定", len(blob), MAX_MEMORY_PATCH_CHARS)
    elif tool == "propose_create_document":
        text = args.get("text") or ""
        if isinstance(text, str) and len(text) > MAX_CREATE_DOCUMENT_CHARS:
            return payload_too_large_message("新建文档", len(text), MAX_CREATE_DOCUMENT_CHARS)
    elif tool == "propose_block_rewrite":
        content = args.get("new_content") or ""
        if isinstance(content, str) and len(content) > MAX_BLOCK_REWRITE_CHARS:
            return payload_too_large_message("整块改写", len(content), MAX_BLOCK_REWRITE_CHARS)
    return None
