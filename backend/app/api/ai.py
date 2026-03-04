from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import AIRequest, AIChatRequest, AIGenerateFromMemoryRequest, AIBatchGenerateRequest
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
