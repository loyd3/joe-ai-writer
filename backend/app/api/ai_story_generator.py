from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.database import get_db
from app.api.auth import get_current_user
from app.services.ai_story_generator_service import AIStoryGeneratorService
from app.services.ai_memory_service import AIMemoryService
from app.models.models import Project

router = APIRouter(prefix="/api/ai-story-generator", tags=["ai-story-generator"])


@router.post("/generate")
async def generate_story(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    根据主题生成完整的故事设定（大纲、角色、情节等）
    
    Request body:
    {
        "theme": "主题/核心概念",
        "genre": "故事类型（可选）",
        "word_count": 5000,
        "additional_requirements": "额外要求（可选）"
    }
    """
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    try:
        result = await AIStoryGeneratorService.generate_full_story(
            theme=theme,
            genre=request.get("genre"),
            word_count=request.get("word_count", 5000),
            additional_requirements=request.get("additional_requirements")
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate/stream")
async def generate_story_stream(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """流式生成故事设定"""
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    async def generate():
        async for chunk in AIStoryGeneratorService.generate_full_story_stream(
            theme=theme,
            genre=request.get("genre"),
            word_count=request.get("word_count", 5000),
            additional_requirements=request.get("additional_requirements")
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/generate-outline")
async def generate_outline(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """仅生成故事大纲"""
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    try:
        result = await AIStoryGeneratorService.generate_outline_only(
            theme=theme,
            genre=request.get("genre"),
            acts=request.get("acts", 3),
            word_count=request.get("word_count", 5000)
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate-characters")
async def generate_characters(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """生成角色设定"""
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    try:
        result = await AIStoryGeneratorService.generate_characters(
            theme=theme,
            existing_outline=request.get("existing_outline")
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/apply-to-project")
async def apply_to_project(
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    将生成的故事设定应用到项目记忆中
    
    Request body:
    {
        "project_id": 1,
        "story_data": { ... }  // AIStoryGeneratorService 生成的数据
    }
    """
    project_id = request.get("project_id")
    story_data = request.get("story_data")
    
    if not project_id or not story_data:
        raise HTTPException(status_code=400, detail="请提供 project_id 和 story_data")
    
    # 检查项目权限
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    
    try:
        # 转换为项目记忆格式
        memory_data = AIStoryGeneratorService.convert_to_project_memory(story_data)
        
        from app.schemas.schemas import AIMemoryUpdate
        
        # 更新项目记忆
        memory_update = AIMemoryUpdate(**memory_data)
        AIMemoryService.update_memory(db, project_id, memory_update)
        
        return {
            "success": True,
            "message": "故事设定已应用到项目",
            "memory_summary": {
                "outline_count": len(memory_data.get("outline", [])),
                "character_count": len(memory_data.get("characters", [])),
                "has_world_building": bool(memory_data.get("world_building"))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用失败: {str(e)}")


@router.post("/quick-create-project")
async def quick_create_project(
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    一键创建项目：主题 → 生成设定 → 保存到项目记忆。
    若请求体带 story_data（前端已生成好的设定），则跳过 AI 生成，直接创建项目，避免长时间等待。
    
    Request body:
    {
        "theme": "主题",
        "project_name": "项目名称（可选）",
        "genre": "类型",
        "word_count": 5000,
        "story_data": { ... }  // 可选，已有设定时传入则不再调用 AI
    }
    """
    theme = request.get("theme")
    story_data = request.get("story_data")
    
    if not theme and not story_data:
        raise HTTPException(status_code=400, detail="请提供主题或 story_data")
    
    try:
        # 1. 故事设定：优先使用前端已生成的，否则再调 AI（耗时长）
        if story_data and isinstance(story_data, dict) and "error" not in story_data:
            if not theme:
                theme = (
                    (story_data.get("title_options") or [None])[0]
                    or story_data.get("core_theme")
                    or "未命名"
                )
        else:
            story_data = await AIStoryGeneratorService.generate_full_story(
                theme=theme or "未命名",
                genre=request.get("genre"),
                word_count=request.get("word_count", 5000)
            )
            if "error" in story_data:
                raise HTTPException(status_code=500, detail=f"生成失败: {story_data['error']}")
        
        # 2. 创建项目
        title_options = story_data.get("title_options", [])
        project_name = request.get("project_name") or (title_options[0] if title_options else theme)
        
        project = Project(
            title=project_name,
            description=f"基于主题「{theme}」生成的{story_data.get('genre', '故事')}",
            owner_id=current_user["id"]
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # 3. 应用设定到项目
        memory_data = AIStoryGeneratorService.convert_to_project_memory(story_data)
        from app.schemas.schemas import AIMemoryUpdate
        memory_update = AIMemoryUpdate(**memory_data)
        AIMemoryService.update_memory(db, project.id, memory_update)
        
        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.title,
                "description": project.description,
                "created_at": project.created_at.isoformat()
            },
            "story_data": story_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")
