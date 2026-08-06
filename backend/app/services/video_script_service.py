"""
将文章一键转换为短视频口播文案 + AI 视频生成提示词。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.services.ai_image_service import _blocks_to_context_text, _html_to_plain_text
from app.services.llm_service import LLMService


class VideoScriptService:
    SYSTEM_PROMPT = """你是一位资深短视频编导与 AI 视频提示词专家。

任务：把用户提供的文章，转换成适合短视频平台（抖音/视频号/小红书）的口播文案，并为 AI 视频生成工具写出可用提示词。

输出要求：
1) 只输出合法 JSON，不要输出任何多余解释或前后缀文本。
2) JSON 结构固定为：
{
  "video_title": "短视频标题（不超过 24 字，有悬念/冲突）",
  "hook": "前 3 秒钩子口播（一句话抓住注意力）",
  "video_script": "完整口播文案（中文，适合朗读，可含【画面】【音效】标注）",
  "scenes": [
    {
      "order": 1,
      "duration_sec": 5,
      "narration": "该镜口播",
      "visual": "该镜画面描述（中文）",
      "video_prompt": "English prompt for AI video tools (Runway/Kling/Luma), cinematic, no on-screen text"
    }
  ],
  "video_prompt": "整片统一英文视频提示词（可直接粘贴到 AI 视频工具）",
  "hashtags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "cta": "结尾行动引导（关注/评论/收藏等）"
}
3) scenes 数量建议 4-8 个，总时长尽量贴近用户指定的目标时长。
4) video_prompt / 各镜 video_prompt 必须是英文，强调镜头运动、光线、主体、氛围；禁止出现文字水印、字幕、logo。
5) 口播文案要口语化、节奏清晰，不要堆砌书面语。
"""

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        if not text:
            return {}
        cleaned = text.strip().replace("\r\n", "\n")
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE)
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not m:
            return {}
        return json.loads(m.group(0))

    @staticmethod
    def resolve_article_text(
        *,
        title: str = "",
        blocks: Optional[List[Dict[str, Any]]] = None,
        raw_content: str = "",
        max_chars: int = 8000,
    ) -> str:
        """从块或纯文本提取文章正文。"""
        parts: List[str] = []
        if title and title.strip():
            parts.append(f"标题：{title.strip()}")

        if blocks:
            body = _blocks_to_context_text(blocks, max_chars=max_chars)
            if body:
                parts.append(body)
        elif raw_content:
            plain = _html_to_plain_text(raw_content)
            if plain:
                parts.append(plain[:max_chars])

        return "\n\n".join(parts).strip()

    @classmethod
    async def convert(
        cls,
        llm: LLMService,
        *,
        title: str = "",
        blocks: Optional[List[Dict[str, Any]]] = None,
        raw_content: str = "",
        duration_sec: int = 60,
        style: str = "口播解说",
        platform: str = "抖音",
    ) -> Dict[str, Any]:
        article_text = cls.resolve_article_text(
            title=title,
            blocks=blocks,
            raw_content=raw_content,
        )
        if not article_text or len(article_text) < 20:
            raise ValueError("文章内容过短，请先写入足够正文后再转换")

        duration_sec = max(15, min(int(duration_sec or 60), 180))
        style = (style or "口播解说").strip()
        platform = (platform or "抖音").strip()

        user_prompt = f"""请将以下文章转换成短视频方案。

目标平台：{platform}
视频风格：{style}
目标时长：约 {duration_sec} 秒

文章内容：
---
{article_text}
---
"""
        text = await llm.generate_text(
            user_prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            temperature=0.7,
        )
        data = cls._extract_json(text)
        if not data:
            raise ValueError("AI 未返回有效 JSON，请重试")

        video_script = (data.get("video_script") or "").strip()
        video_prompt = (data.get("video_prompt") or "").strip()
        if not video_script or not video_prompt:
            raise ValueError("转换结果不完整：缺少视频文案或 AI 视频提示词")

        scenes = data.get("scenes") or []
        if not isinstance(scenes, list):
            scenes = []
        normalized_scenes = []
        for i, s in enumerate(scenes):
            if not isinstance(s, dict):
                continue
            normalized_scenes.append({
                "order": int(s.get("order") or i + 1),
                "duration_sec": int(s.get("duration_sec") or 5),
                "narration": str(s.get("narration") or "").strip(),
                "visual": str(s.get("visual") or "").strip(),
                "video_prompt": str(s.get("video_prompt") or "").strip(),
            })

        hashtags = data.get("hashtags") or []
        if not isinstance(hashtags, list):
            hashtags = []
        hashtags = [str(t).strip().lstrip("#") for t in hashtags if str(t).strip()]

        return {
            "video_title": str(data.get("video_title") or title or "短视频文案").strip(),
            "hook": str(data.get("hook") or "").strip(),
            "video_script": video_script,
            "scenes": normalized_scenes,
            "video_prompt": video_prompt,
            "hashtags": hashtags[:8],
            "cta": str(data.get("cta") or "").strip(),
            "duration_sec": duration_sec,
            "style": style,
            "platform": platform,
        }
