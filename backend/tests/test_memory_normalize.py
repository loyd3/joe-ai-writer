"""大纲被存成 JSON 字符串时，项目接口仍应返回列表。"""
from datetime import datetime
from types import SimpleNamespace

from app.schemas.schemas import AIMemoryResponse
from app.services.memory_normalize import (
    merge_memory_field,
    normalize_memory_fields,
    normalize_outline,
)


OUTLINE_JSON = (
    '[{"title": "一（上）、五星好评的日常", "description": "补写正文。"},'
    ' {"title": "六（下）、编剧的自我和解", "description": "终于睡了个好觉。"}]'
)


def test_normalize_outline_parses_json_string():
    outline = normalize_outline(OUTLINE_JSON)
    assert isinstance(outline, list)
    assert outline[0]["title"] == "一（上）、五星好评的日常"
    assert outline[1]["description"] == "终于睡了个好觉。"


def test_normalize_outline_keeps_list():
    raw = [{"title": "第一章", "description": "开端", "act": "第一幕"}]
    assert normalize_outline(raw) == raw
    assert normalize_outline(None) == []
    assert normalize_outline("") == []


def test_project_response_accepts_string_outline():
    memory = SimpleNamespace(
        id=1,
        project_id=2,
        updated_at=datetime(2026, 10, 17),
        outline=OUTLINE_JSON,
        storyline=None,
        characters=[],
        world_building={},
        writing_style=None,
        key_points=[],
        notes=None,
    )
    parsed = AIMemoryResponse.model_validate(memory)
    assert isinstance(parsed.outline, list)
    assert parsed.outline[0]["title"].startswith("一（上）")

    fields = normalize_memory_fields(outline=OUTLINE_JSON)
    AIMemoryResponse.model_validate({
        "id": 1,
        "project_id": 2,
        "updated_at": datetime(2026, 10, 17),
        **fields,
    })


def test_merge_memory_field_upserts_characters_and_key_points():
    current = [
        {"name": "Irene", "description": "会长", "role": "主角"},
        {"name": "Wendy", "description": "转学生", "role": "主角"},
    ]
    patch = [
        {"name": "Irene", "description": "会长，内心柔软"},
        {"name": "Joy", "description": "闺蜜", "role": "配角"},
    ]
    merged = merge_memory_field("characters", current, patch)
    names = [c["name"] for c in merged]
    assert names == ["Irene", "Wendy", "Joy"]
    assert "柔软" in merged[0]["description"]

    points = merge_memory_field(
        "key_points",
        [{"title": "相遇", "summary": ""}],
        [{"title": "相遇", "summary": "雨天"}, {"title": "告白", "summary": "文化祭"}],
    )
    assert points[0]["summary"] == "雨天"
    assert points[1]["title"] == "告白"


def test_merge_memory_field_storyline_stages():
    current = {"summary": "校园恋", "stages": [{"title": "初遇", "summary": "雨"}]}
    patch = {"stages": [{"title": "初遇", "summary": "雨天伞下"}, {"title": "告白", "summary": "祭典"}]}
    merged = merge_memory_field("storyline", current, patch)
    assert merged["summary"] == "校园恋"
    assert len(merged["stages"]) == 2
    assert "伞" in merged["stages"][0]["summary"]
