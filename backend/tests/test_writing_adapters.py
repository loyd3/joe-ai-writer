"""writing_adapters：只生成不落库，mock 下游服务。"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest


def test_copywriting_generate_returns_unified_shape():
    from app.services import writing_adapters

    async def _fake_gen(*args, **kwargs):
        return {"title": "卖点文案", "content": "## 开头\n\n正文内容", "keywords": ["A"]}

    with patch(
        "app.services.writing_adapters.CopywritingService.generate_copywriting",
        new=AsyncMock(side_effect=_fake_gen),
    ):
        result = asyncio.run(
            writing_adapters.copywriting_generate(
                product="墨心",
                target_audience="作者",
                selling_points="AI 写作",
            )
        )
    assert result["kind"] == "copywriting"
    assert result["title"] == "卖点文案"
    assert "正文" in result["content"]
    assert result["meta"]["product"] == "墨心"


def test_hot_topics_list_and_generate():
    from app.services import writing_adapters

    async def _list(*args, **kwargs):
        return {
            "topics": [{"title": "热点甲", "heat": 99, "source": "test", "category": "社会"}],
            "is_fallback": True,
            "message": "ok",
            "data_source": "fallback",
        }

    async def _outline(*args, **kwargs):
        return {
            "outline": {
                "title_options": ["标题甲"],
                "structure": [{"section": "一", "key_points": ["点"], "word_count": 200}],
                "angle": "评",
                "target_audience": "读者",
            }
        }

    async def _article(*args, **kwargs):
        return "这是一篇完整的热点评论文章正文。" * 3

    with patch.object(
        writing_adapters,
        "_hot_service",
        return_value=type(
            "S",
            (),
            {
                "get_hot_topics": AsyncMock(side_effect=_list),
                "generate_article_outline": AsyncMock(side_effect=_outline),
            },
        )(),
    ), patch(
        "app.services.writing_adapters.HotTopicsWritingService.generate_article",
        new=AsyncMock(side_effect=_article),
    ):
        listed = asyncio.run(writing_adapters.list_hot_topics(limit=5))
        assert listed["kind"] == "hot_topics_list"
        assert listed["topics"][0]["title"] == "热点甲"

        article = asyncio.run(
            writing_adapters.hot_topic_generate(topic_title="热点甲", word_count=800)
        )
        assert article["kind"] == "hot_topic_article"
        assert article["title"] == "标题甲"
        assert "热点评论" in article["content"]


def test_brainstorm_list_and_write():
    from app.services import writing_adapters

    listed = writing_adapters.list_brainstorm_ideas(limit=3)
    assert listed["kind"] == "brainstorm_ideas"
    assert listed["ideas"]
    assert listed["categories"]

    async def _outline(*args, **kwargs):
        return {"title": "脑洞标题", "sections": [{"name": "引", "points": ["a"]}]}

    async def _article(*args, **kwargs):
        return {"title": "脑洞标题", "content": "脑洞正文足够长了。"}

    with patch(
        "app.services.writing_adapters.BrainstormWritingService.generate_outline",
        new=AsyncMock(side_effect=_outline),
    ), patch(
        "app.services.writing_adapters.BrainstormWritingService.generate_article",
        new=AsyncMock(side_effect=_article),
    ):
        result = asyncio.run(
            writing_adapters.brainstorm_write(title="如果时间倒流", concept="时间")
        )
    assert result["kind"] == "brainstorm_article"
    assert result["title"] == "脑洞标题"
    assert "脑洞正文" in result["content"]


def test_story_generate_and_memory_fields():
    from app.services import writing_adapters

    fake_story = {
        "title_options": ["故事一"],
        "characters": [{"name": "阿墨", "role": "主角", "personality": "冷静"}],
        "outline": [{"title": "开端", "description": "遇见"}],
        "plot_points": ["转折"],
        "world_building": {"era": "近未来"},
        "core_theme": "成长",
        "input_theme": "AI 觉醒",
        "genre": "科幻",
        "writing_style": {"tone": "冷静克制"},
    }

    with patch(
        "app.services.writing_adapters.AIStoryGeneratorService.generate_full_story",
        new=AsyncMock(return_value=fake_story),
    ):
        result = asyncio.run(writing_adapters.story_generate(theme="AI 觉醒", genre="科幻"))
    assert result["kind"] == "story_settings"
    assert result["story_data"]["genre"] == "科幻"
    fields = writing_adapters.story_to_memory_fields(fake_story)
    assert "characters" in fields
    assert fields["characters"][0]["name"] == "阿墨"


def test_preview_and_draft_id():
    from app.services import writing_adapters

    assert writing_adapters.new_draft_id().startswith("draft_")
    assert writing_adapters.preview_text("短") == "短"
    long = "字" * 500
    assert writing_adapters.preview_text(long, 100).endswith("…")
    assert len(writing_adapters.preview_text(long, 100)) == 101
