from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import AIRequest, AIChatRequest
from app.services.ai_writing_service import AIWritingService
from app.models.models import Document, Project
from app.api.auth import get_current_user

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
