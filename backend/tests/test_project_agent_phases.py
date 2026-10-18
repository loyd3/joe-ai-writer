"""后台分步编排：复杂指令推断、体积上限、推进逻辑。"""
from app.services.project_agent_phases import (
    MAX_MEMORY_PATCH_CHARS,
    advance_work_plan,
    check_propose_payload_size,
    current_phase_nudge,
    enable_narrow_mode,
    infer_work_plan,
    looks_complex_instruction,
    work_plan_system_note,
)
from app.services.project_agent_tools import ProjectAgentContext


def test_looks_complex_for_enrichment_request():
    text = "丰富人设，加入新角色和冲突线，再写新章节，深化感情转折。"
    assert looks_complex_instruction(text)
    plan = infer_work_plan(text)
    kinds = [s["kind"] for s in plan]
    assert kinds[0] == "read_memory"
    assert "propose_memory_patch" in kinds
    assert "propose_create_document" in kinds
    fields = [s.get("field") for s in plan if s.get("field")]
    assert "characters" in fields
    assert "storyline" in fields
    note = work_plan_system_note(plan)
    assert "分步编排" in note


def test_simple_instruction_skips_plan():
    assert not looks_complex_instruction("把这一段润色一下")
    assert infer_work_plan("把这一段润色一下") == []


def test_advance_work_plan_and_nudge():
    ctx = ProjectAgentContext(1, 1)
    ctx.work_plan = infer_work_plan("丰富人设和故事线，加入冲突")
    ctx.work_plan_index = 0
    assert current_phase_nudge(ctx)
    assert advance_work_plan(ctx, "read_memory", {})
    assert ctx.work_plan_index == 1
    # 错字段不推进
    step = ctx.work_plan[1]
    if step.get("field"):
        assert not advance_work_plan(
            ctx, "propose_memory_patch", {"field": "notes"}
        )
        assert advance_work_plan(
            ctx, "propose_memory_patch", {"field": step["field"]}
        )


def test_payload_size_guard_rejects_huge_memory_patch():
    huge = "冲突" * (MAX_MEMORY_PATCH_CHARS // 2 + 100)
    msg = check_propose_payload_size(
        "propose_memory_patch",
        {"field": "storyline", "before": "", "after": huge},
    )
    assert msg and "提案过大" in msg
    assert check_propose_payload_size(
        "propose_create_document",
        {"title": "x", "text": "章" * (4500 + 10), "reason": ""},
    )


def test_enable_narrow_mode_creates_fallback_plan():
    ctx = ProjectAgentContext(1, 1)
    enable_narrow_mode(ctx)
    assert ctx.narrow_mode is True
    assert ctx.work_plan
    assert current_phase_nudge(ctx)
