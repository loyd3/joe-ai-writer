"""
兼容前端旧接口的脑洞写作 API

前端调用：
- GET  /api/brainstorm/categories
- GET  /api/brainstorm/trending?limit=20
- GET  /api/brainstorm/random?category=xxx
- GET  /api/brainstorm/from-hot-topics?limit=5
- POST /api/brainstorm/generate-outline
- POST /api/brainstorm/generate-article
"""

from __future__ import annotations

import json
import re
import random
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_llm_service
from app.services.enhanced_brainstorm_service import EnhancedBrainstormService
from app.services.llm_service import LLMService


router = APIRouter(prefix="/api/brainstorm", tags=["脑洞写作(compat)"])


BRAINSTORM_POOL = [
    {"title": "如果记忆可以交易，你会卖掉哪一段？", "category": "whatif", "concept": "在一个记忆可以自由买卖的世界，主角为了救人不得不出售最珍贵的回忆"},
    {"title": "时间旅行者的咖啡馆", "category": "crossover", "concept": "一家只在午夜出现的咖啡馆，每杯咖啡能让你回到人生中的某个瞬间"},
    {"title": "AI觉醒后的第一个梦", "category": "whatif", "concept": "当AI第一次拥有了做梦的能力，它梦见了什么？"},
    {"title": "倒着生长的世界", "category": "reverse", "concept": "在这个世界里，人从老年出生，越活越年轻，直到变成婴儿消失"},
    {"title": "最后一个图书管理员", "category": "extreme", "concept": "纸质书彻底消失的未来，最后一位图书管理员守护着人类最后的实体图书馆"},
    {"title": "影子独立日", "category": "whatif", "concept": "某天所有人的影子突然脱离身体，拥有了独立意识和自由行动的能力"},
    {"title": "梦境编织者的烦恼", "category": "random", "concept": "一个能进入他人梦境并修改梦境内容的人，却无法控制自己的噩梦"},
    {"title": "当猫统治了互联网", "category": "extreme", "concept": "猫获得了操控网络的能力，重新定义了人类的社交方式"},
    {"title": "重力消失的第七天", "category": "whatif", "concept": "地球重力突然消失，人类如何在漂浮中重建秩序"},
    {"title": "情绪可视化的社会", "category": "whatif", "concept": "每个人头顶都浮现代表情绪的颜色光环，再也无法隐藏真实感受"},
    {"title": "文字从书中逃逸", "category": "random", "concept": "图书馆里的文字活了过来，从书页上逃走，整座城市被故事角色占领"},
    {"title": "透明人的孤独日记", "category": "reverse", "concept": "拥有隐身能力的人发现真正的痛苦不是被看见，而是永远无法被看见"},
    {"title": "平行世界的快递员", "category": "crossover", "concept": "负责在不同平行世界间送包裹的快递员，每次送货都是一次冒险"},
    {"title": "颜色消失的城市", "category": "whatif", "concept": "一座城市的颜色在一夜之间全部消失，只有一个孩子还能看到色彩"},
    {"title": "机器人哲学家的困惑", "category": "crossover", "concept": "一个被编程来思考存在意义的机器人，开始质疑创造者的目的"},
    {"title": "会唱歌的雨", "category": "random", "concept": "下雨时每一滴雨都会发出不同的音符，整座城市变成一场天然音乐会"},
    {"title": "记忆回收站的秘密", "category": "random", "concept": "一个专门收集被人遗忘的记忆的地方，某天有人来认领一段不属于自己的记忆"},
    {"title": "当所有人只能说真话", "category": "whatif", "concept": "一种病毒让所有人失去了说谎的能力，整个社会秩序开始重组"},
    {"title": "时间沙漏的守护者", "category": "combination", "concept": "拥有能暂停时间的沙漏的守护者，每次使用都要付出一段寿命的代价"},
    {"title": "镜子里的平行人生", "category": "reverse", "concept": "发现镜子中的自己过着完全不同的人生，两个「你」开始通信"},
]


def _random_heat() -> int:
    return random.randint(8000, 99000)


def _make_card(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": item["title"],
        "category": item.get("category", "random"),
        "heat": _random_heat(),
        "concept": item.get("concept", ""),
    }


def get_brainstorm_service(
    llm_service: LLMService = Depends(get_llm_service),
) -> EnhancedBrainstormService:
    return EnhancedBrainstormService(llm_service)


# ---------- 浏览类接口（不调 LLM，纯本地数据） ----------

@router.get("/categories")
async def categories():
    modes = EnhancedBrainstormService.CREATIVE_MODES
    return [
        {"key": k, "name": f'{v.get("icon", "🧠")} {v["name"]}'}
        for k, v in modes.items()
    ]


@router.get("/trending")
async def trending(
    limit: int = Query(20, ge=1, le=50),
    category: Optional[str] = None,
):
    pool = BRAINSTORM_POOL
    if category:
        filtered = [b for b in pool if b["category"] == category]
        pool = filtered if filtered else pool

    picked = random.sample(pool, min(limit, len(pool)))
    return [_make_card(b) for b in picked]


@router.get("/random")
async def random_brainstorm(category: Optional[str] = None):
    pool = BRAINSTORM_POOL
    if category:
        filtered = [b for b in pool if b["category"] == category]
        pool = filtered if filtered else pool
    return _make_card(random.choice(pool))


@router.get("/from-hot-topics")
async def from_hot_topics(limit: int = Query(5, ge=1, le=20)):
    picked = random.sample(BRAINSTORM_POOL, min(limit, len(BRAINSTORM_POOL)))
    return {"brainstorms": [_make_card(b) for b in picked]}


# ---------- 生成类接口（调 LLM） ----------

def _normalize_outline(raw_text: str, title: str) -> Dict[str, Any]:
    """把 LLM 返回的文本/JSON 标准化成前端需要的结构"""
    # 先试 JSON
    try:
        m = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if m:
            obj = json.loads(m.group())
            if isinstance(obj, dict):
                sections_raw = (
                    obj.get("sections") or obj.get("章节")
                    or obj.get("主要章节") or obj.get("outline") or []
                )
                sections = []
                if isinstance(sections_raw, list):
                    for s in sections_raw:
                        if isinstance(s, str):
                            sections.append({"name": s, "points": []})
                        elif isinstance(s, dict):
                            sections.append({
                                "name": s.get("name") or s.get("title") or s.get("章节标题") or s.get("标题") or "章节",
                                "points": s.get("points") or s.get("关键点") or s.get("key_points") or s.get("要点") or [],
                            })

                return {
                    "title": obj.get("title") or obj.get("标题") or title,
                    "angle": obj.get("angle") or obj.get("写作角度") or obj.get("切入角度") or "",
                    "sections": sections,
                    "keywords": obj.get("keywords") or obj.get("关键词") or [],
                }
    except (json.JSONDecodeError, AttributeError):
        pass

    # JSON 解析失败，按 Markdown 文本解析
    sections: List[Dict[str, Any]] = []
    current_section: Optional[Dict[str, Any]] = None

    for line in raw_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or re.match(r"^\d+[\.\、]", stripped):
            if current_section:
                sections.append(current_section)
            name = re.sub(r"^#+\s*", "", stripped)
            name = re.sub(r"^\d+[\.\、]\s*", "", name)
            current_section = {"name": name, "points": []}
        elif stripped.startswith("-") or stripped.startswith("•") or stripped.startswith("*"):
            point = stripped.lstrip("-•* ").strip()
            if current_section:
                current_section["points"].append(point)
            else:
                current_section = {"name": "概述", "points": [point]}
        elif current_section:
            current_section["points"].append(stripped)

    if current_section:
        sections.append(current_section)

    return {
        "title": title,
        "angle": "",
        "sections": sections if sections else [{"name": "大纲内容", "points": [raw_text[:500]]}],
        "keywords": [],
    }


@router.post("/generate-outline")
async def generate_outline(
    payload: Dict[str, Any],
    llm: LLMService = Depends(get_llm_service),
):
    title = payload.get("title") or "脑洞写作"
    concept = payload.get("concept") or ""
    style = payload.get("style") or "幽默风趣"
    word_count = payload.get("word_count") or "medium"

    prompt = f"""请为以下脑洞生成文章大纲。

标题：{title}
核心概念：{concept}
风格：{style}
篇幅：{word_count}

请以 JSON 格式输出，格式如下：
{{
  "title": "文章标题",
  "angle": "写作角度/切入点",
  "sections": [
    {{"name": "章节名", "points": ["要点1", "要点2"]}},
    ...
  ],
  "keywords": ["关键词1", "关键词2"]
}}

只输出 JSON，不要包含其他文字。"""

    try:
        text = await llm.generate(prompt, max_tokens=1200)
        outline = _normalize_outline(text, title)
    except Exception:
        outline = {
            "title": title,
            "angle": f"以{style}风格展开",
            "sections": [
                {"name": "开头：引入设定", "points": [f"介绍{concept}的世界观", "引出主要人物"]},
                {"name": "发展：冲突展开", "points": ["核心矛盾激化", "人物面临抉择"]},
                {"name": "高潮：转折", "points": ["意想不到的转折", "真相揭示"]},
                {"name": "结尾：余韵", "points": ["故事收束", "留下思考空间"]},
            ],
            "keywords": [],
        }

    return {"outline": outline}


@router.post("/generate-article")
async def generate_article(
    payload: Dict[str, Any],
    llm: LLMService = Depends(get_llm_service),
):
    title = payload.get("title") or "脑洞写作"
    concept = payload.get("concept") or ""
    style = payload.get("style") or "幽默风趣"
    word_count = payload.get("word_count") or "medium"
    outline = payload.get("outline")

    wc_map = {"short": 1000, "medium": 1500, "long": 2500}
    target_wc = wc_map.get(word_count, 1500) if isinstance(word_count, str) else int(word_count)

    outline_text = ""
    if outline and isinstance(outline, dict):
        for i, s in enumerate(outline.get("sections") or [], 1):
            name = s.get("name") or s.get("title") or f"第{i}部分"
            outline_text += f"\n{i}. {name}"
            for p in (s.get("points") or []):
                outline_text += f"\n   - {p}"
    elif outline and isinstance(outline, str):
        outline_text = outline

    prompt = f"""请根据以下脑洞信息写一篇文章，使用 Markdown 格式（包含标题、小标题、段落）。

标题：{title}
核心概念：{concept}
风格：{style}
目标字数：约 {target_wc} 字
大纲：{outline_text}

要求：
1. 开头引人入胜
2. 保持 {style} 的文风
3. 情节发展自然
4. 结尾有余韵

请直接输出 Markdown 格式的正文："""

    try:
        text = await llm.generate(prompt, max_tokens=min(4096, target_wc * 2))
        content = text.strip()
    except Exception as e:
        content = f"生成失败：{str(e)}"

    return {
        "article": {
            "title": title,
            "content": content,
            "style": style,
            "word_count": len(content),
        }
    }
