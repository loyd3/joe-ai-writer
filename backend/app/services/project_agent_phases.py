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
    r"章节|新章|续写|扩写|多章|设定字段|全面|"
    r"梳理|对照|整理|重排|重构|对齐)",
    re.I,
)

# 「通读全部章节再梳理」类意图：只编排设定字段，禁止读完全部正文
_REORG_RE = re.compile(
    r"(梳理|对照|整理|重排|重构|对齐).{0,12}(故事线|大纲|章节|设定)|"
    r"(故事线|大纲).{0,12}(梳理|对照|整理|重排)|"
    r"(全部|所有|每一).{0,6}(章节|文档).{0,8}(读|过一遍|梳理)|"
    r"读一遍.{0,8}(章节|文档|storyline|outline)",
    re.I,
)

# 长篇/多章体检：走 map → digest → 设定，而不是通读
_LONG_CORPUS_RE = re.compile(
    r"(全书|全稿|长篇|多章|各章|每一章|所有章节|整本|整部|上下卷|"
    r"consistency|连贯|前后矛盾|伏笔|人设崩)",
    re.I,
)

# 设定字段 → 用户话术线索（按执行优先级）
_FIELD_HINTS = [
    ("characters", r"人设|角色|人物|characters|闺蜜|竞争|配角"),
    ("storyline", r"故事线|剧情|冲突|感情|暗涌|转折|storyline"),
    ("outline", r"文章大纲|章节大纲|章节结构|修改大纲|outline|大纲"),
    ("world_building", r"世界观|世界设定|world"),
    ("key_points", r"关键情节|情节点|要点|关键点|key_points"),
    ("writing_style", r"文风|文笔|writing_style"),
    ("notes", r"备注|notes|补充说明"),
]


def looks_complex_instruction(instruction: str) -> bool:
    text = (instruction or "").strip()
    if len(text) >= 80:
        return True
    hits = _COMPLEX_RE.findall(text)
    return len(hits) >= 2


def looks_like_reorg_instruction(instruction: str) -> bool:
    """梳理/对照故事线或「读完全部章节」类请求。"""
    return bool(_REORG_RE.search(instruction or ""))


_GENERATE_DOCS_RE = re.compile(
    r"(根据|按|用|依照).{0,8}(设定|大纲|故事线).{0,16}(生成|写成|写).{0,12}"
    r"(多篇|多章|各章|全部|所有|几篇|文章|正文|章节|稿)|"
    r"(多篇|多章|各章|每一章|所有章节|全部章节).{0,10}(生成|写成|写出来|写完)|"
    r"(生成|写成).{0,8}(多篇|多章|各章|各篇文章)|"
    r"(根据|按|依照)大纲.{0,12}(生成|写)",
    re.I,
)

# 用户明确要求改设定时才允许写入；「根据大纲生成」不算改大纲
_SETTINGS_EDIT_RE = re.compile(
    r"(修改|更新|调整|完善|补充|改一下|重写|梳理|整理|丰富|深化|扩写设定|写入|保存|改成|换成).{0,12}"
    r"(设定|大纲|人设|角色|人物|故事线|世界观|文风|要点|备注|记忆|"
    r"storyline|outline|characters|world)",
    re.I,
)


def looks_like_generate_documents_instruction(instruction: str) -> bool:
    """根据大纲/设定生成文章：只写正文，不改项目设定。"""
    return bool(_GENERATE_DOCS_RE.search(instruction or ""))


def looks_like_settings_edit_instruction(instruction: str) -> bool:
    """用户点名要改大纲或项目设定。"""
    return bool(_SETTINGS_EDIT_RE.search(instruction or ""))


def requested_setting_fields(instruction: str) -> Optional[List[str]]:
    """当前指令允许写入的设定字段。

    None：没有点名要改设定。
    空列表：要求改设定但没点名字段，由模型选一个相关字段。
    非空：只能改这些字段。
    """
    text = instruction or ""
    if not looks_like_settings_edit_instruction(text):
        return None
    fields: List[str] = []
    for field, pattern in _FIELD_HINTS:
        if field == "outline":
            named = re.search(
                r"文章大纲|章节大纲|章节结构|修改大纲|调整大纲|完善大纲|更新大纲|重写大纲|outline",
                text,
                re.I,
            )
            bare = re.search(r"大纲", text) and not re.search(r"(根据|按|用|依照)大纲", text)
            if named or bare:
                fields.append(field)
            continue
        if re.search(pattern, text, re.I):
            fields.append(field)
    return fields


_CHECK_ONLY_RE = re.compile(r"(检查|看看|是否矛盾|讨论一下|只看|先别改)", re.I)


def instruction_forbids_unsolicited_settings(instruction: str) -> bool:
    """检查、讨论类指令没有要求改设定时，禁止写入。"""
    text = instruction or ""
    if looks_like_settings_edit_instruction(text) or looks_like_generate_documents_instruction(text):
        return False
    return bool(_CHECK_ONLY_RE.search(text))


def generation_forbids_settings_edits(instruction: str) -> bool:
    """按大纲/设定生成文章，且没有同时要求改设定。"""
    text = instruction or ""
    return looks_like_generate_documents_instruction(text) and not looks_like_settings_edit_instruction(text)


def looks_like_long_corpus_instruction(instruction: str) -> bool:
    """全书/多章体检类请求。"""
    return bool(_LONG_CORPUS_RE.search(instruction or ""))


def infer_work_plan(instruction: str) -> List[Dict[str, Any]]:
    """从用户指令推断分步队列。简单任务返回空列表（不启用编排）。"""
    text = (instruction or "").strip()
    generate_step = {
        "id": "generate_docs",
        "kind": "generate_documents_from_settings",
        "hint": (
            "只调用 generate_documents_from_settings() 生成文章，然后 finish。"
            "不要 propose_memory_patch，不要改大纲、人物、故事线、世界观或任何项目设定。"
            "每一章按现有设定来写，正文不要写进本轮对话。"
        ),
    }
    if generation_forbids_settings_edits(text):
        return [generate_step]
    if (
        not looks_complex_instruction(text)
        and not looks_like_reorg_instruction(text)
        and not looks_like_long_corpus_instruction(text)
    ):
        return []

    # 长篇体检：只检查。用户没要求改设定时，不要顺手写回故事线或大纲
    if looks_like_long_corpus_instruction(text) and not looks_like_reorg_instruction(text):
        steps = [
            {
                "id": "document_map",
                "kind": "document_map",
                "hint": (
                    "先 document_map() 拿全项目目录（标题/字数/headings）。"
                    "不要 read_document 通读。"
                ),
            },
            {
                "id": "digest_key_docs",
                "kind": "digest_document",
                "hint": (
                    "对本轮最关键的 1 篇调用 digest_document(document_id)；"
                    "需要多篇就分多轮各 digest 一次。禁止把全文读进对话。"
                ),
            },
        ]
        fields = requested_setting_fields(text) or []
        if fields:
            for field in fields:
                steps.append(_memory_step(field))
        else:
            steps.append(
                {
                    "id": "report_only",
                    "kind": "finish",
                    "hint": "只汇报检查结果。不要 propose_memory_patch，不要改大纲或正文，然后 finish。",
                }
            )
        return steps

    # 梳理/对照：目录可选 + 设定字段，禁止「先读完全部章节」
    if looks_like_reorg_instruction(text):
        steps: List[Dict[str, Any]] = [
            {
                "id": "document_map",
                "kind": "document_map",
                "hint": (
                    "可先 document_map() 看章节目录与字数；"
                    "禁止 read_document 通读全部章节正文。"
                ),
            },
            {
                "id": "read_memory",
                "kind": "read_memory",
                "hint": (
                    "设定概览若已预读可跳过；否则 read_memory(field=\"storyline\") 或 "
                    "read_memory(field=\"outline\")。"
                ),
            },
        ]
        for field in requested_setting_fields(text) or []:
            steps.append(_memory_step(field))
        if not any(step.get("kind") == "propose_memory_patch" for step in steps):
            steps.append(
                {
                    "id": "report_only",
                    "kind": "finish",
                    "hint": "指令只要求梳理或对照。只说明结果，不要改未点名的设定或正文，然后 finish。",
                }
            )
        return steps

    steps = [
        {
            "id": "read_memory",
            "kind": "read_memory",
            "hint": "先调用 read_memory，了解当前设定后再改。",
        }
    ]

    matched_fields = list(requested_setting_fields(text) or [])
    # 「丰富设定」但没点名字段时，只做人设和故事线，不扩散到大纲等其余字段
    if not matched_fields and looks_like_settings_edit_instruction(text):
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

    if re.search(r"新章|新建.{0,4}章|续写|写一章|写两章|再写.{0,6}章", text):
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

    if looks_like_generate_documents_instruction(text):
        steps.append(generate_step)

    # 至少要有「读 + 一步改」，否则不算复杂编排
    if len(steps) < 2:
        return []
    return steps


def looks_like_read_all_plan(text: str) -> bool:
    """模型口头计划「通读全部章节 / 先读完整 storyline」——需立刻打断。"""
    return bool(
        re.search(
            r"(全部|所有|每一).{0,8}(章节|文档).{0,12}(读|过一遍|梳理)|"
            r"(先|我会|我先).{0,8}(把|将)?.{0,8}(storyline|outline|章节|文档).{0,16}"
            r"(读一遍|通读|全部读)|"
            r"读一遍.{0,12}(再|然后).{0,8}(梳理|对照|整理)|"
            r"(先|再).{0,6}读.{0,8}(storyline|outline|故事线|大纲).{0,8}(完整|全文|全部)|"
            r"(完整|全文).{0,8}(storyline|outline|故事线|大纲)",
            text or "",
            re.I,
        )
    )


def _memory_step(field: str) -> Dict[str, Any]:
    return {
        "id": f"mem_{field}",
        "kind": "propose_memory_patch",
        "field": field,
        "hint": (
            f"本步只 propose_memory_patch(field=\"{field}\", mode=\"merge\", after=改动项)。"
            "不要改其他 field，不要新建文档，不要做指令里没写的事。"
        ),
    }


def work_plan_system_note(plan: List[Dict[str, Any]]) -> str:
    lines = [
        "【后台分步编排已启用】只执行当前用户指令。队列外的事不要做。",
        "每轮只做一个工具动作。禁止把多字段设定或长章节塞进同一次 JSON。",
        "队列如下：",
    ]
    for i, step in enumerate(plan, 1):
        field = step.get("field")
        extra = f" field={field}" if field else ""
        lines.append(f"{i}. [{step['kind']}{extra}] {step['hint']}")
    lines.append("完成当前步后再进入下一步。全部完成后 finish。不要补做指令里没有的修改。")
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
    if plan:
        return
    # 没有队列时不要发明改设定任务；只有指令本身在改设定才给一个最小补丁步
    if not looks_like_settings_edit_instruction(getattr(ctx, "instruction", "") or ""):
        return
    ctx.work_plan = [
        {
            "id": "mem_one",
            "kind": "propose_memory_patch",
            "hint": "只改指令点名的 1 个设定 field；after 精简。不要改其他字段。",
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
