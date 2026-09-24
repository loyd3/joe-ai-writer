"""项目设定结构化数据的规范化（读写兼容旧格式）"""
from __future__ import annotations

import json
from typing import Any, Dict, List


DEFAULT_WORLD_CATEGORIES = [
    "时代背景",
    "地理环境",
    "力量/规则",
    "社会结构",
    "文化习俗",
    "其他设定",
]

CHAR_ROLES = ["主角", "重要配角", "反派", "配角", "其他"]


def _as_dict(raw: Any) -> Any:
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return raw
    return raw


def normalize_storyline(raw: Any) -> Dict[str, Any]:
    raw = _as_dict(raw)
    if raw is None or raw == "":
        return {"summary": "", "stages": []}
    if isinstance(raw, str):
        return {"summary": raw, "stages": []}
    if isinstance(raw, list):
        stages = [_normalize_stage(s) for s in raw]
        return {"summary": "", "stages": stages}
    if isinstance(raw, dict):
        stages_raw = raw.get("stages") or raw.get("nodes") or []
        if not isinstance(stages_raw, list):
            stages_raw = []
        return {
            "summary": str(raw.get("summary") or raw.get("overview") or ""),
            "stages": [_normalize_stage(s) for s in stages_raw],
        }
    return {"summary": "", "stages": []}


def _normalize_stage(item: Any) -> Dict[str, str]:
    if isinstance(item, str):
        return {"title": item[:40], "summary": item}
    if isinstance(item, dict):
        title = str(item.get("title") or item.get("name") or "")
        summary = str(
            item.get("summary")
            or item.get("description")
            or item.get("content")
            or ""
        )
        return {"title": title, "summary": summary}
    return {"title": "", "summary": ""}


def normalize_key_points(raw: Any) -> List[Dict[str, str]]:
    raw = _as_dict(raw)
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append({"title": item[:40] if len(item) > 40 else item, "summary": item})
        elif isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or "")
            summary = str(
                item.get("summary")
                or item.get("description")
                or item.get("content")
                or item.get("point")
                or ""
            )
            if not title and summary:
                title = summary[:40]
            result.append({"title": title, "summary": summary})
    return result


def normalize_character(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "name": "",
            "description": "",
            "personality": "",
            "background": "",
            "goals": "",
            "role": "配角",
            "avatar": "",
            "color": "",
        }
    return {
        "name": str(raw.get("name") or ""),
        "description": str(raw.get("description") or ""),
        "personality": str(raw.get("personality") or ""),
        "background": str(raw.get("background") or ""),
        "goals": str(raw.get("goals") or ""),
        "role": str(raw.get("role") or "配角"),
        "avatar": str(raw.get("avatar") or ""),
        "color": str(raw.get("color") or ""),
    }


def normalize_characters(raw: Any) -> List[Dict[str, Any]]:
    raw = _as_dict(raw)
    if not isinstance(raw, list):
        return []
    return [normalize_character(c) for c in raw]


def normalize_world_building(raw: Any) -> Dict[str, Any]:
    """统一为 { categories: [{ name, items: [{ title, content }] }] }"""
    raw = _as_dict(raw)
    if not raw:
        return {"categories": [{"name": n, "items": []} for n in DEFAULT_WORLD_CATEGORIES]}

    if isinstance(raw, dict) and isinstance(raw.get("categories"), list):
        cats = []
        for c in raw["categories"]:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or c.get("title") or "未命名分类")
            items_raw = c.get("items") or []
            items = []
            if isinstance(items_raw, list):
                for it in items_raw:
                    if isinstance(it, str):
                        items.append({"title": it[:30], "content": it})
                    elif isinstance(it, dict):
                        items.append({
                            "title": str(it.get("title") or it.get("key") or it.get("name") or ""),
                            "content": str(it.get("content") or it.get("value") or it.get("description") or ""),
                        })
            cats.append({"name": name, "items": items})
        if not cats:
            cats = [{"name": n, "items": []} for n in DEFAULT_WORLD_CATEGORIES]
        return {"categories": cats}

    # 旧版扁平 key: value
    if isinstance(raw, dict):
        items = []
        for k, v in raw.items():
            if k in ("categories",):
                continue
            items.append({"title": str(k), "content": "" if v is None else str(v)})
        return {
            "categories": [
                {"name": "综合设定", "items": items},
                *[{"name": n, "items": []} for n in DEFAULT_WORLD_CATEGORIES if n != "其他设定"],
            ]
        }

    if isinstance(raw, list):
        cats = []
        for c in raw:
            if isinstance(c, dict) and ("name" in c or "title" in c):
                name = str(c.get("name") or c.get("title") or "未命名")
                items = []
                for it in (c.get("items") or []):
                    if isinstance(it, dict):
                        items.append({
                            "title": str(it.get("title") or it.get("key") or ""),
                            "content": str(it.get("content") or it.get("value") or ""),
                        })
                cats.append({"name": name, "items": items})
        return {"categories": cats or [{"name": n, "items": []} for n in DEFAULT_WORLD_CATEGORIES]}

    return {"categories": [{"name": n, "items": []} for n in DEFAULT_WORLD_CATEGORIES]}


def normalize_memory_fields(
    outline: Any = None,
    storyline: Any = None,
    characters: Any = None,
    world_building: Any = None,
    writing_style: Any = None,
    key_points: Any = None,
    notes: Any = None,
) -> Dict[str, Any]:
    return {
        "outline": outline if isinstance(outline, list) else (outline or []),
        "storyline": normalize_storyline(storyline),
        "characters": normalize_characters(characters),
        "world_building": normalize_world_building(world_building),
        "writing_style": writing_style or "",
        "key_points": normalize_key_points(key_points),
        "notes": notes or "",
    }


def memory_orm_to_dict(memory) -> Dict[str, Any]:
    fields = normalize_memory_fields(
        outline=memory.outline,
        storyline=memory.storyline,
        characters=memory.characters,
        world_building=memory.world_building,
        writing_style=memory.writing_style,
        key_points=memory.key_points,
        notes=memory.notes,
    )
    return {
        "id": memory.id,
        "project_id": memory.project_id,
        "updated_at": memory.updated_at,
        **fields,
    }
