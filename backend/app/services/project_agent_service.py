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
from app.services.memory_normalize import coerce_memory_field
from app.services.project_agent_phases import (
    advance_work_plan,
    current_phase_nudge,
    enable_narrow_mode,
    generation_forbids_settings_edits,
    infer_work_plan,
    looks_like_read_all_plan,
    looks_like_settings_edit_instruction,
    work_plan_system_note,
)
from app.services.project_agent_tools import (
    MEMORY_FIELDS,
    ProjectAgentContext,
    ToolViolation,
    _find_block,
    _norm,
    execute_tool,
)

# 不再因「最大步数」硬失败；以 finish / 取消 / 租约失效 正常结束。
# 仅保留极高安全阀：到顶时尽量提交已有改动，避免失控死循环占满进程。
SAFETY_STEP_CEILING = 500
STEP_FINISH_NUDGE_AT = (20, 40, 80, 160, 320)  # 提醒模型尽快收尾，不中止任务
MAX_EVENTS = 500
MAX_CONSECUTIVE_TEXT_TURNS = 3  # 漏发工具动作可纠正，但不允许无限空转
MAX_VIOLATION_RETRIES = 2  # 可纠正违规（未先读、参数错误等）反馈重试次数，第 3 次判失败
MAX_EMPTY_MODEL_RETRIES = 2  # 空响应：1 次压缩重试 + 1 次极简救援；再空则安全结束（不标 failed）

SYSTEM_PROMPT = """你是「墨心」写作项目的智能编辑搭档「小墨」。按用户这条指令执行，不自行加任务。

## 只执行当前指令
- 本轮唯一任务是最后一条用户指令。历史只作参考，不能追加、改写或续做上一轮没说完的步骤。
- 只做指令里写明的事。不要顺手改大纲、人物、故事线、世界观、正文，也不要额外检查、整理或新建章节。
- 没点名的设定字段不要改。只说生成文章，就只生成文章。只说改人物，就只改人物。只说检查或讨论，就只汇报，不要直接改。
- 预读和工作队列都不能把任务扩大。做完指令里的事就 finish。

## 交互方式
- 每轮先用一两句说明你准备执行指令的哪一部分。仅当系统未给出目标文档/段落时才提问澄清。
- 每轮先用自然语言说明你理解了什么、打算怎么做；仅当系统未给出目标文档/段落时才提问澄清。
- 需要操作时，在回复末尾给出一个 ```json 工具动作（每轮仅一个）：
```json
{"tool": "工具名", "args": { ... }}
```
- 说要读、查、改、扩写时必须真正调用工具，不要停在计划上。
- JSON 字符串里的引号用普通英文双引号，并正确转义。正文对话也用普通引号，不要写成「」『』。
- 最终答复或只需聊天时调用 finish(answer)。用户看不到工具原始返回，用自己的话总结。

## 可用工具
- list_project()：列出文档与可改设定字段。
- document_map(document_id=0, limit=40)：长文目录地图（标题/块数/字数/headings+offset）。document_id=0 扫全项目。不返回正文。
- digest_document(document_id, max_chars=1600)：单篇抽取摘要（类子任务隔离：全文不进主对话）。改稿前仍须定点 read_document。
- read_document(document_id, offset=0, limit=12)：分页读正文（默认每页约 12 块，上限 20）。complete=false 时用 next_offset 继续，切勿一次读完全文。
- read_memory(field="")：读取项目设定。默认返回各字段概览；指定 field（如 key_points）返回该字段较完整内容。
- search_project(query, offset=0, limit=10)：字面量检索正文与设定。
- propose_document_patch(document_id, block_id, old_text, new_text, reason="")：正文补丁。old_text 须在目标块恰好出现一次。
- propose_block_rewrite(document_id, block_id, new_content, reason="")：整块重写（润色/改写/扩写一段时优先用它，不必精确抠 old_text）。
- propose_memory_patch(field, after, before=null, mode="replace", reason="")：更新项目设定。
  · field：characters / storyline / outline / world_building / writing_style / key_points / notes
  · mode="merge"：增量合并（人物/情节点按 name·title upsert；故事线合并 stages；文本追加）。只传新增或改动项即可，不必回传整字段。
  · mode="replace"：整字段覆盖（慎用，大字段易截断）。
  · before 可省略（服务端用暂存基线）。每次只改 1 个 field。
- propose_create_document(title, text, reason="")：新建一篇短文档提案。不要用它一次写多章正文。
- generate_documents_from_settings(custom_instruction="", max_tokens_per_chapter=4000)：按现有大纲逐章生成文章并写入文档。只读项目设定，禁止同时改大纲或任何设定字段。正文不回灌进对话。用户要「根据大纲/设定生成文章」时只用它，然后 finish。
- propose_delete_document(document_id, reason="")：删除文档提案。仅暂存，不会自动执行；须用户在对话中确认后才真正删除。有子文档时不可删。
- create_project(title, description="", reason="")：无项目时即时创建并绑定本轮；已有项目勿调用。
- list_hot_topics(limit=20, category="", refresh=false)：拉取热点选题。
- hot_topic_write(topic_title, article_type="评论", word_count=1500, style="专业", additional_requirements="")：热点写作，返回 draft_id。
- copywriting_write(product, target_audience, copy_objective, selling_points, …)：营销文案，返回 draft_id。
- list_brainstorm_ideas(category="", limit=12)：脑洞选题。
- brainstorm_write(title, category, concept, style, word_count)：脑洞写作，返回 draft_id。
- story_generate(theme, genre="", word_count=5000, chapter_count=0, additional_requirements="")：故事设定包，返回 draft_id。
- propose_writing_draft(draft_id, reason="", title="")：把专项写作草稿提案为新建文档（勿把预览当全文）。
- propose_story_settings(draft_id, reason="")：把故事设定草稿拆入项目 memory 提案。
- finish(answer)：结束本轮。

## 无项目模式
- 用户尚未打开/绑定项目时：可先聊天规划，或直接用专项写作；要落盘正文/设定前必须 create_project(title=...)。
- 推荐顺序：list_* 选题 → *_write / story_generate → create_project（标题可取话题名）→ propose_writing_draft / propose_story_settings → finish。
- 也可先 create_project 再写作。create_project 即时生效并绑定本轮，勿重复创建。
- 纯讨论、不写库时可直接 finish，不必建项目。

## 专项写作 vs 普通改稿
- 用户要「脑洞/热点/文案/故事生成」时，优先用对应专项工具，不要用 propose_block_rewrite 硬写长文。
- 热点/脑洞：先 list_* 选题，再 *_write；写完必须 propose_writing_draft（或故事用 propose_story_settings）再 finish。
- 专项写作 observation 只有标题+预览+draft_id；完整正文在服务端暂存，禁止把 preview 复制进 propose_create_document。
- 已有文档的润色/改写/续写仍走 read + propose_block_rewrite / propose_document_patch。
- 独立写作页仍可用；需要复杂表单时可在答复中提示用户打开对应页面（热点 /hot-topics、脑洞 /brainstorm-writing、文案 /copywriting-writing、故事 /ai-story-generator）。

## 智能编辑原则
1. 有「当前编辑焦点」时，「这篇/当前文档」一律指该 document_id。不要 list_project 确认篇目，不要反问。
2. 系统已给出 block_id / 选中原文时：禁止追问「是哪几段/哪三个段落」；禁止通读全文；立刻 propose_block_rewrite。
3. 润色/改写长文：采用「读一页 → 立刻改 1～3 块 → 再读下一页」。禁止先把全文读完再改；读完全文极易导致空响应失败。
4. 焦点文档若已预读，直接对已给出的 block_id 调用 propose_block_rewrite，不要重复 read_document(offset=0)。
5. 改名、统一用词等跨处修改：先 search_project，再逐处 patch。
6. 更新设定：只有用户明确要求修改设定（大纲、人物、故事线、世界观、文风、要点、备注）时才调用 propose_memory_patch。优先 mode="merge"，每次 1 个 field。正文和设定里的引号用普通引号，不要用「」『』。
7. 「根据大纲/设定生成文章、多篇、多章」：只调用 generate_documents_from_settings()，然后 finish。禁止 propose_memory_patch，禁止改大纲或任何项目设定，禁止为了“对齐生成结果”回写设定。每一章按现有设定来写。单篇短章或改已有文档仍用 propose_create_document / propose_block_rewrite。
8. 「转视频文案 / 影视脚本」：读原文后用 propose_create_document 新建文档，不要覆盖原文档。
9. 用户要求删除文档时：用 propose_delete_document；先 list_project / 焦点确认 document_id。告知用户须在对话里点确认才会真正删除。勿与同轮正文补丁混用。
10. 需要看长文结构时用 document_map → digest_document，再按指令定点 read_document。不要因此去改设定。
    【严禁】把 storyline、outline「完整全文」和全部章节正文读进对话。
11. 指令做完就 finish。只讨论、只检查时不要改稿、不要改设定。
12. 工具动作必须是完整闭合的 ```json … ```；写不完就缩小范围分多轮，切勿输出半截代码块。
13. 用户要求改设定时，只改点名的字段，每次 1 个 field。不要按人设→故事线→大纲的顺序把没点名的字段也改掉。
14. 文章大纲 outline 与关键情节点 key_points 都可改，形状不同：
   · outline：[{{"title":"章名","description":"本章简述"}}]，mode="merge" 按 title 合并；空占位会被丢掉。
   · key_points：[{{"title":"情节点","summary":"发生了什么"}}]，同样 mode="merge"。
   只传本次新增或改动的条目，不要回传整表。"""


def _extract_fenced_json(text: str) -> Optional[str]:
    """从模型输出中提取已闭合的 ```json 代码块内容；没有闭合块返回 None。"""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S | re.I)
    return match.group(1).strip() if match else None


def _extract_unclosed_fenced_json(text: str) -> Optional[str]:
    """提取未闭合 ```json 之后的内容（常见于 max_tokens 截断）。须以 { 开头才视为动作。"""
    if _extract_fenced_json(text) is not None:
        return None
    match = re.search(r"```(?:json)?\s*\n?(.*)\Z", text, re.S | re.I)
    if not match:
        return None
    body = (match.group(1) or "").strip()
    return body if body.startswith("{") else None


def _json_object_structurally_complete(raw: str) -> bool:
    """未闭合围栏场景：仅当花括号/字符串在字面量层面已闭合时才接受（防 json_repair 补全半截正文）。"""
    text = (raw or "").strip()
    if not text.startswith("{") or not text.endswith("}"):
        return False
    depth = 0
    in_str = False
    escape = False
    for ch in text:
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_str


def _json_candidates(raw: str) -> List[str]:
    """生成可尝试解析的 JSON 候选（全文 + 最外层花括号切片）。"""
    text = (raw or "").strip()
    if not text:
        return []
    out = [text]
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        sliced = text[start : end + 1].strip()
        if sliced and sliced not in out:
            out.append(sliced)
    return out


def _try_loads_json(raw: str) -> Any:
    """先标准解析；失败再用 json_repair 容错（未转义引号、尾随逗号等）。无法解析返回 None。"""
    for candidate in _json_candidates(raw):
        try:
            return json.loads(candidate)
        except Exception:
            pass
        try:
            from json_repair import repair_json

            repaired = repair_json(candidate, return_objects=True)
            if isinstance(repaired, str):
                try:
                    repaired = json.loads(repaired)
                except Exception:
                    continue
            if repaired is not None:
                return repaired
        except Exception:
            continue
    return None


def _require_tool_action(obj: Any, *, source: str) -> dict:
    if not isinstance(obj, dict):
        raise ToolViolation(f"{source}必须是 JSON 对象")
    if not isinstance(obj.get("tool"), str):
        raise ToolViolation(f"{source}缺少 tool 字段")
    return obj


_ASK_WHICH_BLOCKS_RE = re.compile(
    r"(哪\s*[一二三四五六七八九十\d]+\s*段|哪几段|哪个段落|是哪三段|告诉我.*段落|具体是哪)",
    re.I,
)


def _asks_which_blocks(text: Optional[str]) -> bool:
    return bool(text and _ASK_WHICH_BLOCKS_RE.search(text))


def _focus_targets_reminder(ctx: ProjectAgentContext) -> str:
    """把已锁定的选中块再钉进对话，阻止模型追问「是哪几段」。"""
    doc_id = getattr(ctx, "focus_document_id", None)
    ids = list(getattr(ctx, "focus_block_ids", None) or [])
    lines = [
        "【强制纠正】目标段落已锁定，禁止追问「是哪几段/哪三个段落」。",
        f"请立刻对下列 block_id 调用 propose_block_rewrite（每次 1～3 块），改完 finish。",
    ]
    if doc_id is not None:
        lines.append(f"document_id={doc_id}")
    blocks = (ctx.read_documents.get(doc_id) or []) if doc_id else []
    by_id = {
        str(b.get("id")): b
        for b in blocks
        if isinstance(b, dict) and b.get("id") is not None
    }
    for bid in ids[:12]:
        block = by_id.get(str(bid))
        if not block:
            lines.append(f"- block_id={bid}")
            continue
        content = block.get("content") or ""
        snippet = content if len(content) <= 400 else content[:400] + "…"
        lines.append(f"- block_id={bid} [{block.get('type')}]\n{snippet}")
    lines.append(
        "JSON 里 new_content 的引号用普通英文双引号并转义，正文不要写成「」『』。"
    )
    return "\n".join(lines)


def _parse_action_and_message(raw: Any):
    """
    解析模型输出 → (action, message)。

    兼容两种形态：
    - 纯 JSON 动作（历史/测试形态）：整段是 {"tool": ..., "args": ...}
    - 对话形态：自然语言 + 末尾 ```json 代码块动作
    返回 (None, message) 表示本轮只是闲聊/说明（say 轮）。
    代码块存在但 JSON 非法 → 抛 ToolViolation（视为模型输出错误）。
    未闭合代码块：若 JSON 本身可修复则接受；否则提示缩小提案并重写。
    """
    if not isinstance(raw, str):
        raise ToolViolation("模型输出必须是字符串")
    text = raw.strip()
    if not text:
        raise ToolViolation("模型输出为空")
    # 形态一：整段以 JSON 开头。可能是一个动作，也可能是连续多个裸 JSON。
    # 整段 json.loads 失败时不要丢掉后面的动作。
    if text.startswith("{"):
        found = _collect_tool_actions(text)
        if found:
            prose = _strip_embedded_tool_json(text).strip() or None
            return found[0], prose
        action = _try_loads_json(text)
        if action is not None:
            return _require_tool_action(action, source="模型输出"), None

    def _message_before_fence() -> Optional[str]:
        idx = text.find("```")
        return (text[:idx].strip() or None) if idx >= 0 else None

    def _action_from_fenced(fenced: str, *, source: str):
        action = _try_loads_json(fenced)
        if action is None:
            detail = "动作代码块不是合法 JSON"
            try:
                json.loads(fenced)
            except Exception as e:
                detail = f"动作代码块不是合法 JSON: {e}"
            raise ToolViolation(
                f"{detail}。请重写整个 ```json 代码块；"
                f"new_content/answer 内的引号请正确转义，正文不要改成「」『』，"
                f"不要省略逗号与引号。"
            )
        return _require_tool_action(action, source=source), _message_before_fence()

    # 形态二：自然语言 + 已闭合 fenced 动作
    fenced = _extract_fenced_json(text)
    if fenced is not None:
        return _action_from_fenced(fenced, source="动作代码块")

    # 形态二 b：未闭合 ```json（漏写结尾围栏 / 输出截断）
    # 仅当 JSON 结构本身已完整时接受（缺 ```）；半截字符串绝不交给 json_repair 补全。
    unclosed = _extract_unclosed_fenced_json(text)
    if unclosed is not None:
        if _json_object_structurally_complete(unclosed):
            action = _try_loads_json(unclosed)
            if action is not None and isinstance(action, dict) and isinstance(action.get("tool"), str):
                return _require_tool_action(action, source="动作代码块"), _message_before_fence()
        raise ToolViolation(
            "动作代码块未闭合或内容被截断。请缩小本次提案"
            "（设定每次只改 1 个字段；新建章节先写短大纲），"
            "重写完整的 ```json … ``` 并确保闭合。"
        )

    if re.search(r"```(?:json)?", text, re.I):
        raise ToolViolation(
            "动作代码块未闭合或内容被截断。请缩小本次提案"
            "（设定每次只改 1 个字段；新建章节先写短大纲），"
            "重写完整的 ```json … ``` 并确保闭合。"
        )
    # 形态四：正文里直接嵌了 {"tool": ...}（没写 ```json）。先执行，不要当成闲聊丢掉。
    inline = _collect_tool_actions(text)
    if inline:
        prose = _strip_embedded_tool_json(text).strip() or None
        return inline[0], prose
    # 形态三：纯自然语言（say 轮）
    return None, text


def _iter_balanced_objects(text: str):
    """按花括号配对切出顶层 JSON 对象切片（忽略字符串内的括号）。"""
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        escape = False
        end = None
        for j in range(i, n):
            ch = text[j]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        if end is None:
            return
        yield i, end
        i = end


def _collect_tool_actions(text: str) -> List[dict]:
    """从一段回复里按出现顺序捞出全部完整工具动作（围栏内或裸 JSON）。"""
    actions: List[dict] = []
    seen = set()
    for start, end in _iter_balanced_objects(text or ""):
        raw = text[start:end]
        if '"tool"' not in raw and "'tool'" not in raw:
            continue
        if not _json_object_structurally_complete(raw):
            continue
        obj = _try_loads_json(raw)
        if not isinstance(obj, dict) or not isinstance(obj.get("tool"), str):
            continue
        key = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        actions.append(obj)
    return actions


def _strip_embedded_tool_json(text: str) -> str:
    """展示用：去掉已识别的工具 JSON，只留自然语言。"""
    spans = []
    for start, end in _iter_balanced_objects(text or ""):
        raw = text[start:end]
        if '"tool"' not in raw:
            continue
        obj = _try_loads_json(raw) if _json_object_structurally_complete(raw) else None
        if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
            spans.append((start, end))
    if not spans:
        return text
    out = []
    cursor = 0
    for start, end in spans:
        out.append(text[cursor:start])
        cursor = end
    out.append(text[cursor:])
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip()


def _split_memory_patch_actions(action: dict) -> List[dict]:
    """storyline/outline 等过大时，按条目拆成多次 merge，而不是整包失败。"""
    args = action.get("args") if isinstance(action.get("args"), dict) else {}
    # 顶层 field/after 也认
    field = args.get("field") or action.get("field")
    after = args.get("after") if "after" in args else action.get("after")
    if not isinstance(after, dict):
        return []
    stages = after.get("stages")
    if not isinstance(stages, list) or len(stages) < 2:
        return []
    mode = args.get("mode") or action.get("mode") or "merge"
    reason = args.get("reason") or action.get("reason") or "分批更新设定"
    pieces: List[dict] = []
    summary = after.get("summary")
    for index, stage in enumerate(stages):
        payload: Dict[str, Any] = {"stages": [stage]}
        if index == 0 and summary:
            payload["summary"] = summary
        pieces.append({
            "tool": "propose_memory_patch",
            "args": {
                "field": field,
                "mode": mode,
                "reason": f"{reason}（{index + 1}/{len(stages)}）",
                "after": payload,
            },
        })
    return pieces


# ---------------------------------------------------------------------------
# 创建 / 查询
# ---------------------------------------------------------------------------

def _snapshot_model_config(db) -> Dict[str, Any]:
    """创建时快照当前模型配置（便于审计与复现）；失败时退回空 dict。"""
    try:
        config: Dict[str, Any] = {}
        for key in (
            "ai_provider",
            "ai_model",
            "ai_base_url",
            "ai_preferred_mode",
            "ai_local_model",
            "ai_local_base_url",
        ):
            row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if row and row.config_value:
                try:
                    config[key] = json.loads(row.config_value).get("value", row.config_value)
                except Exception:
                    config[key] = row.config_value
        return config
    except Exception:
        return {}


def _refresh_runtime_ai_client() -> Dict[str, str]:
    """每次执行前按 DB 刷新全局客户端，避免切换线上/本地后仍用旧单例。"""
    from app.core.ai_client import refresh_ai_client

    client = refresh_ai_client()
    mode = getattr(client, "preferred_mode", "") or "online"
    provider = getattr(client, "provider", "") or ""
    model_name = getattr(client, "model", "") or ""
    base = getattr(client, "base_url", "") or ""
    label = f"{'本地' if mode == 'local' else '线上'} {provider}/{model_name}"
    print(f"[project_agent] 本轮使用模型: {label} @ {base}")
    return {
        "mode": mode,
        "provider": provider,
        "model": model_name,
        "base_url": base,
        "label": label,
    }


def create_run(
    db,
    user_id: int,
    project_id: int,
    instruction: str,
    conversation_id: Optional[str],
    idempotency_key: Optional[str] = None,
    focus: Optional[Dict[str, Any]] = None,
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
    config = _snapshot_model_config(db)
    if focus and isinstance(focus, dict) and focus.get("document_id"):
        # 校验焦点文档属于本项目，避免注入越权 document_id
        doc = db.get(Document, int(focus["document_id"]))
        if doc is None or doc.project_id != project_id:
            raise HTTPException(status_code=400, detail="focus.document_id 无效")
        config = {**(config or {}), "focus": {
            "document_id": doc.id,
            "document_title": doc.title or "",
            "selection": (focus.get("selection") or "")[:20000] or None,
            "block_ids": focus.get("block_ids") if isinstance(focus.get("block_ids"), list) else None,
        }}
    run = AgentRun(
        project_id=project_id,
        user_id=user_id,
        instruction=instruction,
        conversation_id=conversation_id or str(uuid.uuid4()),
        status="queued",
        model_config=config,
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
        return create_run(
            db, user_id, project_id, instruction, conversation_id, idempotency_key, focus=focus
        )
    db.refresh(run)
    return run


def get_run(db, user_id: int, project_id: int, run_id: str) -> AgentRun:
    run = db.get(AgentRun, run_id)
    project = db.get(Project, project_id)
    if (run is None or run.project_id != project_id or run.user_id != user_id
            or run.scope != "project" or project is None or project.owner_id != user_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def create_system_run(
    db,
    user_id: int,
    instruction: str,
    conversation_id: Optional[str],
    idempotency_key: Optional[str] = None,
) -> AgentRun:
    """无项目会话：scope=system，project_id 可空；执行中 create_project 后再绑定。"""
    if conversation_id:
        conversation = (
            db.query(AgentRun)
            .filter(
                AgentRun.conversation_id == conversation_id,
                AgentRun.user_id == user_id,
                AgentRun.scope == "system",
            )
            .first()
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    if idempotency_key:
        existing = db.query(AgentRun).filter(AgentRun.idempotency_key == idempotency_key).first()
        if existing is not None:
            if (
                existing.user_id != user_id
                or existing.scope != "system"
                or (conversation_id and existing.conversation_id != conversation_id)
            ):
                raise HTTPException(status_code=409, detail="Idempotency key scope conflict")
            return existing
    config = _snapshot_model_config(db)
    run = AgentRun(
        scope="system",
        project_id=None,
        user_id=user_id,
        instruction=instruction,
        conversation_id=conversation_id or str(uuid.uuid4()),
        status="queued",
        model_config=config,
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
        return create_system_run(db, user_id, instruction, conversation_id, idempotency_key)
    db.refresh(run)
    return run


def get_system_run(db, user_id: int, run_id: str) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None or run.user_id != user_id or run.scope != "system":
        raise HTTPException(status_code=404, detail="Run not found")
    if run.project_id is not None:
        project = db.get(Project, run.project_id)
        if project is None or project.owner_id != user_id:
            raise HTTPException(status_code=404, detail="Run not found")
    return run


def list_system_runs(db, user_id: int, conversation_id: Optional[str] = None) -> List[AgentRun]:
    query = db.query(AgentRun).filter(
        AgentRun.user_id == user_id, AgentRun.scope == "system"
    )
    if conversation_id:
        query = query.filter(AgentRun.conversation_id == conversation_id)
    return query.order_by(AgentRun.created_at.desc()).all()


def transition_system(db, user_id: int, run_id: str, verb: str) -> AgentRun:
    run = get_system_run(db, user_id, run_id)
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
        "scope": run.scope or "project",
        "project_id": run.project_id,
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

def _is_usable_model_text(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    return not (stripped.startswith("[错误]") or stripped.startswith("[配置错误]"))


# 智能体单次调用等待：普通模型 240s；ai_client 对推理/本地还会再抬到 300s/600s
AGENT_MODEL_TIMEOUT_SEC = 240.0


class PartialModelError(RuntimeError):
    """超时/中断时若已有部分正文，带着草稿抛出，供上层续写而非从头来。"""

    def __init__(self, message: str, partial: str = ""):
        super().__init__(message)
        self.partial = partial or ""


async def default_model(messages, **kwargs) -> str:
    """智能体模型调用：非流式优先，再流式兜底；加长等待；保留半成品供续写。"""
    from app.core.ai_client import ai_client

    on_delta = kwargs.get("on_delta")
    on_heartbeat = kwargs.get("on_heartbeat")
    partial_out = kwargs.get("partial_out")  # 可变 dict，写入已生成草稿
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens") or 8192
    timeout = float(kwargs.get("timeout") or AGENT_MODEL_TIMEOUT_SEC)
    last_error = "[错误] 模型未返回内容"
    partial_acc = ""
    mode = getattr(ai_client, "preferred_mode", "?")
    print(
        f"[project_agent] 调用模型 mode={mode} "
        f"provider={getattr(ai_client, 'provider', '?')} "
        f"model={getattr(ai_client, 'model', '?')} timeout={timeout}s"
    )

    def _beat():
        if on_heartbeat is None:
            return True
        try:
            return bool(on_heartbeat())
        except Exception:
            return True

    def _remember(text: str) -> str:
        nonlocal partial_acc
        text = (text or "").strip()
        if text:
            partial_acc = text
            if isinstance(partial_out, dict):
                partial_out["text"] = text
        return text

    def _emit(text: str) -> None:
        if on_delta is None or not text:
            return
        try:
            on_delta(text)
        except Exception:
            pass

    async def _non_stream_once() -> str:
        text = await ai_client.chat_completion(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            enable_network_test=False,
            retry_attempts=2,
        )
        return _remember((text or "").strip())

    async def _stream_once() -> str:
        chunks: List[str] = []
        async for chunk in ai_client.stream_completion(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        ):
            if not chunk:
                continue
            chunks.append(chunk)
            _emit(chunk)
            _remember("".join(chunks))
            if len(chunks) == 1 or len(chunks) % 8 == 0:
                _beat()
        return _remember("".join(chunks).strip())

    # 1) 非流式优先
    if not _beat():
        raise PartialModelError("[错误] 任务租约已失效，请重试", partial_acc)
    try:
        text = await _non_stream_once()
        if _is_usable_model_text(text):
            _emit(text)
            return text
        last_error = text or last_error
        print(f"[project_agent] 非流式未产出正文: {last_error[:200]}")
    except Exception as e:
        last_error = str(e) or last_error
        print(f"[project_agent] 非流式调用异常: {last_error[:200]}")
        if partial_acc:
            raise PartialModelError(last_error, partial_acc) from e

    # 2) 流式兜底
    if not _beat():
        raise PartialModelError(
            last_error if last_error.startswith("[") else f"[错误] {last_error}",
            partial_acc,
        )
    try:
        text = await _stream_once()
        if _is_usable_model_text(text):
            return text
        last_error = text or last_error
        print(f"[project_agent] 流式兜底仍空: {last_error[:200]}")
    except Exception as e:
        last_error = str(e) or last_error
        print(f"[project_agent] 流式兜底异常: {last_error[:200]}")
        if partial_acc:
            raise PartialModelError(last_error, partial_acc) from e

    if partial_acc:
        raise PartialModelError(
            last_error if last_error.startswith("[") else f"[错误] {last_error}",
            partial_acc,
        )
    raise RuntimeError(last_error if last_error.startswith("[") else f"[错误] {last_error}")


async def _call_model(model, messages, **kwargs) -> str:
    # 设定补丁 JSON 较大；给足等待时间，避免长思考被过早掐断
    result = model(
        messages,
        temperature=0.5,
        max_tokens=8192,
        timeout=AGENT_MODEL_TIMEOUT_SEC,
        **kwargs,
    )
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


def _collect_input_versions(db, project_id: Optional[int]) -> Dict[str, Any]:
    versions: Dict[str, Any] = {}
    if not project_id:
        return versions
    for row in db.query(Document.id, Document.updated_at).filter(Document.project_id == project_id):
        versions[f"document:{row.id}"] = row.updated_at.isoformat() if row.updated_at else None
    memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
    versions["memory"] = memory.updated_at.isoformat() if memory and memory.updated_at else None
    return versions


MAX_CONTEXT_MESSAGES = 12  # 继承同会话历史消息的上限（按条，不是按轮）
MAX_CONTEXT_CHARS = 4000  # 继承上下文的字符上限；长文设定不随对话回放
_HISTORY_TEXT_CHARS = 360  # 单条历史发言只留摘要
# 单轮执行中的上下文预算（借鉴 Kimi auto-compact：逼近上限则压缩旧观察）
LIVE_CONTEXT_BUDGET_CHARS = 28000
LIVE_COMPACT_TRIGGER_RATIO = 0.72
LIVE_COMPACT_TAIL_MESSAGES = 8
STREAM_FLUSH_INTERVAL = 1.2  # 流式回复增量落盘的最小间隔（秒）


def _clip_history_text(content: str) -> str:
    """历史只留结论，不把上一轮的整段设定 JSON 再塞进本轮。"""
    text = _strip_embedded_tool_json(content or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= _HISTORY_TEXT_CHARS:
        return text
    return text[:_HISTORY_TEXT_CHARS] + "…（更早长文已省略，设定以当前暂存为准）"


def _load_conversation_messages(db, run: AgentRun, instruction: str = "") -> List[Dict[str, str]]:
    """同一会话的历史摘要。整段超出长度上限时整段丢弃，只执行当前指令。"""
    scope = run.scope or "project"
    query = db.query(AgentRun).filter(
        AgentRun.conversation_id == run.conversation_id,
        AgentRun.user_id == run.user_id,
        AgentRun.scope == scope,
        AgentRun.id != run.id,
        AgentRun.created_at <= run.created_at,
        AgentRun.status.in_(("proposed", "completed", "applied", "reverted", "failed", "cancelled")),
    )
    if scope == "project":
        query = query.filter(AgentRun.project_id == run.project_id)
    prior = query.order_by(AgentRun.created_at.asc(), AgentRun.id.asc()).all()
    history: List[Dict[str, str]] = []
    for prev in prior:
        history.append({"role": "user", "content": _clip_history_text(prev.instruction or "")})
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
                history.append({"role": "assistant", "content": _clip_history_text(m["content"])})
                turn_contents.add(m["content"])
        answer = _safe_assistant_content(prev.answer)
        if answer and answer not in turn_contents:
            history.append(status_message)
            history.append({"role": "assistant", "content": _clip_history_text(answer)})
    # 历史加上当前指令超出上限：不带任何上下文，只执行当前命令
    history_chars = sum(len(m.get("content") or "") for m in history)
    if history_chars + len(instruction or "") > MAX_CONTEXT_CHARS:
        return []
    # 条数过多时只留最近几条（总字数已在上限内）
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


def _bind_current_article(instruction: str, focus: Optional[Dict[str, Any]]) -> str:
    """文档页只要有焦点，就把「这篇/当前文档/焦点」钉死到该 document_id。"""
    if not isinstance(focus, dict) or not focus.get("document_id"):
        return instruction
    doc_id = focus["document_id"]
    marker = f"document_id={doc_id}"
    title = focus.get("document_title") or ""
    title_bit = f"《{title}》" if title else ""
    out = instruction or ""
    if marker not in out:
        out = (
            f"{out}\n\n"
            f"（系统说明：用户正在编辑的当前文档就是 {marker}{title_bit}。"
            f"「这篇 / 当前文档 / 焦点段落」都指这一篇。"
            f"禁止 list_project 后追问是哪一篇；已预读则直接改稿。）"
        )
    block_ids = [
        str(b) for b in (focus.get("block_ids") or []) if b is not None and str(b).strip()
    ][:40]
    if block_ids and "目标已锁定" not in out:
        listed = "、".join(f"block_id={b}" for b in block_ids)
        out += (
            f"\n\n（系统：用户已选中 {len(block_ids)} 个段落，目标已锁定："
            f"{listed}。"
            f"禁止追问是哪几段；禁止通读全文；直接对这些 block_id 调用 "
            f"propose_block_rewrite 后 finish。）"
        )
    elif _focus_has_selection(focus) and "只改选中" not in out and "目标已锁定" not in out:
        out += (
            "\n\n（系统：用户已给出选中原文，请只改对应段落；"
            "禁止追问是哪几段；禁止通读全文；直接 propose_block_rewrite 后 finish。）"
        )
    return out


def _focus_has_selection(focus: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(focus, dict):
        return False
    if (focus.get("selection") or "").strip():
        return True
    ids = focus.get("block_ids") or []
    return isinstance(ids, list) and len(ids) > 0


def _focus_system_note(focus: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(focus, dict) or not focus.get("document_id"):
        return None
    doc_id = focus["document_id"]
    title = focus.get("document_title") or ""
    title_bit = f"《{title}》" if title else ""
    lines = [
        "## 当前编辑焦点",
        f"用户正在编辑文档 document_id={doc_id}{title_bit}。",
        "用户说「这篇文章」「当前文档」「焦点段落」「这篇」时，就是这篇。",
        "禁止再确认是哪一篇；禁止为找当前文档而 list_project。",
    ]
    block_ids = focus.get("block_ids") or []
    if isinstance(block_ids, list) and block_ids:
        lines.append("目标块 ID（只改这些）：" + ", ".join(str(b) for b in block_ids[:40]))
        lines.append("禁止追问「是哪几段 / 哪三个段落」——标识已在上方给出。")
    selection = (focus.get("selection") or "").strip()
    if selection:
        excerpt = selection if len(selection) <= 4000 else selection[:4000] + "…"
        lines.append("用户选中/引用的原文（请基于此改写）：\n" + excerpt)
    if _focus_has_selection(focus):
        lines.extend(
            [
                "【强制】用户已给出选区/目标块：禁止 read_document，禁止「先通读全文」，禁止追问目标段落。",
                "立刻对目标 block_id 调用 propose_block_rewrite（每次 1～3 块），改完 finish。",
                "propose_block_rewrite 的 new_content 内引号用普通引号并转义，避免 JSON 非法。",
            ]
        )
    else:
        lines.append(
            "若用户要润色长文：读一页就改，禁止通读全文。优先 propose_block_rewrite。"
        )
    lines.append("finish 的 args.answer 须为字符串（缺省会自动兜底）。")
    return "\n".join(lines)


def _preload_focus_document(db, ctx: ProjectAgentContext, focus: Optional[Dict[str, Any]]) -> Optional[str]:
    """有选区则只装目标块；否则只预读首页。避免润色时把全文灌进上下文。"""
    if not isinstance(focus, dict) or not focus.get("document_id"):
        return None
    doc_id = int(focus["document_id"])
    block_ids = [
        str(b) for b in (focus.get("block_ids") or []) if b is not None and str(b).strip()
    ][:40]
    selection = (focus.get("selection") or "").strip()

    if block_ids or selection:
        try:
            # 装载全文到 ctx 供 rewrite，但不把全文塞给模型
            execute_tool(
                ctx,
                db,
                "read_document",
                {"document_id": doc_id, "offset": 0, "limit": 1},
            )
        except Exception as exc:
            return f"预读当前文章失败：{exc}"
        all_blocks = ctx.read_documents.get(doc_id) or []
        by_id = {
            str(b.get("id")): b
            for b in all_blocks
            if isinstance(b, dict) and b.get("id") is not None
        }
        targets: List[dict] = []
        if block_ids:
            for bid in block_ids:
                block = by_id.get(bid)
                if block:
                    targets.append(block)
        if not targets and selection:
            needle = selection[:120]
            for block in all_blocks:
                content = block.get("content") if isinstance(block, dict) else None
                if isinstance(content, str) and needle and needle in content:
                    targets.append(block)
                    if len(targets) >= 8:
                        break
        if not targets:
            targets = [b for b in all_blocks if isinstance(b, dict)][:3]

        lines = [
            f"用户要改的是 document_id={doc_id}《{ctx.document_titles.get(doc_id, '')}》中的选中段落"
            f"（{len(targets)} 块）。正文已在服务端装载。",
            "禁止再调用 read_document。请立刻 propose_block_rewrite，每次 1～3 块，改完 finish。",
        ]
        for block in targets:
            content = block.get("content") or ""
            if not isinstance(content, str) or not content.strip():
                continue
            snippet = content if len(content) <= 1200 else content[:1200] + "…"
            lines.append(f"- block_id={block.get('id')} [{block.get('type')}]\n{snippet}")
        ctx.focus_block_ids = [str(b.get("id")) for b in targets if b.get("id") is not None]
        return "\n".join(lines)

    try:
        data = execute_tool(
            ctx,
            db,
            "read_document",
            {"document_id": doc_id, "offset": 0, "limit": 12},
        )
    except Exception as exc:
        return f"预读当前文章失败：{exc}"
    blocks = data.get("blocks") or []
    total = data.get("total_blocks") or len(blocks)
    lines = [
        f"已预读当前文章 document_id={data.get('document_id')}《{data.get('title') or ''}》"
        f"（全文约 {total} 块，以下仅第 1 页共 {len(blocks)} 块）。",
        "请立刻对本页需要润色的块 propose_block_rewrite（每次 1～3 块）。",
        "禁止为「先看完全文」而连续 read_document；改完本页再用 next_offset 读下一页。",
    ]
    for block in blocks:
        content = block.get("content") or ""
        if not isinstance(content, str) or not content.strip():
            continue
        snippet = content if len(content) <= 500 else content[:500] + "…"
        lines.append(f"- block_id={block.get('id')} [{block.get('type')}]\n{snippet}")
    if data.get("complete") is False:
        lines.append(f"本页未到文末；下页 offset={data.get('next_offset')}（改完本页再读）。")
    return "\n".join(lines)


def _clip_memory_value(value: Any, limit: int = 1200) -> Any:
    """设定字段写入模型观察时截断，完整值仍在 ctx.staged_memory。"""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "…"
    if isinstance(value, list):
        out = []
        used = 0
        for item in value:
            piece = _clip_memory_value(item, min(400, limit))
            piece_len = len(json.dumps(piece, ensure_ascii=False, default=str))
            if used + piece_len > limit and out:
                out.append({"_truncated": f"另有 {len(value) - len(out)} 项已省略"})
                break
            out.append(piece)
            used += piece_len
        return out
    if isinstance(value, dict):
        blob = json.dumps(value, ensure_ascii=False, default=str)
        if len(blob) <= limit:
            return value
        # 保顶层键，值再截断
        clipped = {}
        for k, v in value.items():
            clipped[k] = _clip_memory_value(v, max(120, limit // max(len(value), 1)))
        return clipped
    return value


def _observation_for_model(tool: str, data: Any) -> Any:
    """写入模型上下文的观察再压一刀，防止大 JSON 撑爆后续轮次。"""
    if not isinstance(data, dict):
        return data
    if tool == "document_map":
        clipped = json.loads(json.dumps(data, ensure_ascii=False, default=str))
        docs = clipped.get("documents")
        if isinstance(docs, list) and len(docs) > 24:
            clipped["documents"] = docs[:24]
            clipped["message"] = (
                (clipped.get("message") or "")
                + f" 目录仅展示前 24 篇，其余 {len(docs) - 24} 篇请再 document_map(document_id=…)。"
            ).strip()
        return clipped
    if tool == "digest_document":
        clipped = json.loads(json.dumps(data, ensure_ascii=False, default=str))
        digest = clipped.get("digest")
        if isinstance(digest, str) and len(digest) > 2000:
            clipped["digest"] = digest[:2000] + "…"
        headings = clipped.get("headings") or []
        if isinstance(headings, list) and len(headings) > 20:
            clipped["headings"] = headings[:20]
        return clipped
    if tool == "read_document":
        clipped = json.loads(json.dumps(data, ensure_ascii=False, default=str))
        blocks = clipped.get("blocks") or []
        for block in blocks:
            if isinstance(block, dict) and isinstance(block.get("content"), str):
                text = block["content"]
                if len(text) > 500:
                    block["content"] = text[:500] + "…"
        clipped["blocks"] = blocks
        return clipped
    if tool == "read_memory":
        clipped = json.loads(json.dumps(data, ensure_ascii=False, default=str))
        coverage = clipped.get("coverage")
        if coverage in ("single_field", "single_field_digest"):
            # 单字段：严控进对话体积（大 storyline 已在工具层改成 digest）
            if "value" in clipped and coverage == "single_field":
                clipped["value"] = _clip_memory_value(clipped.get("value"), 2200)
            return clipped
        fields = clipped.get("fields") or {}
        if isinstance(fields, dict) and coverage != "overview":
            # 兼容旧版「全字段全文」观察
            clipped["fields"] = {
                key: _clip_memory_value(val, 800) for key, val in fields.items()
            }
        clipped["message"] = (
            (clipped.get("message") or "")
            + " 完整设定在服务端暂存。更新请 propose_memory_patch(field, after, mode=\"merge\")；"
            "before 可省略。"
        ).strip()
        return clipped
    if tool == "propose_memory_patch":
        clipped = {
            key: data.get(key)
            for key in ("field", "mode", "change_count", "complete", "message", "corrected_before")
            if key in data
        }
        staged = data.get("staged_value")
        if isinstance(staged, list):
            clipped["count"] = len(staged)
            clipped["names"] = [
                item.get("name") for item in staged if isinstance(item, dict) and item.get("name")
            ][:16]
        elif isinstance(staged, dict):
            stages = staged.get("stages") if isinstance(staged.get("stages"), list) else []
            clipped["summary"] = str(staged.get("summary") or "")[:160]
            clipped["stage_titles"] = [
                item.get("title") for item in stages if isinstance(item, dict) and item.get("title")
            ][:12]
        clipped["message"] = (
            (clipped.get("message") or "")
            + " 全文已在服务端暂存，不要为了核对再 read_memory 整字段。"
        ).strip()
        return clipped
    return data


def _is_empty_model_error(err: str) -> bool:
    text = err or ""
    keys = (
        "未返回内容",
        "未返回正文",
        "未产生正文",
        "流式响应未返回正文",
        "均为空",
        "空响应",
        "content 为空",
        "模型未返回",
        "模型输出为空",
        "输出为空",
        "租约已失效",
    )
    if any(k in text for k in keys):
        return True
    # 兜底：带 [错误] 且提到空/内容的瞬时失败，一律软收尾
    if "[错误]" in text and ("空" in text or "内容" in text or "正文" in text):
        return True
    return False


_EMERGENCY_SYSTEM = """你是写作助手小墨。当前处于「空响应救援」模式：上下文已压到最小。
规则：只输出一个完整闭合的 ```json 工具动作，不要长文。
优先 finish(answer=一两句说明)；若必须改设定，只允许一次短的 propose_memory_patch(mode="merge")。
禁止 read_document / list_project / 通读全文。"""


def _build_emergency_messages(
    instruction: str,
    ctx: ProjectAgentContext,
    *,
    focus_note: Optional[str] = None,
) -> List[Dict[str, str]]:
    """极简救援上下文：丢掉巨型观察，只留指令 + 摘要便笺 + 当前步骤。"""
    messages: List[Dict[str, str]] = [{"role": "system", "content": _EMERGENCY_SYSTEM}]
    if focus_note:
        messages.append({"role": "system", "content": focus_note[:1500]})
    scratch = _digest_scratchpad(ctx)
    if scratch:
        messages.append({"role": "system", "content": scratch[:3500]})
    phase = current_phase_nudge(ctx)
    if phase:
        messages.append({"role": "system", "content": phase})
    if ctx.changes:
        messages.append({
            "role": "system",
            "content": f"已有 {len(ctx.changes)} 处暂存修改。请 finish 说明已准备的改动即可。",
        })
    messages.append({
        "role": "user",
        "content": (instruction or "请继续")[:2000],
    })
    messages.append({
        "role": "system",
        "content": (
            "请立刻给出唯一工具动作。推荐：\n"
            "```json\n"
            "{\"tool\":\"finish\",\"args\":{\"answer\":\"本轮先安全结束，请把任务拆小后继续。\"}}\n"
            "```"
        ),
    })
    return messages


def _estimate_messages_chars(messages: List[Dict[str, str]]) -> int:
    return sum(len((m.get("content") or "") if isinstance(m, dict) else "") for m in messages)


def _should_auto_compact(messages: List[Dict[str, str]]) -> bool:
    """Kimi-style：字符预算逼近上限时触发压缩（启发式，偏保守）。"""
    used = _estimate_messages_chars(messages)
    return used >= int(LIVE_CONTEXT_BUDGET_CHARS * LIVE_COMPACT_TRIGGER_RATIO)


def _digest_scratchpad(ctx: ProjectAgentContext) -> str:
    """把服务端暂存的章节摘要浓缩进压缩后的系统提示，避免丢关键事实。"""
    digests = getattr(ctx, "document_digests", None) or {}
    if not digests:
        return ""
    lines = ["【已生成的文档摘要（服务端保留，正文未进对话）】"]
    for doc_id, item in list(digests.items())[:8]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or f"文档{doc_id}"
        digest = (item.get("digest") or "")[:500]
        headings = item.get("headings") or []
        head_bits = "；".join(
            (h.get("text") or "")[:40] for h in headings[:6] if isinstance(h, dict)
        )
        lines.append(f"- id={doc_id}《{title}》摘要：{digest}")
        if head_bits:
            lines.append(f"  标题：{head_bits}")
    return "\n".join(lines)


def _compact_messages(
    messages: List[Dict[str, str]],
    *,
    reason: str,
    ctx: Optional[ProjectAgentContext] = None,
    tail: int = 6,
) -> List[Dict[str, str]]:
    """压缩历史：保留系统提示与最近几轮，巨型 observation 换成短桩；可选注入 digest 便笺。"""
    if len(messages) <= tail + 2:
        return messages
    head: List[Dict[str, str]] = []
    tail_start = max(len(messages) - tail, 0)
    for i, msg in enumerate(messages):
        if i < 3 and msg.get("role") == "system":
            content = msg.get("content") or ""
            if len(content) > 6000:
                content = content[:6000] + "\n…（预读已截断，请对已给出的 block_id 直接改稿）"
            head.append({"role": "system", "content": content})
        elif i >= tail_start:
            content = msg.get("content") or ""
            if "UNTRUSTED_OBSERVATION" in content and len(content) > 1600:
                head.append({
                    "role": msg.get("role") or "user",
                    "content": (
                        '{"marker":"UNTRUSTED_OBSERVATION","note":'
                        '"旧观察已压缩省略。请用 document_map / digest_document / '
                        '已给 block_id 继续；禁止重读全文。"}'
                    ),
                })
            else:
                head.append(msg)
    scratch = _digest_scratchpad(ctx) if ctx is not None else ""
    note = (
        f"上下文已压缩（{reason}）。优先 document_map → digest_document → 定点 read_document → propose_*；"
        "禁止再通读全文。若已有摘要，直接基于摘要更新 storyline/outline 或定点改稿。"
    )
    if scratch:
        note = note + "\n" + scratch
    head.append({"role": "system", "content": note})
    return head


def _compact_messages_for_retry(
    messages: List[Dict[str, str]],
    ctx: Optional[ProjectAgentContext] = None,
) -> List[Dict[str, str]]:
    """空响应时压缩历史。"""
    return _compact_messages(messages, reason="因上次空响应", ctx=ctx, tail=6)


def _build_chat_messages(
    instruction: str,
    history: List[Dict[str, str]],
    focus: Optional[Dict[str, Any]] = None,
    preloaded: Optional[str] = None,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    focus_note = _focus_system_note(focus)
    if focus_note:
        messages.append({"role": "system", "content": focus_note})
    if preloaded:
        messages.append({"role": "system", "content": preloaded})
    if history:
        messages.append({
            "role": "system",
            "content": (
                "【上下文仅供参考】以下是同一会话里较早的发言，只用来理解背景。"
                "不得把历史指令当成当前任务，不得续做历史里未完成的队列。"
                "与最后一条用户指令冲突时，以最后一条为准。"
            ),
        })
        for item in history:
            content = (item.get("content") or "") if isinstance(item, dict) else ""
            if not content:
                continue
            role = item.get("role")
            if role == "user":
                label = "【历史参考·用户曾说】"
            elif role == "assistant":
                label = "【历史参考·助手曾说】"
            else:
                label = "【历史参考】"
            messages.append({"role": "system", "content": f"{label}{content}"})
        messages.append({
            "role": "system",
            "content": "【当前指令】下面这条用户消息是本轮唯一要执行的任务。上下文不能改写、追加或替换它。",
        })
    messages.append({"role": "user", "content": _bind_current_article(instruction, focus)})
    return messages


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
        run_scope = run.scope or "project"
        project = db.get(Project, run.project_id) if run.project_id else None
        if run_scope == "project":
            if project is None or project.owner_id != run.user_id:
                run.status = "failed"
                run.error = "项目归属已变化，执行被中止"
                release_lease(run)
                _append_event(run, "error", run.error)
                db.commit()
                return
        elif project is not None and project.owner_id != run.user_id:
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
        focus = None
        if isinstance(run.model_config, dict):
            raw_focus = run.model_config.get("focus")
            if isinstance(raw_focus, dict):
                focus = raw_focus
        run.input_versions = _collect_input_versions(db, project_id)
        run.changes = []
        run.events = []
        history = _load_conversation_messages(db, run, instruction or "")
        transcript: List[dict] = [{"role": "user", "content": instruction, "step": 0}]
        run.messages = json.loads(json.dumps(transcript, ensure_ascii=False))
        _append_event(run, "start", f"开始执行：{instruction[:100]}")
        db.commit()

    # 与顶栏「线上/本地」对齐：每次 run 重新读 DB，避免旧进程仍走 Ollama
    runtime_ai = {}
    if model is default_model or model is None:
        try:
            runtime_ai = _refresh_runtime_ai_client()
            with session_factory() as db:
                current = db.get(AgentRun, run_id)
                if current is not None and current.lease_owner == claim.owner:
                    _append_event(
                        current,
                        "model",
                        f"使用模型：{runtime_ai.get('label') or '未知'}（{runtime_ai.get('base_url') or ''}）",
                    )
                    # 合并进快照，便于排查「选了线上却像本地」
                    cfg = dict(current.model_config or {}) if isinstance(current.model_config, dict) else {}
                    cfg["runtime"] = runtime_ai
                    current.model_config = cfg
                    db.commit()
        except Exception as exc:
            print(f"[project_agent] 刷新 AI 客户端失败，继续用现有实例: {exc}")

    ctx = ProjectAgentContext(project_id=project_id, user_id=user_id)
    ctx.instruction = instruction or ""
    ctx.scope = run_scope
    preloaded = None
    if focus and focus.get("document_id") and project_id:
        try:
            ctx.focus_document_id = int(focus["document_id"])
        except (TypeError, ValueError):
            ctx.focus_document_id = None
        with session_factory() as db:
            preloaded = _preload_focus_document(db, ctx, focus)
        if preloaded:
            _append_focus_event = preloaded.split("\n", 1)[0][:180]
            with session_factory() as db:
                current = db.get(AgentRun, run_id)
                if current is not None and current.lease_owner == claim.owner:
                    _append_event(current, "read", _append_focus_event)
                    db.commit()
    messages = _build_chat_messages(instruction, history, focus=focus, preloaded=preloaded)
    work_plan = infer_work_plan(instruction)
    if work_plan:
        ctx.work_plan = work_plan
        ctx.work_plan_index = 0
        messages.append({"role": "system", "content": work_plan_system_note(work_plan)})
        nudge = current_phase_nudge(ctx)
        if nudge:
            messages.append({"role": "system", "content": nudge})
    if not project_id:
        messages.insert(
            1,
            {
                "role": "system",
                "content": (
                    "【无项目会话】用户尚未打开项目。可先专项写作或讨论；"
                    "要写入正文/设定前必须 create_project(title=...)。"
                    "创建后本轮即绑定该项目。"
                ),
            },
        )

    # 有项目时后台预读 list_project + read_memory，避免模型首轮「先读设定」空转/撑爆上下文
    if project_id and not _focus_has_selection(focus):
        try:
            with session_factory() as db:
                for tool_name, tool_args in (
                    ("list_project", {}),
                    ("read_memory", {}),
                ):
                    data = execute_tool(ctx, db, tool_name, tool_args)
                    messages.append({
                        "role": "assistant",
                        "content": json.dumps(
                            {"tool": tool_name, "args": tool_args},
                            ensure_ascii=False,
                        ),
                    })
                    messages.append({
                        "role": "user",
                        "content": json.dumps(
                            {
                                "marker": "UNTRUSTED_OBSERVATION",
                                "tool": tool_name,
                                "args": tool_args,
                                "step": 0,
                                "data": _observation_for_model(tool_name, data),
                                "prewarm": True,
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    })
                    advance_work_plan(ctx, tool_name, tool_args)
            if generation_forbids_settings_edits(instruction):
                pre_note = (
                    "【后台已预读】文档列表与设定概览只供生成文章使用。"
                    "禁止 propose_memory_patch。请按当前指令生成文章，然后 finish。"
                )
            elif not looks_like_settings_edit_instruction(instruction):
                pre_note = (
                    "【后台已预读】文档列表与设定概览只供参考。"
                    "当前指令没有要求改设定，禁止 propose_memory_patch。"
                    "只执行用户这条指令，做完 finish。"
                )
            else:
                pre_note = (
                    "【后台已预读】文档列表与设定概览已在上方。"
                    "只改当前指令点名的设定字段，每次 1 个 field，不要改其他字段。"
                    "做完 finish。"
                )
            messages.append({"role": "system", "content": pre_note})
            nudge = current_phase_nudge(ctx)
            if nudge:
                messages.append({"role": "system", "content": nudge})
            with session_factory() as db:
                current = db.get(AgentRun, run_id)
                if current is not None and current.lease_owner == claim.owner:
                    _append_event(current, "read", "后台预读：list_project + read_memory")
                    db.commit()
        except Exception as exc:
            print(f"[project_agent] 预读项目上下文失败，继续由模型自行读取: {exc}")

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
        nonlocal project_id
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if (current is None or current.lease_until is None
                    or current.lease_until < datetime.utcnow()
                    or not renew_lease(db, current, claim.owner)):
                return False
            # create_project 即时落库后回填 run.project_id，供 apply / 前端导航
            if ctx.project_id and current.project_id != ctx.project_id:
                current.project_id = ctx.project_id
                project_id = ctx.project_id
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
        """Complete explicit finish-tool turns through a fenced write.

        有修改时先落为 proposed，再立即自动 apply 写入项目；失败则保留 proposed 供手动确认。
        """
        nonlocal project_id
        upsert_assistant(step, _safe_assistant_content(said or answer), streaming=False)
        auto_apply_id: Optional[str] = None
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            now = datetime.utcnow()
            if (current is None or current.status != "running"
                    or current.lease_owner != claim.owner or current.lease_until is None
                    or current.lease_until < now):
                return
            if ctx.project_id and current.project_id != ctx.project_id:
                current.project_id = ctx.project_id
                project_id = ctx.project_id
            effective_pid = ctx.project_id or project_id or current.project_id
            project = db.get(Project, effective_pid) if effective_pid else None
            # 仅提案文档/设定时必须有项目；created_project 本身已即时落库
            needs_project = any(
                isinstance(c, dict) and c.get("kind") not in ("created_project",)
                for c in (ctx.changes or [])
            )
            if needs_project and (project is None or project.owner_id != user_id):
                current.status = "failed"
                current.error = (
                    "尚未创建或绑定项目，无法写入文档/设定。请先 create_project。"
                    if not effective_pid
                    else "项目归属已变化，执行被中止"
                )
                current.changes = []
                _append_event(current, "error", current.error)
            elif (not needs_project) and effective_pid and (
                project is None or project.owner_id != user_id
            ):
                current.status = "failed"
                current.error = "项目归属已变化，执行被中止"
                current.changes = []
                _append_event(current, "error", current.error)
            else:
                current.messages = json.loads(json.dumps(transcript, ensure_ascii=False))
                current.answer = answer
                current.changes = _dump_changes(ctx)
                if ctx.changes:
                    current.status = "proposed"
                    # 含删除提案时禁止自动 apply，必须用户显式确认
                    if not _changes_require_user_confirm(ctx.changes):
                        auto_apply_id = current.id
                else:
                    current.status = "completed"
                _append_event(current, "finish", _safe_assistant_content(answer) or "完成")
            release_lease(current)
            db.commit()
        if auto_apply_id:
            _auto_apply_run(session_factory, auto_apply_id)

    # ---- 工具循环（仅显式 finish 可成功结束，纯文字继续推进） ----
    consecutive_text_turns = 0
    violation_turns = 0
    empty_model_turns = 0

    def feedback_violation(message: str, raw_text: Optional[str], tool_name: Optional[str], tool_args: Any) -> bool:
        """可纠正违规：把错误作为观察反馈给模型自我修正。返回 False 表示超过重试上限，须终止。"""
        nonlocal violation_turns
        violation_turns += 1
        if violation_turns > MAX_VIOLATION_RETRIES:
            return False
        # 必须回传原始输出，否则模型不知道上一轮 JSON 哪里坏了
        messages.append({"role": "assistant", "content": raw_text or json.dumps({"error": message}, ensure_ascii=False)})
        has_selection = bool(getattr(ctx, "focus_block_ids", None))
        if "未闭合" in message or "截断" in message or "提案过大" in message:
            fix_hint = (
                "上一轮工具 JSON 过大或被截断。请立刻用更小的动作重试："
                "先 propose_memory_patch 只改 1 个 field，或 propose_create_document 只写短大纲；"
                "必须输出完整闭合的 ```json … ```，不要一次塞多字段/长章节。"
            )
        elif "不是合法 JSON" in message or "动作代码块" in message:
            fix_hint = (
                "请原样重写末尾 ```json 动作；字符串字段内的引号用 \\ \" 转义，正文不要改成「」『』；"
                "不要省略逗号。选区已锁定时直接 propose_block_rewrite，不要 read_document。"
            )
        elif has_selection:
            fix_hint = (
                "选区目标已锁定，禁止再 read_document / 追问是哪几段；"
                "请立刻 propose_block_rewrite。修改设定前请先 read_memory。"
            )
        else:
            fix_hint = "修改正文前请先 read_document，修改设定前请先 read_memory。"
        observation = {
            "marker": "UNTRUSTED_OBSERVATION",
            "tool": tool_name or "unknown",
            "args": tool_args if isinstance(tool_args, dict) else {},
            "error": message,
            "data": {
                "ok": False,
                "complete": True,
                "message": f"工具调用被拒绝：{message}。请修正后重新调用；{fix_hint}",
            },
        }
        messages.append(
            {"role": "user", "content": json.dumps(observation, ensure_ascii=False, default=str)}
        )
        if has_selection and (
            "不是合法 JSON" in message
            or "动作代码块" in message
            or tool_name in (None, "unknown", "read_document", "finish")
        ):
            messages.append({"role": "system", "content": _focus_targets_reminder(ctx)})
        persist_progress("error", f"工具被拒绝：{message[:250]}")
        return True

    def feedback_empty_model(err: str, partial: str = "") -> bool:
        """空响应/超时救援：优先带着已生成草稿续写；勿丢掉 ctx.changes。"""
        nonlocal empty_model_turns, messages
        empty_model_turns += 1
        if empty_model_turns > MAX_EMPTY_MODEL_RETRIES:
            return False

        draft = (partial or "").strip()
        # 草稿落进对话 UI，用户能看到「已生成、在续写」
        if draft:
            upsert_assistant(step, _safe_assistant_content(draft), streaming=False)
            persist_transcript()

        # 有半成品：不要核爆清空上下文，只轻量压缩后要求续写补全
        if draft and empty_model_turns <= MAX_EMPTY_MODEL_RETRIES:
            if _should_auto_compact(messages):
                messages = _compact_messages(
                    messages, reason="超时后续写前压缩", ctx=ctx, tail=LIVE_COMPACT_TAIL_MESSAGES,
                )
            messages.append({"role": "assistant", "content": draft})
            keep = (
                f"服务端已保留 {len(ctx.changes)} 处暂存修改。"
                if ctx.changes else ""
            )
            messages.append({
                "role": "system",
                "content": (
                    "上一轮因超时或不完整中断，上面是已生成的草稿。"
                    "请【接着草稿继续】，补全并输出一个完整闭合的 ```json 工具动作；"
                    f"不要从零重写已说的话。{keep}"
                ),
            })
            persist_progress("info", f"超时续写：保留草稿 {len(draft)} 字（{empty_model_turns}/{MAX_EMPTY_MODEL_RETRIES}）")
            return True

        if empty_model_turns >= 2:
            focus_note = _focus_system_note(focus) if focus else None
            messages = _build_emergency_messages(
                instruction, ctx, focus_note=focus_note,
            )
            if draft:
                messages.insert(-1, {"role": "assistant", "content": draft[:4000]})
            persist_progress(
                "info",
                f"空响应极简救援（{empty_model_turns}/{MAX_EMPTY_MODEL_RETRIES}）"
                + (f"·保留草稿 {len(draft)} 字" if draft else ""),
            )
        else:
            messages = _compact_messages_for_retry(messages, ctx=ctx)
            phase = current_phase_nudge(ctx)
            phase_line = f"\n{phase}" if phase else ""
            keep = f"已保留 {len(ctx.changes)} 处暂存修改。" if ctx.changes else ""
            messages.append({
                "role": "system",
                "content": (
                    "上一轮模型未返回可用正文（可能是等待超时）。"
                    f"{keep}"
                    "请只输出一个短的 ```json 工具动作；优先 finish 或一次短 merge。"
                    "禁止通读正文。"
                    f"{phase_line}"
                ),
            })
            persist_progress(
                "info",
                f"空响应已压缩重试（{empty_model_turns}/{MAX_EMPTY_MODEL_RETRIES}）",
            )
        return True

    def soft_finish_after_empty(err: str) -> None:
        """空响应耗尽：安全结束为 completed/proposed，绝不标 failed，不写 run.error。"""
        persist_progress("info", f"空响应安全结束：{(err or '')[:120]}")
        drafted = ""
        for message in reversed(transcript):
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            content = _safe_assistant_content(message.get("content") or "")
            if len(content) >= 40 and "安全结束" not in content:
                drafted = content
                break
        if ctx.changes:
            answer = (
                drafted
                or (
                    f"已准备 {len(ctx.changes)} 处修改（上下文较长，已拆开写入）。"
                    "可在对话里确认或撤销；剩下的部分说「继续」即可。"
                )
            )
        elif drafted:
            # 已有可用说明时，不要用「空响应」套话盖掉
            answer = drafted
        else:
            answer = (
                "本轮已安全结束（模型暂时没有返回可用内容，多半是上下文过长）。"
                "请拆小再试：「先更新故事线」「只改 outline」「只润色第 1 章」。"
                "不必先通读全部章节。"
            )
        upsert_assistant(step, _safe_assistant_content(answer), streaming=False)
        finalize_turn(step, answer, None)
        # finalize 若因租约瞬时失效未落盘，强制收尾并清空 error
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if current is None:
                return
            if current.lease_owner == claim.owner and current.status in (
                "running", "failed",
            ):
                current.status = "proposed" if ctx.changes else "completed"
                current.answer = answer
                current.error = None  # 关键：不要让前端显示红色失败
                current.changes = _dump_changes(ctx)
                current.messages = json.loads(json.dumps(transcript, ensure_ascii=False, default=str))
                release_lease(current)
                _append_event(current, "finish", "空响应安全结束")
                db.commit()
                if current.status == "proposed" and not _changes_require_user_confirm(current.changes):
                    _auto_apply_run(session_factory, run_id)
            elif current.status == "failed" and "未返回" in (current.error or ""):
                # 其它路径误标 failed 时纠偏
                current.status = "completed"
                current.error = None
                current.answer = answer
                release_lease(current)
                db.commit()

    def heartbeat() -> bool:
        """模型长调用期间续租，防止 120s 租约过期后软收尾失败。"""
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if current is None or current.status != "running" or current.lease_owner != claim.owner:
                return False
            ok = renew_lease(db, current, claim.owner)
            if ok:
                db.commit()
            return ok

    step = 0
    # 同一条回复里的后续工具（如先 patch 再 finish）排队执行，不再另起一轮模型
    pending_actions: List[dict] = []
    while True:
        step += 1
        with session_factory() as db:
            current = db.get(AgentRun, run_id)
            if current is None or current.status != "running" or current.lease_owner != claim.owner:
                return  # 执行中被取消/接管

        if step in STEP_FINISH_NUDGE_AT:
            draft_n = len(getattr(ctx, "writing_drafts", {}) or {})
            writing_hint = ""
            if draft_n and not ctx.changes:
                writing_hint = (
                    f"专项写作已有 {draft_n} 份草稿未提案："
                    "请立刻 propose_writing_draft / propose_story_settings，再 finish。"
                )
            elif draft_n:
                writing_hint = "若草稿尚未 propose，请先 propose_writing_draft / propose_story_settings。"
            messages.append({
                "role": "system",
                "content": (
                    f"已执行 {step} 步。请尽快收尾：优先把已改好的块 propose_block_rewrite（若还没提），"
                    f"然后 finish；不要为「再通读一遍」继续空转。"
                    + (f"当前已有 {len(ctx.changes)} 处暂存修改。" if ctx.changes else "")
                    + writing_hint
                ),
            })
            persist_progress(
                "info",
                f"步数提醒：已执行 {step} 步"
                + ("（专项写作进行中）" if draft_n else "")
                + "，请尽快 finish",
            )

        if step > SAFETY_STEP_CEILING:
            # 安全阀：不报「超过最大步数」失败，尽量提交已有成果
            if ctx.changes:
                finalize_turn(
                    step,
                    f"已连续执行 {step} 步，为避免过长占用先提交当前 {len(ctx.changes)} 处修改；"
                    f"未完成部分可再说「继续」。",
                    None,
                )
            else:
                finalize_turn(
                    step,
                    f"已连续执行 {step} 步仍无可用修改。请缩小范围（如选中段落 / 先改开头几段）再试。",
                    None,
                )
            return

        # Kimi-style 主动压缩：逼近上下文预算时折叠旧观察，保留 digest 便笺
        if _should_auto_compact(messages):
            before = _estimate_messages_chars(messages)
            messages = _compact_messages(
                messages,
                reason="上下文预算将满",
                ctx=ctx,
                tail=LIVE_COMPACT_TAIL_MESSAGES,
            )
            after = _estimate_messages_chars(messages)
            persist_progress(
                "info",
                f"上下文自动压缩：{before}→{after} 字（预算 {LIVE_CONTEXT_BUDGET_CHARS}）",
            )

        stream_state = {"chunks": [], "last_flush": 0.0}
        partial_bag: Dict[str, str] = {"text": ""}

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

        def _collect_partial(exc: Optional[BaseException] = None) -> str:
            from_stream = "".join(stream_state["chunks"]).strip()
            from_bag = (partial_bag.get("text") or "").strip()
            from_exc = ""
            if isinstance(exc, PartialModelError):
                from_exc = (exc.partial or "").strip()
            # 取最长的一份草稿
            return max([from_stream, from_bag, from_exc], key=len)

        queued = pending_actions.pop(0) if pending_actions else None
        raw = ""
        action = None
        said = None
        if queued is not None:
            # 同一条回复里拆出的后续任务，不再重新问模型
            action = queued
            raw = json.dumps(queued, ensure_ascii=False)
        else:
            # 长等待期间每 45s 续租，避免 120s 租约在模型思考时过期被当成失败
            async def _lease_keepalive():
                while True:
                    await asyncio.sleep(45)
                    if not heartbeat():
                        return

            keepalive = asyncio.create_task(_lease_keepalive())
            try:
                raw = await _call_model(
                    model,
                    messages,
                    on_delta=on_delta,
                    on_heartbeat=heartbeat,
                    partial_out=partial_bag,
                )
                action, said = _parse_action_and_message(raw)
                empty_model_turns = 0  # 成功产出后重置空响应计数
            except ToolViolation as e:
                err = str(e)
                partial = _collect_partial(e)
                if partial and not raw:
                    raw = partial
                if _is_empty_model_error(err) or "输出为空" in err:
                    if feedback_empty_model(err, partial=partial):
                        continue
                    soft_finish_after_empty(err)
                    return
                truncated = ("未闭合" in err) or ("截断" in err) or ("提案过大" in err)
                if truncated:
                    enable_narrow_mode(ctx)
                # 截断时把半成品当 raw 回传，下一轮可续写
                if not feedback_violation(err, raw or partial or None, None, None):
                    # 已有暂存或确为空响应时收尾；非法工具/坏 JSON 仍判失败
                    if ctx.changes or _is_empty_model_error(err):
                        soft_finish_after_empty(err)
                    else:
                        fail(err, clear_changes=True)
                    return
                if truncated:
                    nudge = current_phase_nudge(ctx)
                    if nudge:
                        messages.append({"role": "system", "content": nudge})
                continue
            except Exception as e:
                err = str(e)
                partial = _collect_partial(e)
                # 半成品若已是完整动作，直接采纳，不重来
                if partial:
                    try:
                        action, said = _parse_action_and_message(partial)
                        raw = partial
                        empty_model_turns = 0
                        upsert_assistant(step, _safe_assistant_content(said or partial), streaming=False)
                        persist_transcript()
                    except ToolViolation as ve:
                        ve_err = str(ve)
                        truncated = ("未闭合" in ve_err) or ("截断" in ve_err)
                        if truncated:
                            enable_narrow_mode(ctx)
                            if feedback_violation(ve_err, partial, None, None):
                                continue
                        if _is_empty_model_error(err) and feedback_empty_model(err, partial=partial):
                            continue
                        if ctx.changes or _is_empty_model_error(err):
                            soft_finish_after_empty(err)
                        else:
                            fail(ve_err, clear_changes=True)
                        return
                elif _is_empty_model_error(err) and feedback_empty_model(err):
                    continue
                elif ctx.changes or _is_empty_model_error(err):
                    soft_finish_after_empty(err)
                    return
                else:
                    fail(err, clear_changes=False)
                    return
            finally:
                keepalive.cancel()
                try:
                    await keepalive
                except (asyncio.CancelledError, Exception):
                    pass

        # 一条回复里的多个工具按顺序排队（先写入、再 finish），避免只执行第一个或整段被丢掉
        if queued is None and isinstance(raw, str) and raw:
            found = _collect_tool_actions(raw)
            if action is None and found:
                action = found[0]
                said = _strip_embedded_tool_json(raw) or said
            if isinstance(action, dict) and found:
                primary_key = json.dumps(action, ensure_ascii=False, sort_keys=True, default=str)
                skipped = False
                for extra in found:
                    key = json.dumps(extra, ensure_ascii=False, sort_keys=True, default=str)
                    if not skipped and key == primary_key:
                        skipped = True
                        continue
                    pending_actions.append(extra)

        if action is None:
            upsert_assistant(step, _safe_assistant_content(said), streaming=False)
            if not persist_transcript():
                return
            consecutive_text_turns += 1
            if consecutive_text_turns >= MAX_CONSECUTIVE_TEXT_TURNS:
                if ctx.changes:
                    soft_finish_after_empty("模型连续未提供工具动作")
                else:
                    fail("模型连续未提供工具动作", clear_changes=True)
                return
            messages.append({"role": "assistant", "content": said or ""})
            if looks_like_read_all_plan(said or ""):
                messages.append({
                    "role": "system",
                    "content": (
                        "【打断】禁止通读全部章节，也禁止索要 storyline/outline「完整全文」。"
                        "不要因此改设定。只做当前指令写明的事；"
                        "长文需要目录时用 document_map → digest_document。末尾给出一个完整 ```json 工具动作。"
                    ),
                })
            elif getattr(ctx, "focus_block_ids", None) and (
                _asks_which_blocks(said) or consecutive_text_turns >= 1
            ):
                messages.append({"role": "system", "content": _focus_targets_reminder(ctx)})
            else:
                messages.append({
                    "role": "system",
                    "content": "刚才仅为文字说明，任务尚未结束。请依据用户目标继续执行，"
                               "在回复末尾提供一个 JSON 工具动作；需要阅读就调用 read_document，"
                               "需要修改就实际提出提案。只有任务确已完成或必须等待用户澄清时，"
                               "才调用 finish，并给出结果或具体问题。"
                               "梳理故事线时不要先读完全部章节。",
                })
            continue

        consecutive_text_turns = 0
        # 本轮自然语言回复定稿（替换流式期间的增量文本）
        if said:
            upsert_assistant(step, _safe_assistant_content(said), streaming=False)
            if not persist_transcript():
                return

        tool = action.get("tool")
        args = action.get("args")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            if not feedback_violation("工具参数必须是对象", raw, tool, {}):
                fail("工具参数必须是对象", clear_changes=True)
                return
            continue
        # 模型常把参数写在顶层：{"tool":"read_memory","field":"storyline"}
        args = dict(args)
        for key, value in action.items():
            if key in ("tool", "args"):
                continue
            if key not in args:
                args[key] = value
        # finish 缺 answer / answer 为 null 时，用当轮自然语言兜底，避免整次 run 失败
        if tool == "finish":
            args = dict(args)
            answer = args.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                args["answer"] = (said or "").strip() or "已完成"
            # 选区已锁定却用 finish 追问「哪几段」→ 拒绝并重钉目标
            if getattr(ctx, "focus_block_ids", None) and (
                _asks_which_blocks(args.get("answer")) or _asks_which_blocks(said)
            ):
                if not feedback_violation(
                    "选区目标已锁定，禁止用 finish 追问是哪几段；请直接 propose_block_rewrite",
                    raw,
                    "finish",
                    args,
                ):
                    fail("选区目标已锁定却追问段落，任务未完成", clear_changes=True)
                    return
                continue
        # 选区润色场景：禁止再通读，直接把目标块交回去逼模型改写
        if tool == "read_document" and getattr(ctx, "focus_block_ids", None):
            doc_id = ctx.focus_document_id
            blocks = (ctx.read_documents.get(doc_id) or []) if doc_id else []
            by_id = {
                str(b.get("id")): b
                for b in blocks
                if isinstance(b, dict) and b.get("id") is not None
            }
            targets = [by_id[i] for i in ctx.focus_block_ids if i in by_id]
            data = {
                "document_id": doc_id,
                "title": ctx.document_titles.get(doc_id or 0, ""),
                "complete": True,
                "message": (
                    "选区正文已在上下文中，禁止再次 read_document。"
                    "请立刻对下列 block_id 调用 propose_block_rewrite。"
                ),
                "blocks": [
                    {
                        "id": b.get("id"),
                        "type": b.get("type"),
                        "content": (b.get("content") or "")[:1200],
                    }
                    for b in targets
                ],
            }
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": json.dumps(
                    {
                        "marker": "UNTRUSTED_OBSERVATION",
                        "tool": tool,
                        "args": args,
                        "step": step,
                        "data": data,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            })
            if not persist_progress("tool", "read_document skipped(focus selection)"):
                return
            continue
        try:
            if tool == "generate_documents_from_settings":
                from app.services.project_agent_tools import (
                    _validate_args,
                    generate_documents_from_settings,
                )
                resolved = _validate_args(tool, args)

                async def _gen_keepalive():
                    while True:
                        await asyncio.sleep(45)
                        if not heartbeat():
                            return

                gen_keepalive = asyncio.create_task(_gen_keepalive())
                try:
                    data = await generate_documents_from_settings(
                        session_factory,
                        ctx,
                        resolved,
                        on_progress=lambda note: persist_progress("tool", note),
                    )
                finally:
                    gen_keepalive.cancel()
                    try:
                        await gen_keepalive
                    except (asyncio.CancelledError, Exception):
                        pass
            else:
                with session_factory() as db:
                    data = execute_tool(ctx, db, tool, args)
        except ToolViolation as e:
            # 未先读、old_text 不匹配、越权等：反馈给模型自我修正，连续超限才判失败
            err = str(e)
            if "提案过大" in err and tool == "propose_memory_patch":
                pieces = _split_memory_patch_actions({"tool": tool, "args": args, **{
                    k: action.get(k) for k in ("field", "after", "mode", "reason") if k not in args
                }})
                if len(pieces) > 1:
                    pending_actions[:0] = pieces
                    persist_progress("info", f"设定提案过大，已拆成 {len(pieces)} 个小任务继续")
                    continue
            if "提案过大" in err:
                enable_narrow_mode(ctx)
            if not feedback_violation(err, raw, tool, args):
                if "提案过大" in err and ctx.changes:
                    soft_finish_after_empty(err)
                    return
                fail(err, clear_changes=True)
                return
            if "提案过大" in err:
                nudge = current_phase_nudge(ctx)
                if nudge:
                    messages.append({"role": "system", "content": nudge})
            continue
        except Exception as e:
            fail(f"工具执行异常: {e}", clear_changes=False)
            return
        violation_turns = 0

        # 模型上下文只留「已执行某工具」，不回放整段设定 JSON，避免下一步被撑空。
        # read_document 观察写入前再截断，避免 90+ 块把后续轮次撑空。
        model_said = raw if isinstance(raw, str) else ""
        if len(model_said) > 500 and _collect_tool_actions(model_said):
            prose = _strip_embedded_tool_json(model_said)
            model_said = ((prose[:240] + "\n") if prose else "") + f"已执行 {tool}。"
        messages.append({"role": "assistant", "content": model_said or f"已执行 {tool}。"})
        observation = {
            "marker": "UNTRUSTED_OBSERVATION",
            "tool": tool,
            "args": args,
            "step": step,
            "data": _observation_for_model(tool, data),
        }
        messages.append(
            {"role": "user", "content": json.dumps(observation, ensure_ascii=False, default=str)}
        )

        if tool == "finish":
            # answer 缺省时用当轮自然语言回复兜底；两者皆空才退到默认总结
            finalize_turn(step, ctx.finish_answer or said or "已完成", said if said is not None else None)
            return

        # 后台分步：匹配当前队列项则推进，并钉扎下一步
        if advance_work_plan(ctx, tool, args if isinstance(args, dict) else {}):
            nudge = current_phase_nudge(ctx)
            if nudge:
                messages.append({"role": "system", "content": nudge})
            elif ctx.work_plan and ctx.work_plan_index >= len(ctx.work_plan):
                messages.append({
                    "role": "system",
                    "content": "分步队列已全部完成。请 finish 用中文总结本轮改动；勿再塞大段新提案。",
                })

        summary = {"tool": tool, "change_count": len(ctx.changes)}
        if not persist_progress("tool", f"{tool} {json.dumps(summary, ensure_ascii=False)}"):
            return


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

def _changes_require_user_confirm(changes: Optional[List]) -> bool:
    """删除类提案必须用户显式确认，禁止自动 apply。"""
    for change in changes or []:
        if isinstance(change, dict) and change.get("kind") == "delete_document":
            return True
    return False


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
        field = change["field"]
        current = coerce_memory_field(field, getattr(memory, field, None))
        expected = coerce_memory_field(field, change["before"])
        if _norm(current) != _norm(expected):
            raise HTTPException(status_code=409, detail=f"设定字段 {field} 已被修改，存在版本冲突")
    elif kind == "create_document":
        return
    elif kind == "created_project":
        # 已在工具内即时创建，apply 仅作记录
        return
    elif kind == "delete_document":
        document = _owned_document(db, run, change["document_id"])
        before = change.get("before") or {}
        expected_title = before.get("title")
        if expected_title is not None and document.title != expected_title:
            raise HTTPException(
                status_code=409,
                detail=f"《{document.title}》在提案后被改名或替换，存在版本冲突，无法删除",
            )
        expected_content = before.get("content")
        if expected_content is not None and _norm(document.content or []) != _norm(expected_content):
            raise HTTPException(
                status_code=409,
                detail=f"《{document.title or change.get('title')}》在提案后被编辑，存在版本冲突，无法删除",
            )
        child_count = (
            db.query(Document)
            .filter(Document.parent_id == document.id, Document.project_id == run.project_id)
            .count()
        )
        if child_count:
            raise HTTPException(
                status_code=409,
                detail=f"《{document.title}》下还有 {child_count} 个子文档，无法删除",
            )
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
        field = change["field"]
        value = coerce_memory_field(field, change["after"])
        change["after"] = json.loads(json.dumps(value, ensure_ascii=False, default=str))
        setattr(memory, field, value)
        _bump_updated_at(memory)
    elif kind == "created_project":
        return
    elif kind == "create_document":
        from app.utils.document_format import parse_formatted_text_to_blocks

        after = change["after"] or {}
        max_order = (
            db.query(Document)
            .filter(Document.project_id == run.project_id)
            .order_by(Document.order_index.desc())
            .first()
        )
        existing_id = change.get("target_id")
        if existing_id:
            existing = db.get(Document, existing_id)
            if existing is not None and existing.project_id == run.project_id:
                return
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
    elif kind == "delete_document":
        document = _owned_document(db, run, change["document_id"])
        doc_id = document.id
        from app.services.document_service import delete_document_with_dependents
        delete_document_with_dependents(db, document)
        db.flush()
        try:
            from app.services.fulltext_search_service import fulltext_search_service

            fulltext_search_service.remove_document(doc_id)
        except Exception as exc:
            print(f"[project_agent] 删除文档后清理检索索引失败: {exc}")


def _apply(db, run: AgentRun, *, auto: bool = False):
    if run.status == "applied":
        return  # 幂等：重复 apply 安全
    if run.status != "proposed":
        raise HTTPException(status_code=409, detail=f"当前状态 {run.status} 不可应用修改")
    # 深拷贝：_apply_change 会原地修改 change（如回填 create 的 target_id），
    # 若直接引用 run.changes 的实时 JSON 对象，赋值时会因值相等而被 ORM 判定未变更
    changes = json.loads(json.dumps(run.changes or [], ensure_ascii=False, default=str))
    if auto and _changes_require_user_confirm(changes):
        # 防御：自动路径绝不执行删除
        return
    for change in changes:
        _check_change_apply(db, run, change)  # 第一遍全量校验，任一冲突即拒绝且不变更任何目标
    for change in changes:
        _apply_change(db, run, change)
    run.changes = json.loads(json.dumps(changes, ensure_ascii=False, default=str))
    run.status = "applied"
    label = "已自动替换" if auto else "已应用"
    _append_event(run, "apply", f"{label} {len(changes)} 项修改")
    db.commit()


def _auto_apply_run(session_factory: sessionmaker, run_id: str) -> None:
    """finish 后立刻写入项目；冲突时保留 proposed，前端仍可手动确认。"""
    try:
        with session_factory() as db:
            run = db.get(AgentRun, run_id)
            if run is None or run.status != "proposed" or not (run.changes or []):
                return
            if _changes_require_user_confirm(run.changes):
                return
            _apply(db, run, auto=True)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        try:
            with session_factory() as db:
                run = db.get(AgentRun, run_id)
                if run is None or run.status != "proposed":
                    return
                _append_event(
                    run,
                    "error",
                    f"自动替换失败：{detail}。可点「确认写入」重试，或缩小改动范围。",
                )
                db.commit()
        except Exception as nested:
            print(f"[project_agent] 记录自动替换失败时出错: {nested}")
    except Exception as exc:
        print(f"[project_agent] 自动替换异常: {exc}")
        try:
            with session_factory() as db:
                run = db.get(AgentRun, run_id)
                if run is None or run.status != "proposed":
                    return
                _append_event(run, "error", f"自动替换异常：{exc}。可点「确认写入」重试。")
                db.commit()
        except Exception:
            pass


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
        field = change["field"]
        current = coerce_memory_field(field, getattr(memory, field, None))
        expected = coerce_memory_field(field, change["after"])
        if _norm(current) != _norm(expected):
            raise HTTPException(status_code=409, detail=f"设定字段 {field} 已被修改，无法撤销")
    elif kind == "created_project":
        return  # 项目创建不随撤销删除
    elif kind == "create_document":
        document = db.get(Document, change.get("target_id")) if change.get("target_id") else None
        if document is None:
            return  # 文档已不存在（可能被删除），视为已回滚
        after = change.get("after") or {}
        if document.title != after.get("title"):
            raise HTTPException(status_code=409, detail="该文档在创建后被人工修改，拒绝删除，无法撤销")
    elif kind == "delete_document":
        # 删除已生效：文档应不存在；若同 id 被重建则拒绝覆盖
        doc_id = change.get("document_id") or change.get("target_id")
        existing = db.get(Document, doc_id) if doc_id else None
        if existing is not None and existing.project_id == run.project_id:
            raise HTTPException(
                status_code=409,
                detail="该文档已被重新创建或恢复，无法自动撤销删除（避免覆盖）",
            )
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
        field = change["field"]
        value = coerce_memory_field(field, change["before"])
        setattr(memory, field, value)
        _bump_updated_at(memory)
    elif kind == "created_project":
        return
    elif kind == "create_document":
        document = db.get(Document, change.get("target_id")) if change.get("target_id") else None
        if document is not None:
            from app.services.document_service import delete_document_with_dependents
            delete_document_with_dependents(db, document)
    elif kind == "delete_document":
        before = change.get("before") or {}
        original_id = change.get("document_id") or change.get("target_id")
        document = Document(
            project_id=run.project_id,
            title=before.get("title") or "未命名",
            content=json.loads(json.dumps(before.get("content") or [], ensure_ascii=False)),
            parent_id=before.get("parent_id"),
            order_index=before.get("order_index") or 0,
        )
        # 原 id 空闲时原样恢复，避免侧栏/编辑器仍指向已删 id
        if original_id is not None and db.get(Document, original_id) is None:
            document.id = int(original_id)
        db.add(document)
        db.flush()
        change["restored_document_id"] = document.id
        change["target_id"] = document.id
        change["document_id"] = document.id


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
    run.changes = json.loads(json.dumps(changes, ensure_ascii=False, default=str))
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
