from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import AIRequest, AIChatRequest, AIGenerateFromMemoryRequest, AIBatchGenerateRequest, LiteraryAnalysisRequest, CreateProjectFromLiteratureRequest, CreateProjectFromLiteratureResponse
from app.services.ai_writing_service import AIWritingService
from app.models.models import Document, Project
from app.api.auth import get_current_user
from app.api.projects import check_project_owner

router = APIRouter(prefix="/api/ai", tags=["ai"])

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
    
    return {"response": response}

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
        async for chunk in AIWritingService.stream_request(db, request, content, current_user["id"]):
            yield f"data: {chunk}\n\n"
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
        async for chunk in AIWritingService.chat(
            db, request.document_id, request.messages, request.include_memory, current_user["id"]
        ):
            yield f"data: {chunk}\n\n"
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
    current_user: dict = Depends(get_current_user)
):
    """根据解析后的作品设定创建项目（不再传原文档，不重复调用分析）"""
    from app.models.models import Project, AIMemory

    analysis = request.analysis

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
