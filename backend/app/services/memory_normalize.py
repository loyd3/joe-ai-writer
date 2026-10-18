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


def normalize_outline(raw: Any) -> List[Dict[str, Any]]:
    """大纲必须是章节对象列表。兼容误存成 JSON 字符串（或再包一层）的旧数据。"""
    raw = _as_dict(raw)
    if isinstance(raw, str):
        raw = _as_dict(raw)
    if raw is None or raw == "":
        return []
    if isinstance(raw, dict):
        nested = raw.get("outline")
        if isinstance(nested, (list, str)):
            return normalize_outline(nested)
        raw = [raw]
    if not isinstance(raw, list):
        return []
    result: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            parsed = _as_dict(item)
            if isinstance(parsed, dict):
                item = parsed
            else:
                text = item.strip()
                item = {"title": text[:80], "description": text}
        if isinstance(item, dict):
            result.append(item)
    return result


def coerce_memory_field(field: str, value: Any) -> Any:
    """写入前规范化各设定字段，兼容旧格式 / 半截结构。"""
    if field == "outline":
        return normalize_outline(value)
    if field == "storyline":
        return normalize_storyline(value)
    if field == "characters":
        return normalize_characters(value)
    if field == "world_building":
        return normalize_world_building(value)
    if field == "key_points":
        return normalize_key_points(value)
    if field in ("writing_style", "notes"):
        return "" if value is None else str(value)
    return value


def _list_item_key(field: str, item: Any) -> str:
    if not isinstance(item, dict):
        return str(item).strip().lower()
    if field == "characters":
        return str(item.get("name") or "").strip().lower()
    if field == "outline":
        return str(item.get("title") or item.get("name") or item.get("chapter") or "").strip().lower()
    # key_points / stages
    return str(item.get("title") or item.get("name") or "").strip().lower()


def _upsert_dict_list(current: List[Any], patch: List[Any], field: str) -> List[Any]:
    """按 name/title 合并列表：同名覆盖非空字段，新名追加。"""
    store: Dict[str, Any] = {}
    order: List[str] = []
    anon = 0
    for item in current:
        key = _list_item_key(field, item)
        if not key:
            key = f"__anon_{anon}"
            anon += 1
        if key not in store:
            order.append(key)
        store[key] = item
    for item in patch:
        key = _list_item_key(field, item)
        if not key:
            key = f"__anon_{anon}"
            anon += 1
            order.append(key)
            store[key] = item
            continue
        if key in store and isinstance(store[key], dict) and isinstance(item, dict):
            merged = dict(store[key])
            for k, v in item.items():
                if v is None or v == "":
                    continue
                merged[k] = v
            store[key] = merged
        else:
            if key not in store:
                order.append(key)
            store[key] = item
    return [store[k] for k in order if k in store]


def merge_memory_field(field: str, current: Any, patch: Any) -> Any:
    """增量合并设定：列表按 name/title upsert；故事线合并 summary/stages；文本追加。

    用于智能体只传「新增/改动的几项」而不必回传整字段，降低截断失败率。
    """
    base = coerce_memory_field(field, current)
    delta = coerce_memory_field(field, patch)

    if field in ("characters", "key_points", "outline"):
        if not isinstance(base, list):
            base = []
        if not isinstance(delta, list):
            delta = [delta] if delta not in (None, "", [], {}) else []
        return coerce_memory_field(field, _upsert_dict_list(base, delta, field))

    if field == "storyline" and isinstance(base, dict) and isinstance(delta, dict):
        summary = str(delta.get("summary") or "").strip() or str(base.get("summary") or "")
        stages_base = base.get("stages") if isinstance(base.get("stages"), list) else []
        stages_delta = delta.get("stages") if isinstance(delta.get("stages"), list) else []
        # 若 patch 是纯字符串规范化结果（只有 summary），保留原 stages
        if stages_delta:
            stages = _upsert_dict_list(stages_base, stages_delta, "key_points")
        else:
            stages = stages_base
        return {"summary": summary, "stages": stages}

    if field == "world_building" and isinstance(base, dict) and isinstance(delta, dict):
        base_cats = {
            str(c.get("name") or ""): c
            for c in (base.get("categories") or [])
            if isinstance(c, dict)
        }
        order = [str(c.get("name") or "") for c in (base.get("categories") or []) if isinstance(c, dict)]
        for cat in delta.get("categories") or []:
            if not isinstance(cat, dict):
                continue
            name = str(cat.get("name") or "").strip() or "未命名分类"
            if name not in base_cats:
                order.append(name)
                base_cats[name] = {"name": name, "items": []}
            existing_items = base_cats[name].get("items") if isinstance(base_cats[name], dict) else []
            if not isinstance(existing_items, list):
                existing_items = []
            new_items = cat.get("items") if isinstance(cat.get("items"), list) else []
            base_cats[name] = {
                "name": name,
                "items": _upsert_dict_list(existing_items, new_items, "key_points"),
            }
        return {"categories": [base_cats[n] for n in order if n in base_cats]}

    if field in ("writing_style", "notes") and isinstance(base, str) and isinstance(delta, str):
        if not base.strip():
            return delta
        if not delta.strip() or delta.strip() == base.strip():
            return base
        # 若 delta 已包含 base 前缀，视为整段替换
        if base.strip() and delta.strip().startswith(base.strip()[: min(40, len(base.strip()))]):
            return delta
        return f"{base.rstrip()}\n\n{delta.lstrip()}"

    # 默认：整段替换
    return delta


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
        "outline": normalize_outline(outline),
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
