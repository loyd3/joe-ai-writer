import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import (
    AIRequest,
    AIChatRequest,
    AIGenerateFromMemoryRequest,
    AIBatchGenerateRequest,
    LiteraryAnalysisRequest,
    CreateProjectFromLiteratureRequest,
    CreateProjectFromLiteratureResponse,
    ApplyProjectFromLiteratureRequest,
    ApplyProjectFromLiteratureResponse,
    AIMemoryUpdate,
    LiteraryAnalysisResult,
)
from app.services.ai_writing_service import AIWritingService
from app.models.models import Document, Project
from app.api.auth import get_current_user
from app.api.projects import check_project_owner
from app.utils.document_format import parse_formatted_text_to_blocks
from app.api.dependencies import get_llm_service
from app.services.enhanced_long_article_service import EnhancedLongArticleService
from app.services.ai_memory_service import AIMemoryService
from app.services.llm_service import LLMService
from app.services.ai_image_service import AIImageService

router = APIRouter(prefix="/api/ai", tags=["ai"])


class GenerateArticleImageRequest(BaseModel):
    """根据文档内容生成一张插图并返回可插入编辑器的 image 块"""
    document_id: int = Field(..., description="文档 ID")
    style: str = Field(default="", description="画面风格，如：水彩插画 / 扁平 / 电影感")
    extra_hint: str = Field(default="", description="额外要求（可选）")
    context_text: Optional[str] = Field(
        default=None,
        description="选中段落等自定义上下文；提供且非空时仅用此文本生成插图，否则根据全文",
    )
    blocks: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="编辑器当前块快照（可选）；传入时优先用于提取正文，避免未保存时数据库内容为空",
    )

def check_document_access(db: Session, document_id: int, user_id: int):
    """检查用户是否有权限访问文档"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    project = db.query(Project).filter(
        Project.id == document.project_id,
        Project.owner_id == user_id
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return document


def _assist_blocks_from_text(text: str) -> list:
    """与脑洞写作文章一致：正文为 Markdown/块标记，解析为编辑器 blocks。"""
    if not text or not str(text).strip():
        return []
    s = str(text).strip()
    if s.startswith("[错误]") or s.startswith("[配置错误]"):
        return []
    return parse_formatted_text_to_blocks(text, "assist")


async def _ensure_outline_for_long_project(
    analysis: LiteraryAnalysisResult,
    llm_service: LLMService,
) -> LiteraryAnalysisResult:
    """
    保底：当 analyze-literature 没拿到 outline 时，用长篇写作规划生成章节级大纲，
    并映射到前端/项目设定使用的 AIMemory.outline 结构。
    """
    if analysis.outline and len(analysis.outline) > 0:
        return analysis

    try:
        long_service = EnhancedLongArticleService(llm_service)

        title = analysis.title or "未命名作品"
        # 写作风格：尽量复用文学分析结果；如果为空，用默认值
        style = analysis.writing_style or "专业严谨"
        # 主题：优先 themes[0]，否则回退到标题
        theme = (analysis.themes or [title])[0] or title

        # 目标字数：当前接口没有传入字数，这里给一个稳妥的长篇默认值
        total_word_count = 50000

        plan = await long_service.create_plan(
            title=title,
            article_type="novel",
            total_word_count=total_word_count,
            style=style,
            theme=theme,
            target_audience="一般读者",
            requirements="",
        )

        outline_nodes: list[dict] = []
        for ch in plan.chapters:
            description = ch.summary or ""
            if (not description) and ch.key_points:
                description = "、".join(ch.key_points[:3])
            outline_nodes.append({
                "title": ch.title or "章节",
                "description": description,
            })

        # 返回一个新的结果对象，避免对 Pydantic 实例的可变性产生不确定性
        return LiteraryAnalysisResult(
            title=analysis.title,
            description=analysis.description,
            category=analysis.category,
            outline=outline_nodes,
            storyline=analysis.storyline,
            characters=analysis.characters,
            world_building=analysis.world_building,
            writing_style=analysis.writing_style,
            key_points=analysis.key_points,
            themes=analysis.themes,
        )
    except Exception:
        # 保底失败时，不影响接口可用性（但 outline 可能仍为空）
        return analysis


@router.post("/assist")
async def ai_assist(
    request: AIRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """AI 辅助（非流式）"""
    document = check_document_access(db, request.document_id, current_user["id"])
    
    content = "\n".join([block.get('content', '') for block in document.content])
    response = await AIWritingService.process_request(db, request, content, current_user["id"])
    blocks = _assist_blocks_from_text(response)
    return {
        "response": response,
        "format": "markdown",
        "blocks": blocks,
    }

@router.post("/assist/stream")
async def ai_assist_stream(
    request: AIRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """AI 辅助（流式）"""
    document = check_document_access(db, request.document_id, current_user["id"])
    
    content = "\n".join([block.get('content', '') for block in document.content])
    
    async def generate():
        buf: list[str] = []
        async for chunk in AIWritingService.stream_request(db, request, content, current_user["id"]):
            buf.append(chunk)
            yield f"data: {chunk}\n\n"
        full = "".join(buf)
        blocks = _assist_blocks_from_text(full)
        if blocks:
            meta = json.dumps({"format": "markdown", "blocks": blocks}, ensure_ascii=False)
            yield f"data: [ASSIST_META]{meta}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/chat/stream")
async def ai_chat_stream(
    request: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """AI 对话（流式）"""
    # 检查文档访问权限
    check_document_access(db, request.document_id, current_user["id"])
    
    async def generate():
        buf: list[str] = []
        async for chunk in AIWritingService.chat(
            db, request.document_id, request.messages, request.include_memory, current_user["id"]
        ):
            buf.append(chunk)
            yield f"data: {chunk}\n\n"
        full = "".join(buf)
        blocks = _assist_blocks_from_text(full)
        if blocks:
            meta = json.dumps({"format": "markdown", "blocks": blocks}, ensure_ascii=False)
            yield f"data: [ASSIST_META]{meta}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/generate-from-memory/stream")
async def ai_generate_from_memory_stream(
    request: AIGenerateFromMemoryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """根据项目设定 AI 自动生成内容（流式）"""
    check_project_owner(db, request.project_id, current_user["id"])

    async def generate():
        async for chunk in AIWritingService.generate_from_memory(
            db,
            project_id=request.project_id,
            generate_type=request.generate_type,
            custom_instruction=request.custom_instruction,
            current_content=request.current_content,
            user_id=current_user["id"],
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/batch-generate/stream")
async def ai_batch_generate_stream(
    request: AIBatchGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """批量/多轮次 AI 写作（流式），基于大纲自动逐章生成"""
    check_document_access(db, request.document_id, current_user["id"])

    async def generate():
        async for chunk in AIWritingService.batch_generate(
            db,
            project_id=request.project_id,
            document_id=request.document_id,
            outline_nodes=request.outline_nodes,
            max_tokens_per_chapter=request.max_tokens_per_chapter,
            continue_on_complete=request.continue_on_complete,
            custom_instruction=request.custom_instruction,
            user_id=current_user["id"],
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/analyze-literature")
async def analyze_literature(
    request: LiteraryAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """分析文学作品，提取结构化信息"""
    analysis = await AIWritingService.analyze_literature(
        content=request.content,
        title=request.title,
        author=request.author,
        category=request.category
    )
    return analysis


@router.post("/create-project-from-literature", response_model=CreateProjectFromLiteratureResponse)
async def create_project_from_literature(
    request: CreateProjectFromLiteratureRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    llm_service: LLMService = Depends(get_llm_service),
):
    """根据解析后的作品设定创建项目（不再传原文档，不重复调用分析）"""
    from app.models.models import Project, AIMemory

    analysis = await _ensure_outline_for_long_project(request.analysis, llm_service)

    project = Project(
        title=analysis.title or "基于作品分析的项目",
        description=analysis.description,
        owner_id=current_user["id"]
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    memory = AIMemory(
        project_id=project.id,
        outline=analysis.outline,
        storyline=analysis.storyline,
        characters=[c.model_dump() for c in analysis.characters],
        world_building=analysis.world_building,
        writing_style=analysis.writing_style,
        key_points=analysis.key_points,
        notes=f"主题: {', '.join(analysis.themes)}"
    )
    db.add(memory)
    db.commit()

    return CreateProjectFromLiteratureResponse(
        project_id=project.id,
        project_title=project.title,
        analysis=analysis,
        message=f"成功创建项目 '{project.title}'，已提取 {len(analysis.characters)} 个角色，{len(analysis.outline)} 个章节"
    )


@router.post("/apply-project-from-literature", response_model=ApplyProjectFromLiteratureResponse)
async def apply_project_from_literature(
    request: ApplyProjectFromLiteratureRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    llm_service: LLMService = Depends(get_llm_service),
):
    """将文学分析结果应用到已有项目设定（覆盖项目设定）"""
    check_project_owner(db, request.project_id, current_user["id"])

    analysis = await _ensure_outline_for_long_project(request.analysis, llm_service)

    memory_update = AIMemoryUpdate(
        outline=analysis.outline,
        storyline=analysis.storyline,
        characters=[c.model_dump() for c in analysis.characters],
        world_building=analysis.world_building,
        writing_style=analysis.writing_style,
        key_points=analysis.key_points,
        notes=f"主题: {', '.join(analysis.themes)}" if analysis.themes else None,
    )

    AIMemoryService.update_memory(db, request.project_id, memory_update)

    return ApplyProjectFromLiteratureResponse(
        success=True,
        project_id=request.project_id,
        analysis=analysis,
        message=f"已覆盖项目设定：{analysis.title}",
    )


@router.post("/generate-article-image")
async def generate_article_image(
    request: GenerateArticleImageRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    根据当前文档正文生成一张配图，保存到 /static/generated_images/，
    返回 image 块（含 props.src）供前端插入编辑器。
    """
    document = check_document_access(db, request.document_id, current_user["id"])
    # 优先使用前端传入的块（含未保存编辑），否则用数据库中的 content
    blocks: List[Dict[str, Any]] = (
        list(request.blocks) if request.blocks is not None else (document.content or [])
    )
    try:
        result = await AIImageService.generate_image_from_document(
            llm_service,
            blocks,
            style=request.style or "",
            extra_hint=request.extra_hint or "",
            context_text=request.context_text,
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成插图失败: {str(e)}")


_ALLOWED_IMAGE_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post("/upload-document-image")
async def upload_document_image(
    document_id: int = Form(..., description="文档 ID，用于校验项目归属"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    上传本地图片到 static/uploads/images/，返回可供编辑器使用的 /static/... URL。
    """
    check_document_access(db, document_id, current_user["id"])
    raw_ct = (file.content_type or "").split(";")[0].strip().lower()
    ext = _ALLOWED_IMAGE_CT.get(raw_ct)
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="仅支持 jpeg、png、gif、webp 图片",
        )
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    backend_dir = Path(__file__).resolve().parent.parent
    upload_dir = backend_dir / "static" / "uploads" / "images"
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = upload_dir / name
    path.write_bytes(data)
    public_url = f"/static/uploads/images/{name}"
    return {"success": True, "url": public_url}
