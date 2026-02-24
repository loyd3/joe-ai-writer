from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import AIMemory, Project
from app.schemas.schemas import AIMemoryUpdate, AIMemoryResponse
import json


class AIMemoryService:
    """AI 记忆管理服务 - 管理项目级别的写作上下文"""

    @staticmethod
    def get_or_create_memory(db: Session, project_id: int) -> AIMemory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project_id).first()
        if not memory:
            memory = AIMemory(project_id=project_id)
            db.add(memory)
            db.commit()
            db.refresh(memory)
        return memory

    @staticmethod
    def update_memory(db: Session, project_id: int, data: AIMemoryUpdate) -> AIMemory:
        memory = AIMemoryService.get_or_create_memory(db, project_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(memory, field, value)

        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def build_memory_context(db: Session, project_id: int) -> str:
        """构建 AI 记忆上下文字符串，用于注入到 AI 提示词中"""
        memory = AIMemoryService.get_or_create_memory(db, project_id)

        context_parts = ["=== 项目记忆 ==="]

        # 大纲
        if memory.outline:
            context_parts.append("\n【文章大纲】")
            for i, item in enumerate(memory.outline, 1):
                title = item.get("title", "未命名章节")
                context_parts.append(f"{i}. {title}")

        # 故事线
        if memory.storyline:
            context_parts.append(f"\n【故事线】\n{memory.storyline}")

        # 角色设定
        if memory.characters:
            context_parts.append("\n【角色设定】")
            for char in memory.characters:
                context_parts.append(f"\n- {char.get('name', '未命名')}:")
                context_parts.append(f"  描述: {char.get('description', '无')}")
                if char.get("personality"):
                    context_parts.append(f"  性格: {char['personality']}")
                if char.get("goals"):
                    context_parts.append(f"  目标: {char['goals']}")

        # 世界观
        if memory.world_building:
            context_parts.append("\n【世界观设定】")
            for key, value in memory.world_building.items():
                context_parts.append(f"- {key}: {value}")

        # 写作风格
        if memory.writing_style:
            context_parts.append(f"\n【写作风格】\n{memory.writing_style}")

        # 关键情节点
        if memory.key_points:
            context_parts.append("\n【关键情节点】")
            for point in memory.key_points:
                context_parts.append(f"- {point}")

        # 其他备注
        if memory.notes:
            context_parts.append(f"\n【备注】\n{memory.notes}")

        return "\n".join(context_parts) if len(context_parts) > 1 else ""

    @staticmethod
    def extract_memory_from_content(db: Session, project_id: int, content: str) -> dict:
        """从文档内容中提取可能的记忆信息（供 AI 分析后调用）"""
        # 这里可以集成 AI 来自动提取大纲、角色等信息
        # 返回结构化数据供前端或 AI 使用
        return {"suggested_outline": [], "detected_characters": [], "summary": ""}
