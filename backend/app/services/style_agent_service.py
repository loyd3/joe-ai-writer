"""用户级文风智能体：预设、CRUD、从文本提炼、编译风格块、解析写作时使用的文风。"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import AIMemory, Project, WritingStyleAgent

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

# 内置预设（克隆到用户文风库后可改）
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

EXTRACT_SYSTEM_PROMPT = """你是文风分析专家。请根据给定范文，提炼可复用的「文风智能体」配置。
只输出一个 JSON 对象，不要 markdown 代码块，不要解释。字段如下：
{
  "name": "不超过12字的文风名",
  "description": "一句话定位",
  "tone": "语气标签",
  "pov": "视角，如第三人称有限/第一人称",
  "pace": "节奏，如紧凑/适中/舒缓",
  "sentence": "句式，如短句为主/长短交错/长句可多",
  "diction": "用词，如白话/口语/书面",
  "dialogue_ratio": "对白占比 低/中/高",
  "detail_level": "细节浓度 克制/适中/浓墨",
  "taboo": ["该文风应避免的写法，1-5条"],
  "custom_text": "80-200字的文风说明，概括节奏、修辞习惯、信息密度",
  "samples": ["从原文摘取的短句范例1（尽量原句，40-120字）", "范例2", "范例3"]
}
要求：samples 尽量摘自原文；不要编造与原文无关的情节；JSON 合法。"""


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


def _parse_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("模型未返回内容")
    try:
        from json_repair import repair_json
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("无法解析文风 JSON")
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        from json_repair import repair_json
        obj = repair_json(m.group(), return_objects=True)
        if isinstance(obj, dict):
            return obj
        raise ValueError("文风 JSON 解析失败")


def _pick_representative_chunks(
    text: str,
    max_chunks: int = 8,
    chunk_size: int = 3200,
) -> List[str]:
    """
    从长文中选取代表性片段（简易 RAG 采样：分段 + 头/中/尾均匀取样）。
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size * 2:
        return [text]

    from app.services.long_text_processor import LongTextProcessor

    processor = LongTextProcessor(max_chunk_size=chunk_size, overlap_size=200, context_size=80)
    segments = processor.split_text(text)
    pieces = [s.content.strip() for s in segments if (s.content or "").strip()]
    if not pieces:
        return [text[:chunk_size]]
    if len(pieces) <= max_chunks:
        return pieces

    # 均匀采样：覆盖全文更多位置
    n = len(pieces)
    if max_chunks <= 1:
        idxs = {0}
    else:
        idxs = {
            int(round(i * (n - 1) / (max_chunks - 1)))
            for i in range(max_chunks)
        }
    return [pieces[i] for i in sorted(idxs)[:max_chunks]]


def _pick_chunks_from_sources(
    sources: List[Tuple[str, str]],
    max_chunks: int = 12,
    chunk_size: int = 3200,
) -> List[str]:
    """
    多文件/多段范文：每个来源至少采 1 段，再按篇幅分配剩余配额。
    返回带来源标记的片段，便于模型区分。
    """
    cleaned: List[Tuple[str, str]] = []
    for name, text in sources:
        t = (text or "").strip()
        if t:
            cleaned.append(((name or "范文").strip()[:80] or "范文", t))
    if not cleaned:
        return []

    # 单来源走原逻辑
    if len(cleaned) == 1:
        name, text = cleaned[0]
        chunks = _pick_representative_chunks(text, max_chunks=max_chunks, chunk_size=chunk_size)
        return [f"【来源：{name}】\n{c}" for c in chunks]

    # 多来源：按字数比例分配，每源至少 1，总和不超过 max_chunks
    total_len = sum(len(t) for _, t in cleaned) or 1
    quotas: List[int] = []
    remaining = max_chunks
    for i, (_, text) in enumerate(cleaned):
        if i == len(cleaned) - 1:
            q = max(1, remaining)
        else:
            q = max(1, round(max_chunks * len(text) / total_len))
            q = min(q, remaining - (len(cleaned) - i - 1))
        quotas.append(q)
        remaining -= q

    labeled: List[str] = []
    for (name, text), q in zip(cleaned, quotas):
        for c in _pick_representative_chunks(text, max_chunks=q, chunk_size=chunk_size):
            labeled.append(f"【来源：{name}】\n{c}")
    return labeled[:max_chunks]


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
            "user_id": agent.user_id,
            "name": agent.name,
            "description": agent.description or "",
            "preset_key": agent.preset_key,
            "config": _normalize_config(agent.config if isinstance(agent.config, dict) else {}),
            "is_default": bool(agent.is_default),
            "source": agent.source or "manual",
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "compiled_preview": compile_style_block(
                agent.name,
                agent.config if isinstance(agent.config, dict) else {},
                agent.description or "",
            ),
        }

    @staticmethod
    def list_agents(db: Session, user_id: int) -> List[WritingStyleAgent]:
        StyleAgentService.ensure_user_agents(db, user_id)
        return (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.user_id == user_id)
            .order_by(WritingStyleAgent.is_default.desc(), WritingStyleAgent.id.asc())
            .all()
        )

    @staticmethod
    def get_agent(
        db: Session, user_id: int, agent_id: int
    ) -> Optional[WritingStyleAgent]:
        return (
            db.query(WritingStyleAgent)
            .filter(
                WritingStyleAgent.user_id == user_id,
                WritingStyleAgent.id == agent_id,
            )
            .first()
        )

    @staticmethod
    def get_default_agent(db: Session, user_id: int) -> Optional[WritingStyleAgent]:
        StyleAgentService.ensure_user_agents(db, user_id)
        return (
            db.query(WritingStyleAgent)
            .filter(
                WritingStyleAgent.user_id == user_id,
                WritingStyleAgent.is_default == True,  # noqa: E712
            )
            .order_by(WritingStyleAgent.id.asc())
            .first()
        )

    @staticmethod
    def ensure_user_agents(db: Session, user_id: int) -> None:
        """若用户尚无智能体：用标准预设建一个默认。"""
        exists = (
            db.query(WritingStyleAgent.id)
            .filter(WritingStyleAgent.user_id == user_id)
            .first()
        )
        if exists:
            return

        preset = StyleAgentService.get_preset("standard") or STYLE_PRESETS[0]
        agent = WritingStyleAgent(
            user_id=user_id,
            name=preset["name"],
            description=preset.get("description") or "",
            preset_key=preset["key"],
            config=_normalize_config(preset.get("config")),
            is_default=True,
            source="preset",
        )
        db.add(agent)
        db.commit()

    @staticmethod
    def _clear_defaults(db: Session, user_id: int) -> None:
        db.query(WritingStyleAgent).filter(
            WritingStyleAgent.user_id == user_id
        ).update({"is_default": False}, synchronize_session=False)

    @staticmethod
    def create_agent(
        db: Session,
        user_id: int,
        name: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        preset_key: Optional[str] = None,
        is_default: bool = False,
        source: str = "manual",
    ) -> WritingStyleAgent:
        count = (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.user_id == user_id)
            .count()
        )
        if is_default or count == 0:
            StyleAgentService._clear_defaults(db, user_id)
            is_default = True

        agent = WritingStyleAgent(
            user_id=user_id,
            name=(name or "未命名文风").strip()[:100],
            description=(description or "").strip() or None,
            preset_key=preset_key,
            config=_normalize_config(config),
            is_default=is_default,
            source=source or "manual",
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def create_from_preset(
        db: Session, user_id: int, preset_key: str, set_default: bool = False
    ) -> WritingStyleAgent:
        preset = StyleAgentService.get_preset(preset_key)
        if not preset:
            raise ValueError(f"未知预设: {preset_key}")
        return StyleAgentService.create_agent(
            db,
            user_id=user_id,
            name=preset["name"],
            description=preset.get("description") or "",
            config=preset.get("config"),
            preset_key=preset["key"],
            is_default=set_default,
            source="preset",
        )

    @staticmethod
    def update_agent(
        db: Session,
        user_id: int,
        agent_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_default: Optional[bool] = None,
    ) -> WritingStyleAgent:
        agent = StyleAgentService.get_agent(db, user_id, agent_id)
        if not agent:
            raise ValueError("文风智能体不存在")
        if name is not None:
            agent.name = name.strip()[:100] or agent.name
        if description is not None:
            agent.description = description.strip() or None
        if config is not None:
            agent.config = _normalize_config(config)
        if is_default is True:
            StyleAgentService._clear_defaults(db, user_id)
            agent.is_default = True
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def delete_agent(db: Session, user_id: int, agent_id: int) -> None:
        agent = StyleAgentService.get_agent(db, user_id, agent_id)
        if not agent:
            raise ValueError("文风智能体不存在")
        was_default = agent.is_default
        db.delete(agent)
        db.commit()
        remaining = (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.user_id == user_id)
            .order_by(WritingStyleAgent.id.asc())
            .all()
        )
        if was_default and remaining:
            remaining[0].is_default = True
            db.commit()
        if not remaining:
            StyleAgentService.ensure_user_agents(db, user_id)

    @staticmethod
    def set_default(db: Session, user_id: int, agent_id: int) -> WritingStyleAgent:
        return StyleAgentService.update_agent(
            db, user_id, agent_id, is_default=True
        )

    @staticmethod
    def resolve_style_block_for_user(
        db: Session,
        user_id: int,
        style_agent_id: Optional[int] = None,
        *,
        use_default: bool = True,
    ) -> str:
        """按用户文风库解析风格块（无项目亦可）。"""
        agent: Optional[WritingStyleAgent] = None
        if style_agent_id:
            agent = StyleAgentService.get_agent(db, user_id, style_agent_id)
        if not agent and use_default:
            agent = StyleAgentService.get_default_agent(db, user_id)
        if not agent:
            return ""
        return compile_style_block(
            agent.name,
            agent.config if isinstance(agent.config, dict) else {},
            agent.description or "",
        )

    @staticmethod
    def resolve_style_block(
        db: Session,
        project_id: int,
        style_agent_id: Optional[int] = None,
    ) -> str:
        """解析本次写作应注入的风格块（按项目所有者的用户级文风库）。"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return ""
        block = StyleAgentService.resolve_style_block_for_user(
            db, project.owner_id, style_agent_id, use_default=True
        )
        if block:
            return block
        memory = (
            db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
        )
        if memory and (memory.writing_style or "").strip():
            return f"【写作风格】\n{memory.writing_style.strip()}"
        return ""

    @staticmethod
    def prompt_style_section(
        db: Optional[Session],
        user_id: Optional[int],
        style_agent_id: Optional[int] = None,
        fallback_label: str = "",
        *,
        use_default: bool = True,
    ) -> str:
        """
        供脑洞/热点等独立写作页注入 prompt。
        有文风智能体时用结构化块；否则回退到简短风格标签。
        """
        block = ""
        sid: Optional[int] = None
        if style_agent_id not in (None, "", 0, "0"):
            try:
                sid = int(style_agent_id)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                sid = None

        if db is not None and user_id is not None:
            if sid is not None:
                block = StyleAgentService.resolve_style_block_for_user(
                    db, int(user_id), sid, use_default=False
                )
            elif use_default:
                block = StyleAgentService.resolve_style_block_for_user(
                    db, int(user_id), None, use_default=True
                )
        if block:
            return f"\n{block}\n"
        label = (fallback_label or "").strip()
        if label:
            return f"\n风格倾向：{label}\n请尽量贴近该风格写作。\n"
        return ""

    @staticmethod
    async def extract_style_from_text(
        text: str = "",
        preferred_name: Optional[str] = None,
        sources: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        从范文提炼文风配置（支持多文件/多段；长文分段采样 + LLM）。
        sources: [(filename_or_label, text), ...]；与 text 可同时提供。
        返回 { name, description, config, compiled_preview, source_chunks, source_files }。
        """
        from app.core.ai_client import ai_client

        merged: List[Tuple[str, str]] = []
        if sources:
            for item in sources:
                if not item:
                    continue
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    merged.append((str(item[0] or "范文"), str(item[1] or "")))
        raw = (text or "").strip()
        if raw:
            merged.append(("粘贴文本", raw))

        # 过滤过短片段，但允许多文件合计达标
        merged = [(n, t.strip()) for n, t in merged if (t or "").strip()]
        total_chars = sum(len(t) for _, t in merged)
        if total_chars < 80:
            raise ValueError("文本太短，请至少提供约 80 字以上的范文（可多文件合计）")

        # 多文件最多 12 段，单文件 8 段；语料上限约 3 万字
        max_chunks = 12 if len(merged) > 1 else 8
        chunks = _pick_chunks_from_sources(merged, max_chunks=max_chunks, chunk_size=3200)
        if not chunks:
            raise ValueError("未能从提供的文本中采样到有效片段")

        corpus = "\n\n——片段分隔——\n\n".join(chunks)
        corpus_limit = 30000
        if len(corpus) > corpus_limit:
            corpus = corpus[:corpus_limit]

        source_names = [n for n, _ in merged]
        user_prompt = (
            "请综合分析以下范文（可能来自多个文件/片段），提炼统一可复用的文风 JSON。\n"
            f"来源数量：{len(merged)}；采样片段：{len(chunks)}。\n\n"
            f"{corpus}"
        )
        if preferred_name:
            user_prompt += f"\n\n若合适，name 优先使用：{preferred_name}"

        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        reply = await ai_client.chat_completion(messages, max_tokens=2500, temperature=0.3)
        data = _parse_json_object(reply)

        name = (preferred_name or data.get("name") or "提炼文风").strip()[:100]
        description = str(data.get("description") or "从范文自动提炼").strip()
        if len(merged) > 1 and "多" not in description and "综合" not in description:
            description = f"综合 {len(merged)} 份范文提炼。{description}"
        config = _normalize_config(data)
        return {
            "name": name,
            "description": description,
            "config": config,
            "compiled_preview": compile_style_block(name, config, description),
            "source_chunks": len(chunks),
            "source_files": len(merged),
            "source_names": source_names[:20],
        }
