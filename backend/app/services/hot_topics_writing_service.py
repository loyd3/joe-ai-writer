"""
热点写作服务 - 热点 → 提纲 → 文章 全流程
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from app.services.hot_topics_service import HotTopicsService
from app.core.ai_client import ai_client
from app.services.ai_memory_service import AIMemoryService
from app.models.models import Document, Project, AIInteraction
import json


class HotTopicsWritingService:
    """热点写作服务 - 将热点话题转化为文章"""
    
    # 生成提纲的系统提示词
    OUTLINE_SYSTEM_PROMPT = """你是一位资深的选题策划和编辑专家。你的任务是根据提供的热点话题，生成一篇高质量的文章大纲。

要求：
1. 分析热点话题的核心价值和读者关注点
2. 确定文章的角度和立场
3. 设计吸引人的标题（提供3个备选）
4. 规划文章结构，包括：
   - 引人入胜的开头（如何抓住读者）
   - 主体部分的逻辑层次（3-5个要点）
   - 有力的结尾（升华主题或引发思考）
5. 每个部分标注预估字数和写作要点

输出格式必须是JSON：
{
    "title_options": ["标题1", "标题2", "标题3"],
    "angle": "文章切入角度",
    "target_audience": "目标读者群体",
    "structure": [
        {
            "section": "章节名称",
            "word_count": 预估字数,
            "key_points": ["要点1", "要点2"],
            "writing_tips": "写作技巧提示"
        }
    ],
    "keywords": ["关键词1", "关键词2"],
    "tone": "文章基调（如：严肃/轻松/深度/娱乐）"
}"""

    # 生成文章的系统提示词
    ARTICLE_SYSTEM_PROMPT = """你是一位专业的写作者。根据提供的大纲，撰写一篇完整、流畅、有深度的文章。

写作要求：
1. 严格按照大纲结构组织内容
2. 开头要吸引人，快速进入主题
3. 每个段落有明确的主题句
4. 使用恰当的过渡词保持段落间连贯
5. 适当使用修辞手法增强表现力
6. 结尾要有力，给读者留下深刻印象
7. 语言风格与大纲指定的基调一致

注意事项：
- 保持客观理性，避免过度情绪化表达
- 确保事实准确，对敏感话题保持中立
- 文章要有信息增量，不只是热点复述
- 字数要达到大纲要求"""

    @staticmethod
    async def get_hot_topics() -> Dict[str, Any]:
        """获取网络热点列表"""
        return await HotTopicsService.fetch_all_hot_topics()
    
    @staticmethod
    async def generate_outline(
        topic_title: str,
        topic_source: str = "",
        article_type: str = "深度分析",
        word_count: int = 1500,
        style: str = "专业"
    ) -> Dict[str, Any]:
        """
        根据热点话题生成文章大纲
        
        Args:
            topic_title: 热点标题
            topic_source: 来源平台
            article_type: 文章类型
            word_count: 目标字数
            style: 写作风格
        """
        messages = [
            {"role": "system", "content": HotTopicsWritingService.OUTLINE_SYSTEM_PROMPT},
            {"role": "user", "content": f"""请为以下热点话题生成文章大纲：

话题：{topic_title}
来源：{topic_source}
文章类型：{article_type}
目标字数：{word_count}字
写作风格：{style}

请确保输出是合法的JSON格式。"""}
        ]
        
        try:
            response = await ai_client.chat_completion(messages)
            
            # 尝试解析JSON
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            outline = json.loads(json_str.strip())
            
            outline["topic"] = topic_title
            outline["source"] = topic_source
            outline["article_type"] = article_type
            outline["target_word_count"] = word_count
            outline["style"] = style
            
            return outline
            
        except json.JSONDecodeError as e:
            return {
                "error": "大纲生成失败，AI返回格式不正确",
                "raw_response": response,
                "parse_error": str(e),
                "topic": topic_title
            }
        except Exception as e:
            return {
                "error": f"大纲生成失败: {str(e)}",
                "topic": topic_title
            }
    
    @staticmethod
    async def generate_outline_stream(
        topic_title: str,
        topic_source: str = "",
        article_type: str = "深度分析",
        word_count: int = 1500,
        style: str = "专业"
    ) -> AsyncGenerator[str, None]:
        """流式生成大纲"""
        messages = [
            {"role": "system", "content": HotTopicsWritingService.OUTLINE_SYSTEM_PROMPT},
            {"role": "user", "content": f"""请为以下热点话题生成文章大纲：

话题：{topic_title}
来源：{topic_source}
文章类型：{article_type}
目标字数：{word_count}字
写作风格：{style}

请确保输出是合法的JSON格式。"""}
        ]
        
        async for chunk in ai_client.stream_completion(messages):
            yield chunk
    
    @staticmethod
    async def generate_article(
        outline: Dict[str, Any],
        selected_title: Optional[str] = None,
        additional_requirements: Optional[str] = None
    ) -> str:
        """根据大纲生成完整文章"""
        title = selected_title or outline.get("title_options", ["热点文章"])[0]
        structure = outline.get("structure", [])
        tone = outline.get("tone", "专业")
        target_words = outline.get("target_word_count", 1500)
        topic = outline.get("topic", "")
        
        outline_text = f"标题：{title}\n"
        outline_text += f"基调：{tone}\n"
        outline_text += f"目标字数：{target_words}字\n\n"
        outline_text += "文章结构：\n"
        
        for idx, section in enumerate(structure, 1):
            outline_text += f"\n{idx}. {section.get('section', '未命名章节')}\n"
            outline_text += f"   字数：{section.get('word_count', 200)}字\n"
            outline_text += f"   要点：{', '.join(section.get('key_points', []))}\n"
            if section.get('writing_tips'):
                outline_text += f"   提示：{section.get('writing_tips')}\n"
        
        user_prompt = f"""请根据以下大纲撰写一篇完整的文章：

{outline_text}

原始话题：{topic}
"""
        
        if additional_requirements:
            user_prompt += f"\n额外要求：{additional_requirements}\n"
        
        user_prompt += f"\n请直接输出文章正文，不需要包含'文章正文'等标记。字数要达到{target_words}字左右。"
        
        messages = [
            {"role": "system", "content": HotTopicsWritingService.ARTICLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        return await ai_client.chat_completion(messages)
    
    @staticmethod
    async def generate_article_stream(
        outline: Dict[str, Any],
        selected_title: Optional[str] = None,
        additional_requirements: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成文章"""
        title = selected_title or outline.get("title_options", ["热点文章"])[0]
        structure = outline.get("structure", [])
        tone = outline.get("tone", "专业")
        target_words = outline.get("target_word_count", 1500)
        topic = outline.get("topic", "")
        
        outline_text = f"标题：{title}\n"
        outline_text += f"基调：{tone}\n"
        outline_text += f"目标字数：{target_words}字\n\n"
        outline_text += "文章结构：\n"
        
        for idx, section in enumerate(structure, 1):
            outline_text += f"\n{idx}. {section.get('section', '未命名章节')}\n"
            outline_text += f"   字数：{section.get('word_count', 200)}字\n"
            outline_text += f"   要点：{', '.join(section.get('key_points', []))}\n"
        
        user_prompt = f"""请根据以下大纲撰写一篇完整的文章：

{outline_text}

原始话题：{topic}
"""
        
        if additional_requirements:
            user_prompt += f"\n额外要求：{additional_requirements}\n"
        
        messages = [
            {"role": "system", "content": HotTopicsWritingService.ARTICLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        async for chunk in ai_client.stream_completion(messages):
            yield chunk
    
    @staticmethod
    async def create_document_from_article(
        db: Session,
        project_id: int,
        title: str,
        content: str,
        outline_data: Optional[Dict[str, Any]] = None,
        user_id: int = None
    ) -> Document:
        """将生成的文章保存为文档"""
        from app.schemas.schemas import Block
        
        blocks = []
        paragraphs = content.split('\n\n')
        
        for idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
                
            if para.startswith('#') or (len(para) < 30 and not any(c in para for c in '。，！？.,!?')):
                block_type = "heading"
                para = para.lstrip('#').strip()
            else:
                block_type = "paragraph"
            
            blocks.append({
                "id": f"block-{idx}",
                "type": block_type,
                "content": para,
                "props": {}
            })
        
        if not blocks:
            blocks = [{
                "id": "block-0",
                "type": "paragraph",
                "content": content or "",
                "props": {}
            }]
        
        document = Document(
            title=title,
            project_id=project_id,
            content=blocks,
            parent_id=None,
            order_index=0
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        if outline_data:
            interaction = AIInteraction(
                document_id=document.id,
                interaction_type="hot_topic_article",
                user_input=json.dumps(outline_data, ensure_ascii=False),
                ai_response=content[:1000] + "..." if len(content) > 1000 else content,
                context_used={"outline": outline_data, "auto_created": True}
            )
            db.add(interaction)
            db.commit()
        
        return document
