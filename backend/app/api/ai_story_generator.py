"""
AI 故事生成器 API（一站式：主题 → 完整设定 → 写入项目记忆）

==============================================================================
定位
------------------------------------------------------------------------------
本路由挂在 `/api/ai-story-generator`，面向「从零构思一部作品」的场景：
用户给主题/类型/目标字数，AI 产出结构化故事设定（标题备选、大纲、角色、
情节点、世界观、文风建议），再可一键落到某个项目的「项目设定」(AIMemory)。

与「文档内 AI 写作」(`/api/ai/*`) 不同：这里不写正文块，只生成/落库设定。
与脑洞写作等兼容层的区别：本文件是正式前端页 `AIStoryGenerator.vue` 的主 API；
`brainstorm_compat` 会直接复用底层 `AIStoryGeneratorService`，不一定走本路由。

==============================================================================
调用链（谁用谁）
------------------------------------------------------------------------------
前端路由：`/ai-story-generator` → `frontend/src/views/AIStoryGenerator.vue`
  - POST /generate/stream      流式生成完整设定（主流程，SSE）
  - POST /quick-create-project 用已有 story_data 或再调 AI，新建项目并写入记忆
  - POST /apply-to-project     把设定应用到已有项目记忆

后端装配：`main.py` → `include_router(ai_story_generator.router)`
业务实现：`AIStoryGeneratorService`
  - generate_full_story / generate_full_story_stream
  - generate_outline_only / generate_characters
  - convert_to_project_memory  （story_data → AIMemoryUpdate 字段）

典型用户路径：
  1) 填主题 → /generate/stream → 前端展示 JSON 设定
  2a) 「应用到现有项目」→ /apply-to-project
  2b) 「一键创建项目」→ /quick-create-project（可带上一步的 story_data，避免二次生成）

==============================================================================
请求体约定
------------------------------------------------------------------------------
各接口均用宽松的 `dict` 接参（未强类型 Schema）。常用字段：
  theme, genre, word_count, chapter_count, additional_requirements,
  project_id, story_data, project_name, existing_outline, acts

鉴权：全部接口 `Depends(get_current_user)`；写项目时再校验 `Project.owner_id`。
"""

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


# ---------------------------------------------------------------------------
# 生成类：主题 → story_data（不落库）
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_story(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    非流式：根据主题生成完整故事设定。

    当前前端主路径用的是 `/generate/stream`；本接口保留给同步调用 / 调试。

    Request body:
    {
        "theme": "主题/核心概念",                 # 必填
        "genre": "故事类型（可选）",
        "word_count": 5000,                     # 目标规模，影响大纲粒度
        "chapter_count": 可选章节/幕数量,
        "additional_requirements": "额外要求（可选）"
    }

    Response: { "success": true, "data": <story_data> }
    story_data 典型键：title_options, genre, core_theme, outline, characters,
    plot_points, world_building, writing_style
    """
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    try:
        result = await AIStoryGeneratorService.generate_full_story(
            theme=theme,
            genre=request.get("genre"),
            word_count=request.get("word_count", 5000),
            chapter_count=request.get("chapter_count"),
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
    """
    流式生成完整故事设定（SSE）。

    前端 AIStoryGenerator 主入口：边生成边展示进度/片段。
    事件格式：`data: <chunk>\\n\\n`，结束为 `data: [DONE]\\n\\n`。
    chunk 内容由 Service 决定（多为文本片段或最终 JSON 字符串）。

    Body 字段同 /generate。
    """
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    async def generate():
        async for chunk in AIStoryGeneratorService.generate_full_story_stream(
            theme=theme,
            genre=request.get("genre"),
            word_count=request.get("word_count", 5000),
            chapter_count=request.get("chapter_count"),
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
    """
    仅生成大纲（轻量接口；当前主前端页未直接调用，可供分步向导扩展）。

    acts / chapter_count：幕数或章节数，默认 3。
    """
    theme = request.get("theme")
    if not theme:
        raise HTTPException(status_code=400, detail="请提供主题")
    
    try:
        result = await AIStoryGeneratorService.generate_outline_only(
            theme=theme,
            genre=request.get("genre"),
            acts=request.get("acts") or request.get("chapter_count") or 3,
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
    """
    仅生成角色卡（可带已有大纲作上下文；当前主前端页未直接调用）。

    Body:
    {
        "theme": "...",
        "existing_outline": {...} | "..."  # 可选，约束角色服务大纲
    }
    """
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


# ---------------------------------------------------------------------------
# 落库类：story_data → 项目 AIMemory（大纲/角色/世界观等）
# ---------------------------------------------------------------------------

@router.post("/apply-to-project")
async def apply_to_project(
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    将已生成的 story_data 写入指定项目的项目设定（覆盖式 update_memory）。

    前端：用户在生成器里选「应用到已有项目」时调用。
    内部：convert_to_project_memory → AIMemoryUpdate → AIMemoryService.update_memory。

    Request body:
    {
        "project_id": 1,
        "story_data": { ... }  # /generate 或 /generate/stream 得到的 data
    }

    注意：会替换该项目记忆中对应字段；调用前应确认用户知情。
    """
    project_id = request.get("project_id")
    story_data = request.get("story_data")
    
    if not project_id or not story_data:
        raise HTTPException(status_code=400, detail="请提供 project_id 和 story_data")
    
    # 仅项目所有者可写入设定
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    
    try:
        # story_data → outline / characters / storyline / world_building / ...
        memory_data = AIStoryGeneratorService.convert_to_project_memory(story_data)
        
        from app.schemas.schemas import AIMemoryUpdate
        
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
    一键：主题（或已有 story_data）→ 新建 Project → 写入 AIMemory。

    前端推荐：先 /generate/stream 拿到设定，再把 story_data 传入本接口，
    这样创建项目时不再二次调 AI，避免长时间超时。

    若未带有效 story_data，则本接口内再调 generate_full_story（耗时长）。

    Request body:
    {
        "theme": "主题",                    # 与 story_data 至少其一
        "project_name": "项目名称（可选）",  # 默认取 title_options[0] 或 theme
        "genre": "类型",
        "word_count": 5000,
        "chapter_count": 可选,
        "story_data": { ... }               # 可选；有则跳过 AI 生成
    }

    Response: { success, project: {id,name,...}, story_data }
    """
    theme = request.get("theme")
    story_data = request.get("story_data")
    
    if not theme and not story_data:
        raise HTTPException(status_code=400, detail="请提供主题或 story_data")
    
    try:
        # 1) 设定：优先复用前端已生成结果
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
                word_count=request.get("word_count", 5000),
                chapter_count=request.get("chapter_count")
            )
            if "error" in story_data:
                raise HTTPException(status_code=500, detail=f"生成失败: {story_data['error']}")
        
        # 2) 创建空项目（仅元数据；设定写在 ai_memories）
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
        
        # 3) 设定落入项目记忆，后续文档 AI 写作可经 build_memory_context 注入
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
