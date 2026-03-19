"""
AI 自动写作 API 路由
基于大纲设定，逐章生成并插入到对应文档
"""
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from typing import Optional
from pydantic import BaseModel, Field
from app.services.auto_write_service import AutoWriteService
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.services.project_service import ProjectService
from app.api.dependencies import get_llm_service, get_document_service, get_project_service
import json

router = APIRouter(prefix="/auto-write", tags=["AI自动写作"])


class AutoWriteRequest(BaseModel):
    project_id: int = Field(..., description="项目ID")
    document_id: int = Field(..., description="文档ID")
    outline_nodes: list = Field(..., description="大纲节点列表")
    max_tokens_per_chapter: int = Field(default=2000, ge=500, le=8000, description="每章最大token数")
    continue_on_complete: bool = Field(default=True, description="完成后是否继续")
    custom_instruction: Optional[str] = Field(default=None, description="自定义指令")


class AutoWriteChapterRequest(BaseModel):
    project_id: int = Field(..., description="项目ID")
    document_id: int = Field(..., description="文档ID")
    node: dict = Field(..., description="大纲节点")
    chapter_index: int = Field(..., description="章节索引")
    total_chapters: int = Field(..., description="总章节数")
    max_tokens: int = Field(default=2000, ge=500, le=8000)
    custom_instruction: Optional[str] = Field(default=None)
    previous_chapter_summary: Optional[str] = Field(default=None, description="前一章摘要，用于保持连贯性")


@router.post("/generate-stream")
async def auto_write_stream(
    request: AutoWriteRequest,
    llm_service: LLMService = Depends(get_llm_service),
    document_service: DocumentService = Depends(get_document_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    AI 自动写作 - 流式生成
    基于大纲逐章生成内容
    """
    auto_write_service = AutoWriteService(llm_service, document_service, project_service)

    async def event_generator():
        try:
            async for event in auto_write_service.generate_chapters_stream(
                project_id=request.project_id,
                document_id=request.document_id,
                outline_nodes=request.outline_nodes,
                max_tokens_per_chapter=request.max_tokens_per_chapter,
                custom_instruction=request.custom_instruction
            ):
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event, ensure_ascii=False)
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


@router.post("/generate-chapter-stream")
async def generate_single_chapter_stream(
    request: AutoWriteChapterRequest,
    llm_service: LLMService = Depends(get_llm_service),
    document_service: DocumentService = Depends(get_document_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    生成单个章节 - 流式输出
    """
    auto_write_service = AutoWriteService(llm_service, document_service, project_service)

    async def event_generator():
        try:
            async for event in auto_write_service.generate_single_chapter_stream(
                project_id=request.project_id,
                document_id=request.document_id,
                node=request.node,
                chapter_index=request.chapter_index,
                total_chapters=request.total_chapters,
                max_tokens=request.max_tokens,
                custom_instruction=request.custom_instruction,
                previous_chapter_summary=request.previous_chapter_summary
            ):
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event, ensure_ascii=False)
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


@router.post("/batch-generate-stream")
async def batch_generate_stream(
    request: AutoWriteRequest,
    llm_service: LLMService = Depends(get_llm_service),
    document_service: DocumentService = Depends(get_document_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    批量生成多个章节 - 流式输出
    """
    auto_write_service = AutoWriteService(llm_service, document_service, project_service)

    async def event_generator():
        try:
            async for event in auto_write_service.batch_generate_stream(
                project_id=request.project_id,
                document_id=request.document_id,
                outline_nodes=request.outline_nodes,
                max_tokens_per_chapter=request.max_tokens_per_chapter,
                custom_instruction=request.custom_instruction
            ):
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event, ensure_ascii=False)
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())
