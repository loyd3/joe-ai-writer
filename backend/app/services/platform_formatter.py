"""
多平台内容格式化服务
将文档内容适配到不同自媒体平台的格式要求
"""
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    id: str
    name: str
    icon: str
    color: str
    max_title_len: int
    max_content_len: Optional[int]
    supports_markdown: bool
    supports_html: bool
    post_url: str
    description: str


PLATFORMS: Dict[str, PlatformInfo] = {
    "wechat": PlatformInfo(
        id="wechat",
        name="微信公众号",
        icon="wechat",
        color="#07C160",
        max_title_len=64,
        max_content_len=None,
        supports_markdown=False,
        supports_html=True,
        post_url="https://mp.weixin.qq.com/",
        description="支持API直接发布草稿，需要配置AppID和AppSecret",
    ),
    "xiaohongshu": PlatformInfo(
        id="xiaohongshu",
        name="小红书",
        icon="xiaohongshu",
        color="#FF2442",
        max_title_len=20,
        max_content_len=1000,
        supports_markdown=False,
        supports_html=False,
        post_url="https://creator.xiaohongshu.com/publish/publish",
        description="自动生成小红书风格文案，带emoji和话题标签",
    ),
    "zhihu": PlatformInfo(
        id="zhihu",
        name="知乎",
        icon="zhihu",
        color="#0066FF",
        max_title_len=100,
        max_content_len=None,
        supports_markdown=True,
        supports_html=False,
        post_url="https://zhuanlan.zhihu.com/write",
        description="支持Markdown长文，适合深度内容",
    ),
    "toutiao": PlatformInfo(
        id="toutiao",
        name="今日头条",
        icon="toutiao",
        color="#F85959",
        max_title_len=30,
        max_content_len=None,
        supports_markdown=False,
        supports_html=True,
        post_url="https://mp.toutiao.com/profile_v4/graphic/publish",
        description="支持HTML富文本，标题需要吸引眼球",
    ),
    "weibo": PlatformInfo(
        id="weibo",
        name="新浪微博",
        icon="weibo",
        color="#FF8200",
        max_title_len=0,
        max_content_len=2000,
        supports_markdown=False,
        supports_html=False,
        post_url="https://weibo.com/",
        description="短文本为主，支持#话题#标签",
    ),
    "bilibili": PlatformInfo(
        id="bilibili",
        name="哔哩哔哩",
        icon="bilibili",
        color="#FB7299",
        max_title_len=80,
        max_content_len=None,
        supports_markdown=True,
        supports_html=False,
        post_url="https://member.bilibili.com/platform/upload/text/edit",
        description="支持Markdown专栏文章",
    ),
    "douyin": PlatformInfo(
        id="douyin",
        name="抖音",
        icon="douyin",
        color="#000000",
        max_title_len=55,
        max_content_len=None,
        supports_markdown=False,
        supports_html=False,
        post_url="https://creator.douyin.com/creator-micro/content/upload",
        description="短视频平台，支持图文发布",
    ),
    "baijiahao": PlatformInfo(
        id="baijiahao",
        name="百家号",
        icon="baijiahao",
        color="#306CFF",
        max_title_len=30,
        max_content_len=None,
        supports_markdown=False,
        supports_html=True,
        post_url="https://baijiahao.baidu.com/builder/rc/edit",
        description="百度旗下自媒体平台，支持HTML富文本",
    ),
}


def get_platform_list() -> List[Dict[str, Any]]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "icon": p.icon,
            "color": p.color,
            "max_title_len": p.max_title_len,
            "max_content_len": p.max_content_len,
            "supports_api": p.id == "wechat",
            "post_url": p.post_url,
            "description": p.description,
        }
        for p in PLATFORMS.values()
    ]


def _blocks_to_text(blocks: list) -> str:
    parts = []
    for b in blocks:
        content = b.get("content", "")
        if not content:
            continue
        btype = b.get("type", "paragraph")
        level = b.get("props", {}).get("level", 2)
        if btype == "heading":
            parts.append(content)
        else:
            parts.append(content)
    return "\n\n".join(parts)


def _blocks_to_markdown(blocks: list) -> str:
    parts = []
    for b in blocks:
        content = b.get("content", "")
        if not content:
            continue
        btype = b.get("type", "paragraph")
        props = b.get("props", {})
        if btype == "heading":
            level = props.get("level", 2)
            parts.append(f"{'#' * level} {content}")
        elif btype == "list":
            for line in content.split("\n"):
                line = line.strip()
                if line:
                    parts.append(f"- {line}")
        elif btype == "quote":
            for line in content.split("\n"):
                parts.append(f"> {line}")
        else:
            parts.append(content)
    return "\n\n".join(parts)


def _blocks_to_html(blocks: list) -> str:
    parts = []
    for b in blocks:
        content = b.get("content", "")
        if not content:
            continue
        btype = b.get("type", "paragraph")
        props = b.get("props", {})
        if btype == "heading":
            level = min(props.get("level", 2), 4)
            parts.append(f"<h{level}>{content}</h{level}>")
        elif btype == "list":
            items = "".join(
                f"<li>{line.strip()}</li>"
                for line in content.split("\n")
                if line.strip()
            )
            parts.append(f"<ul>{items}</ul>")
        elif btype == "quote":
            parts.append(f"<blockquote>{content}</blockquote>")
        else:
            for para in content.split("\n"):
                if para.strip():
                    parts.append(f"<p>{para.strip()}</p>")
    return "\n".join(parts)


def _extract_keywords(text: str, limit: int = 5) -> List[str]:
    """简易关键词提取：取标题和高频名词短语"""
    words: Dict[str, int] = {}
    for seg in re.split(r"[，。！？、；：\s\n,.!?;:]+", text):
        seg = seg.strip()
        if 2 <= len(seg) <= 8:
            words[seg] = words.get(seg, 0) + 1
    sorted_words = sorted(words.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:limit]]


def format_for_platform(
    platform_id: str,
    title: str,
    blocks: list,
    raw_text: Optional[str] = None,
) -> Dict[str, Any]:
    """根据平台 ID 格式化文档内容"""
    info = PLATFORMS.get(platform_id)
    if not info:
        return {"error": f"不支持的平台: {platform_id}"}

    plain = raw_text or _blocks_to_text(blocks)
    md = _blocks_to_markdown(blocks)
    html = _blocks_to_html(blocks)
    keywords = _extract_keywords(plain)

    formatter = _FORMATTERS.get(platform_id, _format_generic)
    return formatter(info, title, plain, md, html, keywords, blocks)


# ── 各平台格式化器 ──────────────────────────────────────────

def _format_wechat(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    styled = _apply_wechat_style(html)
    return {
        "platform": info.id,
        "title": title[:info.max_title_len],
        "content": styled,
        "content_type": "html",
        "digest": plain[:120],
        "tags": keywords,
        "supports_api": True,
        "char_count": len(plain),
    }


def _apply_wechat_style(html: str) -> str:
    """为公众号内容添加基本内联样式"""
    html = re.sub(
        r"<h(\d)>",
        r'<h\1 style="font-weight:bold;color:#333;margin:24px 0 12px;">',
        html,
    )
    html = re.sub(
        r"<p>",
        '<p style="margin:12px 0;line-height:1.8;font-size:16px;color:#333;">',
        html,
    )
    html = re.sub(
        r"<blockquote>",
        '<blockquote style="border-left:4px solid #07C160;padding:8px 16px;'
        'margin:16px 0;color:#666;background:#f8f8f8;">',
        html,
    )
    return html


def _format_xiaohongshu(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    xhs_title = title[:info.max_title_len]
    if len(title) > info.max_title_len:
        xhs_title = title[:info.max_title_len - 1] + "…"

    body = plain
    if info.max_content_len and len(body) > info.max_content_len:
        body = body[: info.max_content_len - 50] + "\n\n...(完整内容见评论区)"

    emojis = ["✨", "💡", "🔥", "📌", "💫", "🌟", "📖", "🎯", "❤️", "👀"]
    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    decorated = []
    for i, p in enumerate(paragraphs):
        emoji = emojis[i % len(emojis)]
        decorated.append(f"{emoji} {p}")
    body_text = "\n\n".join(decorated)

    tags = " ".join(f"#{kw}#" for kw in keywords[:8])
    full_content = f"{body_text}\n\n---\n{tags}"

    return {
        "platform": info.id,
        "title": xhs_title,
        "content": full_content,
        "content_type": "text",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(full_content),
        "tips": "小红书图文建议配合3-9张图片发布效果更好",
    }


def _format_zhihu(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    return {
        "platform": info.id,
        "title": title[:info.max_title_len],
        "content": md,
        "content_type": "markdown",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(plain),
    }


def _format_toutiao(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    return {
        "platform": info.id,
        "title": title[:info.max_title_len],
        "content": html,
        "content_type": "html",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(plain),
    }


def _format_weibo(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    tags = " ".join(f"#{kw}#" for kw in keywords[:5])
    header = f"【{title}】" if title else ""
    body = plain
    max_body = (info.max_content_len or 2000) - len(header) - len(tags) - 10
    if len(body) > max_body:
        body = body[:max_body - 20] + "...(全文见长微博)"

    full = f"{header}\n{body}\n\n{tags}"
    return {
        "platform": info.id,
        "title": "",
        "content": full,
        "content_type": "text",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(full),
        "over_limit": len(full) > (info.max_content_len or 2000),
    }


def _format_bilibili(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    return {
        "platform": info.id,
        "title": title[:info.max_title_len],
        "content": md,
        "content_type": "markdown",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(plain),
    }


def _format_douyin(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    tags = " ".join(f"#{kw}#" for kw in keywords[:5])
    body = plain[:500] if len(plain) > 500 else plain
    full = f"{body}\n\n{tags}"
    return {
        "platform": info.id,
        "title": title[:info.max_title_len],
        "content": full,
        "content_type": "text",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(full),
        "tips": "抖音图文建议配合视频或图片发布",
    }


def _format_baijiahao(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    return {
        "platform": info.id,
        "title": title[:info.max_title_len],
        "content": html,
        "content_type": "html",
        "tags": keywords,
        "supports_api": False,
        "char_count": len(plain),
    }


def _format_generic(
    info: PlatformInfo, title: str, plain: str,
    md: str, html: str, keywords: List[str], blocks: list,
) -> Dict[str, Any]:
    if info.supports_html:
        content, ctype = html, "html"
    elif info.supports_markdown:
        content, ctype = md, "markdown"
    else:
        content, ctype = plain, "text"
    return {
        "platform": info.id,
        "title": title,
        "content": content,
        "content_type": ctype,
        "tags": keywords,
        "supports_api": False,
        "char_count": len(plain),
    }


_FORMATTERS = {
    "wechat": _format_wechat,
    "xiaohongshu": _format_xiaohongshu,
    "zhihu": _format_zhihu,
    "toutiao": _format_toutiao,
    "weibo": _format_weibo,
    "bilibili": _format_bilibili,
    "douyin": _format_douyin,
    "baijiahao": _format_baijiahao,
}
