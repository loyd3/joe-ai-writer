from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.models import AIMemory, Project
from app.schemas.schemas import AIMemoryUpdate
from app.services.llm_service import LLMService
from app.services.memory_normalize import (
    normalize_storyline,
    normalize_key_points,
    normalize_characters,
    normalize_world_building,
    normalize_memory_fields,
    memory_orm_to_dict,
)
import json
import re

EXPAND_SCOPES = (
    "outline",
    "storyline",
    "characters",
    "world_building",
    "writing_style",
    "key_points",
    "notes",
)


FIELD_META: Dict[str, Dict[str, str]] = {
    "outline_title": {
        "label": "章节标题",
        "hint": "输出一个简洁有力的章节标题，10～20字为宜，不要编号，不要引号。",
    },
    "outline_description": {
        "label": "章节简述",
        "hint": "输出该章节的情节要点简述，2～4句话，交代本章发生什么、推动哪些冲突，不要标题。",
    },
    "storyline": {
        "label": "故事线概述",
        "hint": "输出故事主线概述，100～300字，概括起承转合。",
    },
    "storyline_stage_title": {
        "label": "故事线阶段标题",
        "hint": "输出阶段标题，如「开端」「中段冲突」，4～12字，不要编号。",
    },
    "storyline_stage_summary": {
        "label": "故事线阶段简述",
        "hint": "输出该阶段情节简述，2～4句。",
    },
    "character_name": {
        "label": "角色名称",
        "hint": "输出一个贴合设定的角色姓名，可含绰号；只输出名字本身。",
    },
    "character_description": {
        "label": "角色描述",
        "hint": "输出角色外貌、身份与简要经历，3～6句，具体可感。",
    },
    "character_personality": {
        "label": "性格特点",
        "hint": "输出性格关键词与一句说明，例如：外冷内热，遇事先冷静分析。",
    },
    "character_background": {
        "label": "角色背景",
        "hint": "输出角色出身、过往经历与关键转折，100～250字。",
    },
    "character_goals": {
        "label": "目标/动机",
        "hint": "输出表面目标与深层动机，可各一句。",
    },
    "world_item_title": {
        "label": "世界观条目标题",
        "hint": "输出简短条目名，如「主要城邦」「魔法禁忌」，2～10字。",
    },
    "world_item_content": {
        "label": "世界观条目内容",
        "hint": "输出该条目的具体设定说明，2～5句。",
    },
    "world_building": {
        "label": "世界观",
        "hint": "按分类输出世界观：每行「分类名|条目标题|内容」。",
    },
    "writing_style": {
        "label": "写作风格",
        "hint": "描述叙述视角、语言节奏、情感基调与禁忌，分条列出。",
    },
    "key_point": {
        "label": "关键情节点标题",
        "hint": "输出情节点短标题，点明冲突或转折，不要序号。",
    },
    "key_point_summary": {
        "label": "关键情节简述",
        "hint": "输出该情节点的具体说明，1～3句。",
    },
    "notes": {
        "label": "备注",
        "hint": "整理写作时需注意的约束、伏笔或待办，分条清晰。",
    },
}


class AIMemoryService:
    """项目设定服务 - 管理项目级别的写作上下文"""

    @staticmethod
    def get_or_create_memory(db: Session, project_id: int) -> AIMemory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
        if not memory:
            memory = AIMemory(project_id=project_id)
            db.add(memory)
            db.commit()
            db.refresh(memory)
        return memory

    @staticmethod
    def to_response(memory: AIMemory) -> Dict[str, Any]:
        return memory_orm_to_dict(memory)

    @staticmethod
    def update_memory(db: Session, project_id: int, data: AIMemoryUpdate) -> AIMemory:
        memory = AIMemoryService.get_or_create_memory(db, project_id)

        update_data = data.model_dump(exclude_unset=True)
        if "storyline" in update_data:
            update_data["storyline"] = normalize_storyline(update_data["storyline"])
        if "key_points" in update_data:
            update_data["key_points"] = normalize_key_points(update_data["key_points"])
        if "characters" in update_data:
            update_data["characters"] = normalize_characters(update_data["characters"])
        if "world_building" in update_data:
            update_data["world_building"] = normalize_world_building(update_data["world_building"])

        for field, value in update_data.items():
            setattr(memory, field, value)

        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def build_memory_context(
        db: Session,
        project_id: int,
        style_agent_id: Optional[int] = None,
    ) -> str:
        """构建项目设定上下文字符串，用于注入到 AI 提示词中。

        style_agent_id 指定时用对应文风智能体；否则用用户默认智能体。
        有智能体风格块时不再重复注入旧 writing_style，避免两套打架。
        """
        memory = AIMemoryService.get_or_create_memory(db, project_id)
        data = normalize_memory_fields(
            outline=memory.outline,
            storyline=memory.storyline,
            characters=memory.characters,
            world_building=memory.world_building,
            writing_style=memory.writing_style,
            key_points=memory.key_points,
            notes=memory.notes,
        )

        context_parts = ["=== 项目设定 ==="]

        outline = data["outline"]
        if outline:
            context_parts.append("\n【文章大纲】")
            for i, item in enumerate(outline, 1):
                if not isinstance(item, dict):
                    continue
                title = item.get("title", "未命名章节")
                desc = item.get("description") or ""
                if desc:
                    context_parts.append(f"{i}. {title} — {desc}")
                else:
                    context_parts.append(f"{i}. {title}")

        storyline = data["storyline"]
        if storyline.get("summary") or storyline.get("stages"):
            context_parts.append("\n【故事线】")
            if storyline.get("summary"):
                context_parts.append(storyline["summary"])
            for i, stage in enumerate(storyline.get("stages") or [], 1):
                title = stage.get("title") or f"阶段{i}"
                summary = stage.get("summary") or ""
                context_parts.append(f"{i}. {title}" + (f"：{summary}" if summary else ""))

        characters = data["characters"]
        if characters:
            context_parts.append("\n【角色设定】")
            for char in characters:
                role = char.get("role") or ""
                label = f"{char.get('name', '未命名')}" + (f"（{role}）" if role else "")
                context_parts.append(f"\n- {label}:")
                context_parts.append(f"  描述: {char.get('description') or '无'}")
                if char.get("personality"):
                    context_parts.append(f"  性格: {char['personality']}")
                if char.get("background"):
                    context_parts.append(f"  背景: {char['background']}")
                if char.get("goals"):
                    context_parts.append(f"  目标: {char['goals']}")

        world = data["world_building"]
        cats = world.get("categories") or []
        if any(c.get("items") for c in cats):
            context_parts.append("\n【世界观设定】")
            for cat in cats:
                items = cat.get("items") or []
                if not items:
                    continue
                context_parts.append(f"· {cat.get('name', '未命名')}")
                for it in items:
                    context_parts.append(
                        f"  - {it.get('title') or '条目'}: {it.get('content') or ''}"
                    )

        from app.services.style_agent_service import StyleAgentService

        style_block = StyleAgentService.resolve_style_block(
            db, project_id, style_agent_id
        )
        if style_block:
            context_parts.append(f"\n{style_block}")
        elif data.get("writing_style"):
            context_parts.append(f"\n【写作风格】\n{data['writing_style']}")

        key_points = data["key_points"]
        if key_points:
            context_parts.append("\n【关键情节点】")
            for point in key_points:
                title = point.get("title") or ""
                summary = point.get("summary") or ""
                if title and summary:
                    context_parts.append(f"- {title}：{summary}")
                else:
                    context_parts.append(f"- {title or summary}")

        if data.get("notes"):
            context_parts.append(f"\n【备注】\n{data['notes']}")

        return "\n".join(context_parts) if len(context_parts) > 1 else ""

    @staticmethod
    def _resolve_mode(mode: str, current_value: Optional[str]) -> str:
        if mode and mode != "auto":
            return mode
        return "expand" if (current_value or "").strip() else "generate"

    @staticmethod
    def _build_field_prompt(
        field: str,
        mode: str,
        current_value: Optional[str],
        instruction: Optional[str],
        extra: Optional[Dict[str, Any]],
        memory_context: str,
        project_title: str,
    ) -> tuple[str, str]:
        meta = FIELD_META.get(field)
        if not meta:
            raise ValueError(f"不支持的字段: {field}")

        mode_text = {
            "generate": "请根据项目设定全新创作该字段内容。",
            "expand": "请在保留原意的基础上扩写、丰满细节。",
            "refine": "请精炼改写，使表达更清晰、更贴合项目设定。",
        }.get(mode, "请根据项目设定创作或完善该字段内容。")

        extra_lines = []
        if extra:
            if extra.get("outline_title"):
                extra_lines.append(f"所属章节标题：{extra['outline_title']}")
            if extra.get("character_name"):
                extra_lines.append(f"角色名称：{extra['character_name']}")
            if extra.get("category_name"):
                extra_lines.append(f"世界观分类：{extra['category_name']}")
            if extra.get("stage_title"):
                extra_lines.append(f"阶段标题：{extra['stage_title']}")
            if extra.get("sibling_titles"):
                extra_lines.append(f"已有章节：{' / '.join(extra['sibling_titles'])}")
            if extra.get("existing_points"):
                pts = extra["existing_points"]
                if pts and isinstance(pts[0], dict):
                    pts = [p.get("title") or p.get("summary") or "" for p in pts]
                extra_lines.append(f"已有情节点：{'；'.join(pts)}")

        system = (
            "你是小说/长文项目设定助手。只输出目标字段的最终文本，"
            "不要加标题、前缀、引号或解释说明。"
        )
        parts = [
            f"项目名称：{project_title or '未命名项目'}",
            memory_context or "（当前设定较空，请合理原创）",
            f"\n目标字段：{meta['label']}",
            meta["hint"],
            mode_text,
        ]
        if extra_lines:
            parts.append("补充信息：\n" + "\n".join(extra_lines))
        if current_value and current_value.strip():
            parts.append(f"当前内容：\n{current_value.strip()}")
        if instruction and instruction.strip():
            parts.append(f"用户额外要求：{instruction.strip()}")
        parts.append("请直接输出结果：")
        return system, "\n\n".join(parts)

    @staticmethod
    def _clean_result(text: str) -> str:
        result = (text or "").strip()
        result = re.sub(r"^```(?:\w+)?\s*", "", result)
        result = re.sub(r"\s*```$", "", result)
        result = re.sub(
            r"^(章节标题|章节简述|故事线|故事线概述|角色名称|角色描述|性格特点|角色背景|目标[/／]?动机|世界观|写作风格|关键情节点|备注)[：:]\s*",
            "",
            result,
        )
        return result.strip()

    @staticmethod
    async def assist_field(
        db: Session,
        project_id: int,
        field: str,
        mode: str = "auto",
        current_value: Optional[str] = None,
        instruction: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """基于项目设定，为单个设定字段生成/扩写/精炼内容"""
        if field not in FIELD_META:
            raise ValueError(f"不支持的字段: {field}")

        project = db.query(Project).filter(Project.id == project_id).first()
        memory_context = AIMemoryService.build_memory_context(db, project_id)
        resolved = AIMemoryService._resolve_mode(mode, current_value)
        system, prompt = AIMemoryService._build_field_prompt(
            field=field,
            mode=resolved,
            current_value=current_value,
            instruction=instruction,
            extra=extra,
            memory_context=memory_context,
            project_title=project.title if project else "",
        )
        raw = await LLMService.generate_text(prompt=prompt, system_prompt=system, temperature=0.8)
        return AIMemoryService._clean_result(raw)

    @staticmethod
    def extract_memory_from_content(db: Session, project_id: int, content: str) -> dict:
        return {"suggested_outline": [], "detected_characters": [], "summary": ""}

    @staticmethod
    def _extract_json_object(text: str) -> dict:
        raw = (text or "").strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            if isinstance(data, dict):
                return data
        raise ValueError("AI 未返回合法的 JSON 设定")

    @staticmethod
    async def expand_memory(
        db: Session,
        project_id: int,
        instruction: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        apply: bool = True,
    ) -> Dict[str, Any]:
        """基于现有项目设定，用 AI 扩展指定范围并可选写回。"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("项目不存在")

        memory = AIMemoryService.get_or_create_memory(db, project_id)
        current = normalize_memory_fields(
            outline=memory.outline,
            storyline=memory.storyline,
            characters=memory.characters,
            world_building=memory.world_building,
            writing_style=memory.writing_style,
            key_points=memory.key_points,
            notes=memory.notes,
        )

        selected = [s for s in (scopes or list(EXPAND_SCOPES)) if s in EXPAND_SCOPES]
        if not selected:
            selected = list(EXPAND_SCOPES)

        seed = {k: current.get(k) for k in selected}
        system = (
            "你是资深网文/小说设定顾问。根据已有项目设定扩展内容，保持风格一致、细节可感、可直接用于写作。"
            "只输出合法 JSON 对象，不要 markdown 代码块，不要解释。"
        )
        prompt = (
            f"项目标题：{project.title or ''}\n"
            f"需要扩展的字段：{', '.join(selected)}\n"
            f"用户额外要求：{(instruction or '').strip() or '无；在现有基础上合理充实'}\n\n"
            "现有设定（JSON）：\n"
            f"{json.dumps(seed, ensure_ascii=False, indent=2)}\n\n"
            "请输出 JSON，且只包含上述需要扩展的字段。字段结构要求：\n"
            '- outline: [{"title":"...","description":"..."}]\n'
            '- storyline: {"summary":"...","stages":[{"title":"...","summary":"..."}]}\n'
            '- characters: [{"name":"...","description":"...","personality":"...","background":"...","goals":"...","role":"主角|配角|反派"}]\n'
            '- world_building: {"categories":[{"name":"...","items":[{"title":"...","content":"..."}]}]}\n'
            '- writing_style: 字符串\n'
            '- key_points: [{"title":"...","summary":"..."}]\n'
            '- notes: 字符串\n'
            "要求：在保留原意与关键名的前提下显著充实细节；空字段请合理生成；不要删光原有核心信息。"
        )

        raw = await LLMService.generate_text(prompt=prompt, system_prompt=system, temperature=0.75)
        parsed = AIMemoryService._extract_json_object(raw)

        patch: Dict[str, Any] = {}
        if "outline" in selected and "outline" in parsed:
            patch["outline"] = parsed.get("outline") or []
        if "storyline" in selected and "storyline" in parsed:
            patch["storyline"] = normalize_storyline(parsed.get("storyline"))
        if "characters" in selected and "characters" in parsed:
            patch["characters"] = normalize_characters(parsed.get("characters") or [])
        if "world_building" in selected and "world_building" in parsed:
            patch["world_building"] = normalize_world_building(parsed.get("world_building") or {})
        if "writing_style" in selected and "writing_style" in parsed:
            patch["writing_style"] = str(parsed.get("writing_style") or "")
        if "key_points" in selected and "key_points" in parsed:
            patch["key_points"] = normalize_key_points(parsed.get("key_points") or [])
        if "notes" in selected and "notes" in parsed:
            patch["notes"] = str(parsed.get("notes") or "")

        if not patch:
            raise ValueError("AI 未返回可应用的扩展内容")

        if apply:
            memory = AIMemoryService.update_memory(db, project_id, AIMemoryUpdate(**patch))
            result_memory = AIMemoryService.to_response(memory)
        else:
            result_memory = {**AIMemoryService.to_response(memory), **patch}

        return {
            "memory": result_memory,
            "scopes": selected,
            "applied": bool(apply),
        }
