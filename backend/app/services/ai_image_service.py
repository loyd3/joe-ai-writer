"""
根据文档内容生成插图：先用 LLM 生成英文绘图提示词，再调用 OpenAI 兼容的 images/generations 接口，
将图片保存到 static/generated_images 并返回可访问 URL。
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.services.llm_service import LLMService


def _html_to_plain_text(raw: str) -> str:
    """编辑器块 content 多为 HTML，去掉标签后再判断是否为空。"""
    if not raw or not isinstance(raw, str):
        return ""
    t = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[ \t\f\v]+", " ", t)
    t = "\n".join(line.strip() for line in t.splitlines())
    return t.strip()


def _blocks_to_context_text(blocks: List[Dict[str, Any]], max_chars: int = 6000) -> str:
    """将块列表转为纯文本，供生成插图提示词使用。"""
    parts: List[str] = []
    for b in blocks or []:
        btype = b.get("type", "paragraph")
        raw = b.get("content") or ""
        c = _html_to_plain_text(str(raw)) if isinstance(raw, str) else ""
        if btype == "image":
            parts.append("[插图]")
            continue
        if btype == "divider":
            continue
        if c:
            parts.append(c)
    text = "\n".join(parts)
    return text[:max_chars]


def _get_image_api_config() -> Tuple[str, str, str]:
    s = get_settings()
    api_key = (getattr(s, "image_api_key", None) or "").strip()
    if not api_key:
        # 未单独配置时：若主线路为 OpenAI，可复用 openai_api_key
        if getattr(s, "ai_provider", "") == "openai" and (s.openai_api_key or "").strip():
            api_key = s.openai_api_key.strip()
    base = (getattr(s, "image_base_url", None) or "https://api.openai.com/v1").strip().rstrip("/")
    model = (getattr(s, "image_model", None) or "dall-e-3").strip()
    return api_key, base, model


async def _llm_image_prompt(llm: LLMService, article_excerpt: str, style: str, extra: str) -> str:
    system = """You are an expert art director for editorial illustrations.
Output a single JSON object ONLY, no markdown:
{"prompt": "English prompt for an image generation model, max 1200 characters"}
Rules:
- The image must match the article mood and theme; no text/letters/watermarks in the image.
- Avoid real people's names or trademarked logos.
- Describe composition, lighting, style (e.g. editorial illustration, soft watercolor, cinematic).
"""
    user = f"""Article excerpt (may be Chinese):
---
{article_excerpt}
---
Visual style hint: {style or "clean editorial illustration"}
Extra requirements: {extra or "none"}
"""
    text = await llm.generate_text(user, system_prompt=system, temperature=0.6)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("LLM 未返回合法 JSON")
    obj = json.loads(m.group())
    p = (obj.get("prompt") or "").strip()
    if not p:
        raise ValueError("绘图提示词为空")
    return p[:1200]


async def _call_images_generations(api_key: str, base_url: str, model: str, prompt: str) -> str:
    """调用 OpenAI 兼容 images/generations，返回图片下载 URL。"""
    url = f"{base_url}/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "url",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise ValueError(f"图片生成接口错误 {r.status_code}: {detail}")
        data = r.json()
    items = data.get("data") or []
    if not items:
        raise ValueError("图片生成返回为空")
    u = items[0].get("url")
    if not u:
        # 部分兼容接口只返回 b64_json
        b64 = items[0].get("b64_json")
        if b64:
            import base64

            raw = base64.b64decode(b64)
            return await _save_bytes_and_get_url(raw)
        raise ValueError("图片生成未返回 url")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        ir = await client.get(u)
        ir.raise_for_status()
        return await _save_bytes_and_get_url(ir.content)


async def _save_bytes_and_get_url(data: bytes) -> str:
    backend_dir = Path(__file__).resolve().parent.parent
    static_dir = backend_dir / "static" / "generated_images"
    static_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    path = static_dir / name
    path.write_bytes(data)
    return f"/static/generated_images/{name}"


class AIImageService:
    @staticmethod
    async def generate_image_from_document(
        llm: LLMService,
        blocks: List[Dict[str, Any]],
        style: str = "",
        extra_hint: str = "",
        context_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        context_text: 若传入非空字符串，则仅用其作为插图上下文（如多选段落），否则用全文块拼接。
        """
        if context_text is not None and str(context_text).strip():
            excerpt = _html_to_plain_text(str(context_text))[:6000]
            if not excerpt:
                excerpt = str(context_text).strip()[:6000]
        else:
            excerpt = _blocks_to_context_text(blocks)
        if not excerpt.strip():
            raise ValueError("文档内容为空，无法生成插图")

        api_key, base_url, model = _get_image_api_config()
        if not api_key:
            raise ValueError(
                "未配置图片生成 API：请在 .env 设置 IMAGE_API_KEY（或主线路为 openai 时配置 OPENAI_API_KEY），"
                "并设置 IMAGE_BASE_URL（默认 https://api.openai.com/v1）与 IMAGE_MODEL（默认 dall-e-3）"
            )

        prompt = await _llm_image_prompt(llm, excerpt, style, extra_hint)
        public_url = await _call_images_generations(api_key, base_url, model, prompt)

        block_id = uuid.uuid4().hex[:12]
        block: Dict[str, Any] = {
            "id": block_id,
            "type": "image",
            "content": "",
            "props": {
                "src": public_url,
                "alt": "插图",
                "prompt": prompt,
            },
        }
        return {
            "image_url": public_url,
            "prompt": prompt,
            "block": block,
        }
