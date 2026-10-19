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


def test_reorg_storyline_plan_skips_reading_all_chapters():
    from app.services.project_agent_phases import (
        looks_like_reorg_instruction,
        looks_like_read_all_plan,
    )

    text = "请对照新故事线梳理 storyline、outline，并整理全部章节"
    assert looks_like_reorg_instruction(text)
    plan = infer_work_plan(text)
    kinds = [s["kind"] for s in plan]
    assert kinds[0] == "document_map"
    assert "propose_memory_patch" in kinds
    assert [s.get("field") for s in plan if s.get("field")] == ["storyline", "outline"]
    storyline_only = infer_work_plan("请梳理故事线，不要改别的")
    assert [s.get("field") for s in storyline_only if s.get("field")] == ["storyline"]
    assert "propose_create_document" not in kinds
    assert "read_document" not in kinds
    assert looks_like_read_all_plan(
        "我先把当前 storyline、outline 和全部章节文档读一遍，再对照新故事线做梳理。"
    )
    assert looks_like_read_all_plan("好，先读 storyline 当前完整内容，再据此分章节补副线。")


def test_long_corpus_plan_uses_map_then_digest():
    from app.services.project_agent_phases import looks_like_long_corpus_instruction

    text = "检查全书人设是否崩坏，看看各章是否前后矛盾"
    assert looks_like_long_corpus_instruction(text)
    plan = infer_work_plan(text)
    kinds = [s["kind"] for s in plan]
    assert kinds == ["document_map", "digest_document", "finish"]
    assert "不要 propose_memory_patch" in plan[-1]["hint"]


def test_generate_many_documents_uses_settings_api_plan():
    text = "根据设定生成多篇文章"
    plan = infer_work_plan(text)
    assert [step["kind"] for step in plan] == ["generate_documents_from_settings"]
    assert "generate_documents_from_settings" in work_plan_system_note(plan)
    assert "不要 propose_memory_patch" in plan[0]["hint"]


def test_outline_article_generation_does_not_update_settings():
    plan = infer_work_plan("根据大纲生成文章")
    assert [step["kind"] for step in plan] == ["generate_documents_from_settings"]


def test_explicit_settings_edit_still_updates_memory():
    plan = infer_work_plan("修改人物设定，补充角色背景")
    assert any(step["kind"] == "propose_memory_patch" for step in plan)
    fields = [step.get("field") for step in plan]
    assert "characters" in fields


def test_generate_plus_explicit_edit_keeps_both_steps():
    plan = infer_work_plan("先修改大纲，再根据大纲生成文章")
    kinds = [step["kind"] for step in plan]
    assert "propose_memory_patch" in kinds
    assert kinds[-1] == "generate_documents_from_settings"


def test_memory_patch_is_skipped_while_generating_articles():
    from app.services.project_agent_tools import tool_propose_memory_patch

    ctx = ProjectAgentContext(1, 1)
    ctx.instruction = "根据大纲生成文章"
    result = tool_propose_memory_patch(
        ctx, None, {"field": "outline", "after": [{"title": "被改写的大纲"}], "reason": "对齐"},
    )
    assert result["skipped"] is True
    assert ctx.changes == []


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
    ctx.instruction = "润色这一段"
    enable_narrow_mode(ctx)
    assert ctx.narrow_mode is True
    assert not ctx.work_plan
    ctx.instruction = "修改人物设定"
    enable_narrow_mode(ctx)
    assert ctx.work_plan
    assert current_phase_nudge(ctx)


def test_check_instruction_does_not_write_settings():
    from app.services.project_agent_tools import tool_propose_memory_patch

    ctx = ProjectAgentContext(1, 1)
    ctx.instruction = "检查全书人设是否崩坏"
    result = tool_propose_memory_patch(
        ctx, None, {"field": "characters", "after": [{"name": "被改写"}], "reason": "顺手"},
    )
    assert result["skipped"] is True
    assert ctx.changes == []


def test_named_field_edit_does_not_touch_other_fields():
    from app.services.project_agent_tools import tool_propose_memory_patch

    ctx = ProjectAgentContext(1, 1)
    ctx.instruction = "修改人物设定"
    result = tool_propose_memory_patch(
        ctx, None, {"field": "outline", "after": [{"title": "不该改的大纲"}], "reason": "顺手"},
    )
    assert result["skipped"] is True
    assert ctx.changes == []
