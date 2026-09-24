"""项目级文风智能体：预设、CRUD、编译风格块、解析写作时使用的文风。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import AIMemory, WritingStyleAgent

# 结构化 config 字段默认值
DEFAULT_CONFIG: Dict[str, Any] = {
    "tone": "自然克制",
    "pov": "第三人称有限",
    "pace": "适中",
    "sentence": "长短交错",
    "diction": "白话",
    "dialogue_ratio": "中",
    "detail_level": "适中",
    "taboo": [],
    "custom_text": "",
    "samples": [],
}

# 内置预设（克隆到项目后可改）
STYLE_PRESETS: List[Dict[str, Any]] = [
    {
        "key": "standard",
        "name": "标准叙述",
        "description": "中性、清楚、适合大多数章节推进",
        "config": {
            **DEFAULT_CONFIG,
            "tone": "自然克制",
            "pace": "适中",
            "sentence": "长短交错",
            "detail_level": "适中",
        },
    },
    {
        "key": "cold_minimal",
        "name": "冷硬极简",
        "description": "短句、少形容、事实与动作优先",
        "config": {
            **DEFAULT_CONFIG,
            "tone": "冷峻疏离",
            "pace": "紧凑",
            "sentence": "短句为主",
            "diction": "白话精简",
            "dialogue_ratio": "低",
            "detail_level": "克制",
            "taboo": ["大段心理独白", "排比抒情", "主题升华句"],
        },
    },
    {
        "key": "warm_lyrical",
        "name": "深情细腻",
        "description": "情绪与感官细节多一些，节奏偏缓",
        "config": {
            **DEFAULT_CONFIG,
            "tone": "温暖细腻",
            "pace": "舒缓",
            "sentence": "长短交错",
            "diction": "略带文学性",
            "dialogue_ratio": "中",
            "detail_level": "浓墨",
            "taboo": ["油腻鸡汤式收尾"],
        },
    },
    {
        "key": "light_humor",
        "name": "轻松幽默",
        "description": "口语感强，可有轻吐槽，不油腻",
        "config": {
            **DEFAULT_CONFIG,
            "tone": "轻松幽默",
            "pace": "轻快",
            "sentence": "短句为主",
            "diction": "口语",
            "dialogue_ratio": "高",
            "detail_level": "适中",
            "taboo": ["连续段子", "网络烂梗堆砌"],
        },
    },
    {
        "key": "suspense",
        "name": "悬疑压迫",
        "description": "信息克制、氛围紧、留白多",
        "config": {
            **DEFAULT_CONFIG,
            "tone": "压抑紧张",
            "pace": "紧凑",
            "sentence": "短句为主",
            "diction": "白话",
            "dialogue_ratio": "低",
            "detail_level": "克制",
            "taboo": ["过早揭底", "全知解说动机"],
        },
    },
    {
        "key": "epic_formal",
        "name": "史诗书面",
        "description": "书面语略重，场面开阔，忌堆砌形容词",
        "config": {
            **DEFAULT_CONFIG,
            "tone": "庄重开阔",
            "pace": "舒缓",
            "sentence": "长句可多",
            "diction": "书面",
            "dialogue_ratio": "低",
            "detail_level": "适中",
            "taboo": ["口号式宣言", "空洞宏大形容词连用"],
        },
    },
]


def _normalize_config(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = deepcopy(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return cfg
    for key in DEFAULT_CONFIG:
        if key not in raw:
            continue
        val = raw[key]
        if key in ("taboo", "samples"):
            if isinstance(val, list):
                cfg[key] = [str(x).strip() for x in val if str(x).strip()]
            elif isinstance(val, str) and val.strip():
                cfg[key] = [line.strip() for line in val.splitlines() if line.strip()]
        else:
            cfg[key] = str(val) if val is not None else DEFAULT_CONFIG[key]
    return cfg


def compile_style_block(name: str, config: Dict[str, Any], description: str = "") -> str:
    """把智能体设定编译成注入 prompt 的风格块。"""
    cfg = _normalize_config(config)
    lines = [f"【文风智能体：{name}】"]
    if description:
        lines.append(f"定位：{description}")
    lines.extend(
        [
            f"语气：{cfg.get('tone') or '自然'}",
            f"视角：{cfg.get('pov') or '不限'}",
            f"节奏：{cfg.get('pace') or '适中'}",
            f"句式：{cfg.get('sentence') or '长短交错'}",
            f"用词：{cfg.get('diction') or '白话'}",
            f"对白占比：{cfg.get('dialogue_ratio') or '中'}",
            f"细节浓度：{cfg.get('detail_level') or '适中'}",
        ]
    )
    taboo = cfg.get("taboo") or []
    if taboo:
        lines.append("额外禁忌：" + "；".join(taboo))
    custom = (cfg.get("custom_text") or "").strip()
    if custom:
        lines.append(f"作者补充：\n{custom}")
    samples = cfg.get("samples") or []
    if samples:
        lines.append("请贴近以下笔触（勿照抄原文）：")
        for i, s in enumerate(samples[:3], 1):
            lines.append(f"--- 范例{i} ---\n{s}\n---")
    lines.append("请严格按上述文风组织语言与节奏，与设定中的角色/世界观保持一致。")
    return "\n".join(lines)


class StyleAgentService:
    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        return [
            {
                "key": p["key"],
                "name": p["name"],
                "description": p["description"],
                "config": _normalize_config(p.get("config")),
            }
            for p in STYLE_PRESETS
        ]

    @staticmethod
    def get_preset(key: str) -> Optional[Dict[str, Any]]:
        for p in STYLE_PRESETS:
            if p["key"] == key:
                return p
        return None

    @staticmethod
    def to_dict(agent: WritingStyleAgent) -> Dict[str, Any]:
        return {
            "id": agent.id,
            "project_id": agent.project_id,
            "name": agent.name,
            "description": agent.description or "",
            "preset_key": agent.preset_key,
            "config": _normalize_config(agent.config if isinstance(agent.config, dict) else {}),
            "is_default": bool(agent.is_default),
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "compiled_preview": compile_style_block(
                agent.name,
                agent.config if isinstance(agent.config, dict) else {},
                agent.description or "",
            ),
        }

    @staticmethod
    def list_agents(db: Session, project_id: int) -> List[WritingStyleAgent]:
        StyleAgentService.ensure_project_agents(db, project_id)
        return (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.project_id == project_id)
            .order_by(WritingStyleAgent.is_default.desc(), WritingStyleAgent.id.asc())
            .all()
        )

    @staticmethod
    def get_agent(
        db: Session, project_id: int, agent_id: int
    ) -> Optional[WritingStyleAgent]:
        return (
            db.query(WritingStyleAgent)
            .filter(
                WritingStyleAgent.project_id == project_id,
                WritingStyleAgent.id == agent_id,
            )
            .first()
        )

    @staticmethod
    def get_default_agent(db: Session, project_id: int) -> Optional[WritingStyleAgent]:
        StyleAgentService.ensure_project_agents(db, project_id)
        return (
            db.query(WritingStyleAgent)
            .filter(
                WritingStyleAgent.project_id == project_id,
                WritingStyleAgent.is_default == True,  # noqa: E712
            )
            .first()
        )

    @staticmethod
    def ensure_project_agents(db: Session, project_id: int) -> None:
        """若项目尚无智能体：用旧 writing_style 或标准预设建一个默认。"""
        exists = (
            db.query(WritingStyleAgent.id)
            .filter(WritingStyleAgent.project_id == project_id)
            .first()
        )
        if exists:
            return

        memory = (
            db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
        )
        legacy = (memory.writing_style or "").strip() if memory else ""
        preset = StyleAgentService.get_preset("standard") or STYLE_PRESETS[0]
        config = _normalize_config(preset.get("config"))
        if legacy:
            config["custom_text"] = legacy
            name = "项目默认文风"
            description = "由原写作风格文本迁移"
            preset_key = None
        else:
            name = preset["name"]
            description = preset.get("description") or ""
            preset_key = preset["key"]

        agent = WritingStyleAgent(
            project_id=project_id,
            name=name,
            description=description,
            preset_key=preset_key,
            config=config,
            is_default=True,
        )
        db.add(agent)
        db.commit()

    @staticmethod
    def _clear_defaults(db: Session, project_id: int) -> None:
        db.query(WritingStyleAgent).filter(
            WritingStyleAgent.project_id == project_id
        ).update({"is_default": False}, synchronize_session=False)

    @staticmethod
    def create_agent(
        db: Session,
        project_id: int,
        name: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        preset_key: Optional[str] = None,
        is_default: bool = False,
    ) -> WritingStyleAgent:
        count = (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.project_id == project_id)
            .count()
        )
        if is_default or count == 0:
            StyleAgentService._clear_defaults(db, project_id)
            is_default = True

        agent = WritingStyleAgent(
            project_id=project_id,
            name=(name or "未命名文风").strip()[:100],
            description=(description or "").strip() or None,
            preset_key=preset_key,
            config=_normalize_config(config),
            is_default=is_default,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        StyleAgentService._sync_legacy_writing_style(db, project_id)
        return agent

    @staticmethod
    def create_from_preset(
        db: Session, project_id: int, preset_key: str, set_default: bool = False
    ) -> WritingStyleAgent:
        preset = StyleAgentService.get_preset(preset_key)
        if not preset:
            raise ValueError(f"未知预设: {preset_key}")
        return StyleAgentService.create_agent(
            db,
            project_id=project_id,
            name=preset["name"],
            description=preset.get("description") or "",
            config=preset.get("config"),
            preset_key=preset["key"],
            is_default=set_default,
        )

    @staticmethod
    def update_agent(
        db: Session,
        project_id: int,
        agent_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_default: Optional[bool] = None,
    ) -> WritingStyleAgent:
        agent = StyleAgentService.get_agent(db, project_id, agent_id)
        if not agent:
            raise ValueError("文风智能体不存在")
        if name is not None:
            agent.name = name.strip()[:100] or agent.name
        if description is not None:
            agent.description = description.strip() or None
        if config is not None:
            agent.config = _normalize_config(config)
        if is_default is True:
            StyleAgentService._clear_defaults(db, project_id)
            agent.is_default = True
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        StyleAgentService._sync_legacy_writing_style(db, project_id)
        return agent

    @staticmethod
    def delete_agent(db: Session, project_id: int, agent_id: int) -> None:
        agent = StyleAgentService.get_agent(db, project_id, agent_id)
        if not agent:
            raise ValueError("文风智能体不存在")
        was_default = agent.is_default
        db.delete(agent)
        db.commit()
        remaining = (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.project_id == project_id)
            .order_by(WritingStyleAgent.id.asc())
            .all()
        )
        if was_default and remaining:
            remaining[0].is_default = True
            db.commit()
        if not remaining:
            # 删光后重建一个默认，避免写作无文风
            StyleAgentService.ensure_project_agents(db, project_id)
        StyleAgentService._sync_legacy_writing_style(db, project_id)

    @staticmethod
    def set_default(db: Session, project_id: int, agent_id: int) -> WritingStyleAgent:
        return StyleAgentService.update_agent(
            db, project_id, agent_id, is_default=True
        )

    @staticmethod
    def _sync_legacy_writing_style(db: Session, project_id: int) -> None:
        """把默认智能体的编译结果/补充写回 AIMemory.writing_style，兼容旧导出路径。"""
        memory = (
            db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
        )
        if not memory:
            return
        default = (
            db.query(WritingStyleAgent)
            .filter(
                WritingStyleAgent.project_id == project_id,
                WritingStyleAgent.is_default == True,  # noqa: E712
            )
            .first()
        )
        if not default:
            return
        cfg = _normalize_config(default.config if isinstance(default.config, dict) else {})
        custom = (cfg.get("custom_text") or "").strip()
        # 优先保留用户自由说明；否则写简短摘要
        if custom:
            memory.writing_style = custom
        else:
            memory.writing_style = (
                f"{default.name}｜语气{cfg.get('tone')}｜"
                f"{cfg.get('pov')}｜{cfg.get('pace')}｜{cfg.get('sentence')}"
            )
        db.commit()

    @staticmethod
    def resolve_style_block(
        db: Session,
        project_id: int,
        style_agent_id: Optional[int] = None,
    ) -> str:
        """解析本次写作应注入的风格块。"""
        agent: Optional[WritingStyleAgent] = None
        if style_agent_id:
            agent = StyleAgentService.get_agent(db, project_id, style_agent_id)
        if not agent:
            agent = StyleAgentService.get_default_agent(db, project_id)
        if agent:
            return compile_style_block(
                agent.name,
                agent.config if isinstance(agent.config, dict) else {},
                agent.description or "",
            )
        # 兜底：旧 writing_style
        memory = (
            db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
        )
        if memory and (memory.writing_style or "").strip():
            return f"【写作风格】\n{memory.writing_style.strip()}"
        return ""
