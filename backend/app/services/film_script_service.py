"""
将文章一键转换为影视脚本（Markdown 长文本，用于生成新文档）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.llm_service import LLMService
from app.services.video_script_service import VideoScriptService


class FilmScriptService:
    SYSTEM_PROMPT = """你是一位资深影视编剧，擅长把小说、故事、文章改写成标准影视脚本。

任务：把用户提供的文章内容，改写成规范、可直接阅读的影视脚本。

输出要求：
1) 直接输出 Markdown 格式的脚本文本，不要输出任何解释或前后缀说明。
2) 第一行为脚本标题，格式：# 《脚本标题》
3) 正文按场次组织，每场格式：
## 第X场 场景名 - 内景/外景 - 日/夜
【出场人物】角色甲、角色乙

画面与镜头描述（段落形式，写清楚环境、人物动作、神态、必要的镜头提示）。

角色甲：台词内容
角色乙：台词内容

（需要时用"旁白："引出画外音/旁白。）
4) 场次数量根据原文情节容量合理安排（一般 3-10 场），情节推进忠实于原文，不得虚构原文没有的主线情节与结局。
5) 对白要符合人物身份与语气，画面描述要具体、可视化。
"""

    @classmethod
    async def convert(
        cls,
        llm: LLMService,
        *,
        title: str = "",
        blocks: Optional[List[Dict[str, Any]]] = None,
        raw_content: str = "",
    ) -> Dict[str, Any]:
        article_text = VideoScriptService.resolve_article_text(
            title=title,
            blocks=blocks,
            raw_content=raw_content,
        )
        if not article_text or len(article_text) < 20:
            raise ValueError("文章内容过短，请先写入足够正文后再转换")

        user_prompt = f"""请将以下文章改写成影视脚本。

文章内容：
---
{article_text}
---
"""
        script_text = (
            await llm.generate_text(
                user_prompt,
                system_prompt=cls.SYSTEM_PROMPT,
                temperature=0.7,
            )
            or ""
        ).strip()
        if not script_text:
            raise ValueError("AI 未返回有效脚本，请重试")

        script_title = (title or "").strip()
        first_line = script_text.splitlines()[0].strip() if script_text else ""
        if first_line.startswith("#"):
            heading = first_line.lstrip("#").strip().strip("《》")
            if heading:
                script_title = heading

        return {
            "script_title": script_title or "影视脚本",
            "script_text": script_text,
        }
