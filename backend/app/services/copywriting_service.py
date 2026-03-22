"""
文案写作服务

面向广告/推销/引流场景生成可直接保存为文档的 Markdown 文本。
平台风格（如微信公众号/小红书/知乎等）交由前端的 PublishDialog
通过后端 `platform_formatter.py` 统一格式化适配。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, List

from app.services.llm_service import LLMService


class CopywritingService:
    SYSTEM_PROMPT = """你是一位资深的营销文案编辑与内容策划专家。

你的任务是根据用户提供的信息，撰写“广告/推销/引流”类文案。

输出要求：
1) 只输出合法 JSON，不要输出任何多余解释或前后缀文本。
2) JSON 结构固定为：
{
  "title": "文案标题（不超过 30 字，尽量吸引点击）",
  "content": "文案正文（Markdown 格式）",
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"]
}
3) content 的 Markdown 写法要求：
   - 使用 ## 作为二级标题（可选多次）
   - 允许使用段落换行（空一行分段）
   - 使用 - 开头的列表（可选）
   - 不要包含任何话题标签（不要出现 #xxx# 或 #xxx）与表情符号（emoji 交由平台格式化器处理）
   - 末尾必须包含一个明确的“行动引导”，例如：私信/评论/表单/加群/领取资料等（但不要编造保证/承诺）

风格要求：
- 语言要符合中文自媒体的阅读习惯：短句、信息密度适中、逻辑清晰。
- 避免夸大承诺或不实保证，不要出现“绝对”“100%”“保证有效”等措辞。
"""

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """
        从模型输出中提取 JSON。
        兼容：模型可能带有代码块或多余文本。
        """
        if not text:
            return {}

        # 去掉可能的 markdown 代码块标记
        cleaned = text.strip()
        cleaned = cleaned.replace("\r\n", "\n")
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE)

        # 尝试抓取第一个 { ... } 片段
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not m:
            return {}

        raw = m.group(0)
        return json.loads(raw)

    @staticmethod
    async def generate_copywriting(
        llm: LLMService,
        *,
        product: str,
        target_audience: str,
        copy_objective: str,
        selling_points: str,
        pain_points: str = "",
        evidence_cases: str = "",
        cta: str = "",
        tone: str = "专业且有说服力",
        word_count: int = 900,
        additional_requirements: str = "",
    ) -> Dict[str, Any]:
        """
        生成营销文案：
        - 返回 title/content/keywords
        - content 为 Markdown，供后端解析为文档块
        """
        product = (product or "").strip()
        target_audience = (target_audience or "").strip()
        selling_points = (selling_points or "").strip()

        if not product:
            product = "你的产品或服务"
        if not target_audience:
            target_audience = "目标用户"
        if not selling_points:
            selling_points = "核心卖点与优势"

        prompt = f"""用户信息如下：
- 文案目标：{copy_objective}
- 产品/服务：{product}
- 目标人群：{target_audience}
- 核心卖点/差异化：{selling_points}
- 目标用户痛点（可选）：{pain_points}
- 证据/案例/体验（可选）：{evidence_cases}
- 行动引导/引流方式（可选）：{cta}
- 写作语气：{tone}
- 预计长度（字数）：{word_count}
- 额外要求（可选）：{additional_requirements}

请生成适合广告/推销/引流的文案内容。
注意：不要输出任何话题标签和 emoji。
"""

        max_tokens = max(900, int(word_count * 2.5))

        # 该项目的 LLMService generate_text 支持 system_prompt
        raw = await llm.generate_text(
            prompt,
            system_prompt=CopywritingService.SYSTEM_PROMPT,
            model=None,
            temperature=0.7,
        )

        try:
            obj = CopywritingService._extract_json(raw)
            if not isinstance(obj, dict):
                raise ValueError("invalid json object")
        except Exception:
            # 兜底：尽量给出可用文案
            title = f"{product}：一篇让你看懂并愿意行动的文案"
            content = (
                "## 一句话抓住重点\n\n"
                f"你现在最关心的是：{pain_points or '找到更有效的解决方案'}。"
                f"\n\n我们为你准备了{product}的核心优势：{selling_points}。"
                "\n\n"
                "## 怎么做到更好\n\n"
                "- 用更清晰的方式帮你理解关键点\n"
                "- 用更省时间的流程推进决策\n"
                "- 用可执行的步骤降低上手成本\n\n"
                "## 行动引导\n\n"
                f"{cta or '在评论区留下你的需求，我把详细资料发给你'}。"
            )
            keywords = [w for w in [product, copy_objective, "引流", "卖点", "行动"] if w][:5]
            return {"title": title, "content": content, "keywords": keywords}

        # 强制补齐字段，避免前端/平台格式化器取不到
        title = str(obj.get("title") or "").strip() or product
        content = str(obj.get("content") or "").strip()
        keywords = obj.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        if not isinstance(keywords, list):
            keywords = []

        if not content:
            content = "## 行动引导\n\n" + (cta or "欢迎私信/评论领取资料。")

        # 去掉可能混入的 #话题标签/emoji，尽量符合平台格式化器的职责划分
        content = re.sub(r"#.{1,30}#|#.{1,30}\b", "", content).strip()

        return {"title": title, "content": content, "keywords": keywords[:10]}

