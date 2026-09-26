"""
AI 自动写作 API（按大纲逐章生成并写入文档）

==============================================================================
定位
------------------------------------------------------------------------------
基于项目大纲节点，用 LLM 逐章（或单章）生成正文，并通过 DocumentService
写回指定文档。流式协议用 sse-starlette 的 EventSourceResponse（带 event 名）。

装配：`main.py` → `include_router(auto_write.router)`
前缀：`/auto-write`（注意：无 `/api` 前缀，完整路径如 `/auto-write/generate-stream`）
实现：`AutoWriteService`（依赖 LLMService / DocumentService / ProjectService）

==============================================================================
与 `/api/ai/batch-generate/stream` 的关系
------------------------------------------------------------------------------
功能相近（大纲 → 多章正文 → 目标文档），但是两套实现：

  本文件 AutoWriteService
    - 路由前缀 /auto-write
    - SSE：{ event: <type>, data: JSON }
    - 服务内自行拼 prompt、写文档

  ai.py → AIWritingService.batch_generate
    - 路由 /api/ai/batch-generate/stream
    - SSE：data: <JSON 行>，走项目设定/文风智能体注入与去机感等统一写作链路

当前前端 `AIAutoWrite.vue` / 大纲「创建文章」主要走的是
  `aiApi.batchGenerateStream` → `/api/ai/batch-generate/stream`。
本路由仍保留，可供旧客户端或直接调 AutoWriteService 的场景使用。

==============================================================================
接口一览
------------------------------------------------------------------------------
  POST /auto-write/generate-stream
      多章连续生成（generate_chapters_stream）

  POST /auto-write/generate-chapter-stream
      单章生成（可带 previous_chapter_summary 保持连贯）

  POST /auto-write/batch-generate-stream
      批量多章（batch_generate_stream；与 generate-stream 入口不同、服务方法不同）

SSE 事件名通常来自 service 返回的 type，如：
  start | chapter_start | content | complete | chapter_complete | error | done
（以 AutoWriteService 实际 yield 为准）

==============================================================================
请求体
------------------------------------------------------------------------------
AutoWriteRequest（多章 / 批量）:
  project_id, document_id, outline_nodes[]
  max_tokens_per_chapter (500–32000, 默认 8000)
  continue_on_complete（schema 有字段；部分 service 路径可能未使用）
  custom_instruction?

AutoWriteChapterRequest（单章）:
  project_id, document_id, node, chapter_index, total_chapters
  max_tokens, custom_instruction?, previous_chapter_summary?

鉴权：本文件未直接 Depends(get_current_user)；若全局无鉴权中间件，
调用方需自行保证仅所有者可写对应项目文档（与 /api/ai 路径不同）。
==============================================================================
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
    """多章 / 批量自动写作请求。"""
    project_id: int = Field(..., description="项目ID")
    document_id: int = Field(..., description="目标文档ID（生成内容写入此文档）")
    outline_nodes: list = Field(..., description="大纲节点列表，项含 title / description 等")
    max_tokens_per_chapter: int = Field(default=8000, ge=500, le=32000, description="每章最大token数")
    continue_on_complete: bool = Field(default=True, description="一章完成后是否继续下一章（schema 字段）")
    custom_instruction: Optional[str] = Field(default=None, description="全局额外写作要求")


class AutoWriteChapterRequest(BaseModel):
    """单章流式生成请求。"""
    project_id: int = Field(..., description="项目ID")
    document_id: int = Field(..., description="目标文档ID")
    node: dict = Field(..., description="当前大纲节点 {title, description, ...}")
    chapter_index: int = Field(..., description="章节索引（从 0 起）")
    total_chapters: int = Field(..., description="总章节数（进度展示）")
    max_tokens: int = Field(default=8000, ge=500, le=32000)
    custom_instruction: Optional[str] = Field(default=None)
    previous_chapter_summary: Optional[str] = Field(
        default=None, description="前一章摘要，用于保持连贯性"
    )


@router.post("/generate-stream")
async def auto_write_stream(
    request: AutoWriteRequest,
    llm_service: LLMService = Depends(get_llm_service),
    document_service: DocumentService = Depends(get_document_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    按 outline_nodes 顺序逐章流式生成，并写入 document_id。

    SSE：每条为 { "event": <type>, "data": "<json>" }，
    data 为 AutoWriteService.generate_chapters_stream 产出的事件字典。
    异常时 event=error，data={"error": "..."}。
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
    只生成一章（流式），适合前端自行控速、章间插入摘要再开下一章。

    可传 previous_chapter_summary 降低章间脱节；
    实现见 AutoWriteService.generate_single_chapter_stream。
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
    批量流式生成多章（请求体同 AutoWriteRequest）。

    走 AutoWriteService.batch_generate_stream，与 /generate-stream
    的 generate_chapters_stream 是不同服务方法（事件形状可能略有差异）。
    若前端已统一用 /api/ai/batch-generate/stream，优先走那边以共享设定/文风注入。
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
