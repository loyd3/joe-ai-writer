from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import AIRequest, AIChatRequest
from app.services.ai_writing_service import AIWritingService
from app.models.models import Document

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/assist")
async def ai_assist(request: AIRequest, db: Session = Depends(get_db)):
    """AI 辅助（非流式）"""
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    content = "\n".join([block.get('content', '') for block in document.content])
    response = await AIWritingService.process_request(db, request, content)
    
    return {"response": response}

@router.post("/assist/stream")
async def ai_assist_stream(request: AIRequest, db: Session = Depends(get_db)):
    """AI 辅助（流式）"""
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    content = "\n".join([block.get('content', '') for block in document.content])
    
    async def generate():
        async for chunk in AIWritingService.stream_request(db, request, content):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/chat/stream")
async def ai_chat_stream(request: AIChatRequest, db: Session = Depends(get_db)):
    """AI 对话（流式）"""
    async def generate():
        async for chunk in AIWritingService.chat(
            db, request.document_id, request.messages, request.include_memory
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")