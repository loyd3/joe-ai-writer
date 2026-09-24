"""
兼容前端旧接口的脑洞写作 API

前端调用：
- GET  /api/brainstorm/categories
- GET  /api/brainstorm/trending?limit=8   # AI 生成热门脑洞
- GET  /api/brainstorm/random?category=xxx
- GET  /api/brainstorm/from-hot-topics?limit=5
- POST /api/brainstorm/generate-outline[/stream]
- POST /api/brainstorm/generate-article[/stream]
- POST /api/brainstorm/generate-project/stream  # 脑洞→新项目+设定+分章
"""

from __future__ import annotations

import json
import re
import random
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_llm_service
from app.api.auth import get_current_user
from app.database import get_db
from app.models.models import Project, Document, AIMemory, SavedBrainstorm
from app.services.enhanced_brainstorm_service import EnhancedBrainstormService
from app.services.llm_service import LLMService
from app.services.ai_story_generator_service import AIStoryGeneratorService
from app.services.ai_writing_service import AIWritingService
from app.services.document_service import _markdown_to_blocks
from sqlalchemy.orm import Session


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


# ---------- 浏览类接口（AI 生成脑洞，失败回退本地池） ----------

async def _ai_generate_brainstorms(
    llm: LLMService,
    count: int,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """用 AI 批量生成脑洞卡片"""
    mode_hint = ""
    if category and category in EnhancedBrainstormService.CREATIVE_MODES:
        mode = EnhancedBrainstormService.CREATIVE_MODES[category]
        mode_hint = f"创意模式侧重「{mode['name']}」：{mode['description']}。"

    prompt = f"""你是脑洞创意专家。请生成 {count} 个适合写成短篇小说/连载的脑洞话题。
{mode_hint}

要求：
1. 标题要抓人、有画面感（15字以内为宜）
2. concept 写清核心设定与冲突（40～80字）
3. category 从以下选一个：random, crossover, whatif, reverse, analogy, extreme, combination, constraint
4. 脑洞彼此差异大，不要重复套路

只输出 JSON 数组，不要其他文字：
[
  {{"title": "标题", "category": "whatif", "concept": "核心设定与冲突"}}
]
"""
    try:
        text = await llm.generate(prompt, max_tokens=3000, timeout=90.0)
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            raise ValueError("no json array")
        arr = json.loads(m.group())
        if not isinstance(arr, list) or not arr:
            raise ValueError("empty")
        results = []
        for item in arr[:count]:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            concept = (item.get("concept") or "").strip()
            if not title or not concept:
                continue
            cat = item.get("category") or category or "random"
            results.append(_make_card({
                "title": title,
                "category": cat,
                "concept": concept,
            }))
        if results:
            return results
    except Exception as e:
        print(f"[brainstorm] AI 生成热门脑洞失败，回退本地池: {e}")

    pool = BRAINSTORM_POOL
    if category:
        filtered = [b for b in pool if b["category"] == category]
        pool = filtered if filtered else pool
    picked = random.sample(pool, min(count, len(pool)))
    return [_make_card(b) for b in picked]


@router.get("/categories")
async def categories():
    modes = EnhancedBrainstormService.CREATIVE_MODES
    return [
        {"key": k, "name": f'{v.get("icon", "🧠")} {v["name"]}'}
        for k, v in modes.items()
    ]


@router.get("/trending")
async def trending(
    limit: int = Query(8, ge=1, le=20),
    category: Optional[str] = None,
    llm: LLMService = Depends(get_llm_service),
):
    """AI 生成热门脑洞列表"""
    return await _ai_generate_brainstorms(llm, count=limit, category=category)


@router.get("/random")
async def random_brainstorm(
    category: Optional[str] = None,
    llm: LLMService = Depends(get_llm_service),
):
    """AI 生成单个随机脑洞"""
    items = await _ai_generate_brainstorms(llm, count=1, category=category)
    return items[0] if items else _make_card(random.choice(BRAINSTORM_POOL))


@router.get("/from-hot-topics")
async def from_hot_topics(
    limit: int = Query(5, ge=1, le=20),
    llm: LLMService = Depends(get_llm_service),
):
    """基于「热点感」由 AI 生成一批脑洞（当前不接外部热点源）"""
    prompt = f"""请结合当下社会/网络常见话题方向，生成 {limit} 个脑洞（科幻、生活、职场、情感均可）。
只输出 JSON 数组：[{{"title":"...","category":"whatif","concept":"..."}}]"""
    try:
        text = await llm.generate(prompt, max_tokens=2500, timeout=90.0)
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            arr = json.loads(m.group())
            cards = []
            for item in arr[:limit]:
                if isinstance(item, dict) and item.get("title") and item.get("concept"):
                    cards.append(_make_card(item))
            if cards:
                return {"brainstorms": cards}
    except Exception as e:
        print(f"[brainstorm] from-hot-topics AI 失败: {e}")

    return {"brainstorms": await _ai_generate_brainstorms(llm, count=limit)}


# ---------- 收藏脑洞（登录用户持久化） ----------

def _saved_to_dict(row: SavedBrainstorm) -> Dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "category": row.category or "收藏",
        "concept": row.concept,
        "source": row.source or "manual",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/saved")
async def list_saved_brainstorms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = (
        db.query(SavedBrainstorm)
        .filter(SavedBrainstorm.user_id == current_user["id"])
        .order_by(SavedBrainstorm.created_at.desc())
        .all()
    )
    return {"brainstorms": [_saved_to_dict(r) for r in rows]}


@router.post("/saved")
async def save_brainstorm(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    title = (payload.get("title") or "").strip()
    concept = (payload.get("concept") or "").strip()
    if not concept:
        raise HTTPException(status_code=400, detail="核心概念不能为空")
    if not title:
        title = f"收藏脑洞｜{concept[:12]}"

    # 同一用户相同 concept 不重复收藏
    existing = (
        db.query(SavedBrainstorm)
        .filter(
            SavedBrainstorm.user_id == current_user["id"],
            SavedBrainstorm.concept == concept,
        )
        .first()
    )
    if existing:
        return {"success": True, "brainstorm": _saved_to_dict(existing), "duplicated": True}

    row = SavedBrainstorm(
        user_id=current_user["id"],
        title=title,
        category=(payload.get("category") or "收藏").strip() or "收藏",
        concept=concept,
        source=(payload.get("source") or "manual").strip() or "manual",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "brainstorm": _saved_to_dict(row), "duplicated": False}


@router.delete("/saved/{saved_id}")
async def delete_saved_brainstorm(
    saved_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = (
        db.query(SavedBrainstorm)
        .filter(
            SavedBrainstorm.id == saved_id,
            SavedBrainstorm.user_id == current_user["id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="未找到该收藏")
    db.delete(row)
    db.commit()
    return {"success": True}


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
        text = await llm.generate(prompt, max_tokens=4000, timeout=180.0)
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


@router.post("/generate-outline/stream")
async def generate_outline_stream(
    payload: Dict[str, Any],
    llm: LLMService = Depends(get_llm_service),
):
    """
    流式输出脑洞文章大纲：
    - SSE: data: <chunk>\n\n
    - 最后：data: [OUTLINE_META]{json}\n\n
    - 结束：data: [DONE]\n\n
    """
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

    async def gen():
        full = []
        try:
            async for chunk in llm.generate_stream(prompt, max_tokens=4000):
                text = str(chunk)
                if text:
                    full.append(text)
                    safe = text.replace("\n", "")
                    yield f"data: {safe}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
            yield "data: [DONE]\n\n"
            return

        raw_text = "".join(full)
        outline = _normalize_outline(raw_text, title)
        meta = json.dumps(outline, ensure_ascii=False)
        yield f"data: [OUTLINE_META]{meta}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


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
4. 结尾有余韵，但不要对称升华或金句收束
5. 写得像人手：场面先行、句长参差、对话口语、信息有取舍

{AIWritingService.ANTI_AI_STYLE_RULES}

请直接输出 Markdown 格式的正文："""

    try:
        text = await llm.generate(
            prompt,
            max_tokens=max(8000, target_wc * 3),
            timeout=300.0,
        )
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


@router.post("/generate-article/stream")
async def generate_article_stream(
    payload: Dict[str, Any],
    llm: LLMService = Depends(get_llm_service),
):
    """
    流式输出脑洞文章正文（与前端 /hot-topics/generate-article/stream 类似）。
    逐片输出 data: {text}\n\n，最后输出 data: [DONE]\n\n。
    """
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
4. 结尾有余韵，但不要对称升华或金句收束
5. 写得像人手：场面先行、句长参差、对话口语、信息有取舍

{AIWritingService.ANTI_AI_STYLE_RULES}

请直接输出 Markdown 格式的正文："""

    async def gen():
        try:
            max_tokens = max(8000, target_wc * 3)
            async for chunk in llm.generate_stream(prompt, max_tokens=max_tokens):
                text = str(chunk)
                if text:
                    yield f"data: {text}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------- 脑洞 → 新项目（提纲+设定+分章内容） ----------

def _project_scale(word_count: Any) -> tuple:
    """返回 (目标总字数, 章节数, 每章约字数)"""
    if isinstance(word_count, str):
        mapping = {
            "short": (4000, 3, 1200),
            "medium": (8000, 5, 1500),
            "long": (15000, 8, 1800),
        }
        return mapping.get(word_count, mapping["medium"])
    wc = int(word_count or 8000)
    chapters = max(3, min(wc // 1500, 12))
    return wc, chapters, max(800, wc // chapters)


@router.post("/generate-project/stream")
async def generate_project_stream(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    llm: LLMService = Depends(get_llm_service),
):
    """
    从脑洞一键创建项目：生成提纲与设定 → 建文档分章 → 逐章写正文。
    SSE 事件（JSON）：
      {type: status|project_created|memory_ready|chapter_start|chapter_done|complete|error, ...}
    """
    title = (payload.get("title") or "脑洞项目").strip()
    concept = (payload.get("concept") or "").strip()
    style = payload.get("style") or "幽默风趣"
    category = payload.get("category") or ""
    word_count = payload.get("word_count") or "medium"
    total_wc, chapter_count, per_chapter_wc = _project_scale(word_count)

    if not concept:
        raise HTTPException(status_code=400, detail="请提供脑洞核心概念 concept")

    theme = f"{title}。{concept}"
    if category:
        theme += f"（创意类型：{category}）"

    def sse(obj: Dict[str, Any]) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    async def gen():
        project_id = None
        try:
            yield sse({"type": "status", "step": "story", "message": "正在生成提纲与项目设定…"})

            story_data = await AIStoryGeneratorService.generate_full_story(
                theme=theme,
                genre=None,
                word_count=total_wc,
                chapter_count=chapter_count,
                additional_requirements=f"写作风格偏向：{style}。设定要适合连载分章展开。",
            )
            if not story_data or "error" in story_data:
                yield sse({
                    "type": "error",
                    "message": (story_data or {}).get("error") or "生成设定失败",
                })
                yield "data: [DONE]\n\n"
                return

            title_opts = story_data.get("title_options") or []
            project_title = title_opts[0] if title_opts else title

            project = Project(
                title=project_title,
                description=f"脑洞：「{title}」\n{concept[:200]}",
                owner_id=current_user["id"],
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            project_id = project.id

            yield sse({
                "type": "project_created",
                "project_id": project.id,
                "project_title": project.title,
                "message": f"已创建项目「{project.title}」",
            })

            memory_data = AIStoryGeneratorService.convert_to_project_memory(story_data)
            memory = AIMemory(
                project_id=project.id,
                outline=memory_data.get("outline") or [],
                storyline=memory_data.get("storyline"),
                characters=memory_data.get("characters") or [],
                world_building=memory_data.get("world_building") or {},
                writing_style=memory_data.get("writing_style") or style,
                key_points=memory_data.get("key_points") or [],
                notes=memory_data.get("notes") or f"来源脑洞：{title}",
            )
            db.add(memory)
            db.commit()

            outline = memory_data.get("outline") or []
            if not outline:
                outline = [
                    {"title": f"第{i+1}章", "content": concept, "act": f"第{i+1}幕"}
                    for i in range(chapter_count)
                ]
                memory.outline = outline
                db.commit()

            yield sse({
                "type": "memory_ready",
                "outline_count": len(outline),
                "character_count": len(memory_data.get("characters") or []),
                "message": f"设定已写入：{len(outline)} 章提纲，{len(memory_data.get('characters') or [])} 个角色",
            })

            chars = memory_data.get("characters") or []
            char_brief = "；".join(
                f"{c.get('name','')}（{c.get('role','')}）" for c in chars[:6] if isinstance(c, dict)
            )
            storyline = memory_data.get("storyline") or {}
            story_summary = ""
            if isinstance(storyline, dict):
                story_summary = storyline.get("summary") or ""
            elif isinstance(storyline, str):
                story_summary = storyline

            previous_summary = ""
            created_docs = []

            for idx, chapter in enumerate(outline):
                if not isinstance(chapter, dict):
                    chapter = {"title": str(chapter), "content": ""}
                ch_title = (
                    chapter.get("title")
                    or chapter.get("act")
                    or f"第{idx + 1}章"
                )
                ch_desc = chapter.get("content") or chapter.get("description") or ""

                yield sse({
                    "type": "chapter_start",
                    "index": idx,
                    "total": len(outline),
                    "title": ch_title,
                    "message": f"正在写第 {idx + 1}/{len(outline)} 章：{ch_title}",
                })

                chapter_prompt = f"""请根据项目设定撰写本章正文，使用 Markdown（可用 ## 小标题）。

【项目】{project_title}
【脑洞】{title} — {concept}
【主线】{story_summary}
【主要角色】{char_brief or '（见设定）'}
【本章】{ch_title}
【本章要点】{ch_desc}
【前文摘要】{previous_summary or '（本章为开篇）'}
【风格】{style}
【目标字数】约 {per_chapter_wc} 字

要求：
1. 只写本章正文，不要输出元说明
2. 情节承接前文、为后文留钩子
3. 人物言行符合设定
4. 直接输出 Markdown 正文
"""
                try:
                    content = await llm.generate(
                        chapter_prompt,
                        max_tokens=max(4000, per_chapter_wc * 3),
                        timeout=300.0,
                    )
                    content = (content or "").strip()
                except Exception as e:
                    content = f"（本章生成失败：{e}）\n\n要点：{ch_desc}"

                blocks = _markdown_to_blocks(content)
                doc = Document(
                    title=ch_title,
                    content=blocks,
                    project_id=project.id,
                    parent_id=None,
                    order_index=idx,
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                created_docs.append({"id": doc.id, "title": doc.title})

                previous_summary = (content[:280] + "…") if len(content) > 280 else content

                yield sse({
                    "type": "chapter_done",
                    "index": idx,
                    "total": len(outline),
                    "document_id": doc.id,
                    "title": ch_title,
                    "word_count": len(content),
                    "message": f"第 {idx + 1}/{len(outline)} 章已完成",
                })

            yield sse({
                "type": "complete",
                "project_id": project.id,
                "project_title": project.title,
                "documents": created_docs,
                "message": f"项目「{project.title}」已生成完毕，共 {len(created_docs)} 章",
            })
            yield "data: [DONE]\n\n"

        except Exception as e:
            print(f"[brainstorm] generate-project 失败: {e}")
            yield sse({
                "type": "error",
                "project_id": project_id,
                "message": str(e),
            })
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
