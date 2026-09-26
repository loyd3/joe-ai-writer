"""
文案写作兼容 API（`/api/copywriting`）

==============================================================================
定位
------------------------------------------------------------------------------
给前端页 `CopywritingWriter.vue` 用的营销/广告/引流文案链路：
  填产品信息 → 生成文案（含可编辑 blocks）→ 保存为项目文档，或一键生成并入库。

文件名带 compat：对齐前端约定的路径与响应形状，写法参照
`hot_topics_compat` / `brainstorm_compat`。

装配：`main.py` → `include_router(copywriting_compat.router)`

==============================================================================
调用方
------------------------------------------------------------------------------
  frontend/src/views/CopywritingWriter.vue
    POST /api/copywriting/generate         仅生成（可不登录）
    POST /api/copywriting/create-document  把已有文案存成 Document（需登录）
    POST /api/copywriting/quick-write      生成并直接落库（需登录）

依赖：
  CopywritingService.generate_copywriting（LLM 出 title/content/keywords）
  parse_formatted_text_to_blocks（Markdown/格式化文本 → 编辑器块）
  Document / Project（落库与权限）

==============================================================================
接口一览
------------------------------------------------------------------------------
POST /generate
  Body：product, target_audience, copy_objective, selling_points,
        pain_points?, evidence_cases?, cta?, tone?, word_count?,
        additional_requirements?
  （兼容别名：objective、sellingPoint、painPoints、cases、call_to_action）
  返回：{ success, data: { title, content, keywords, ..., blocks } }
  说明：生成后立刻解析 blocks，便于未保存时 PublishDialog 按平台排版。

POST /create-document  （需登录）
  Body：project_id, title, content
  校验项目归属；content → blocks → 新建 Document
  返回：{ document: { id, title, project_id } }

POST /quick-write  （需登录）
  Body：project_id + 与 /generate 相同的文案字段
  流程：generate → 建 Document → 返回 document + title/content/keywords/blocks

权限：create-document / quick-write 均要求当前用户为 project.owner。
==============================================================================
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_current_user_optional
from app.services.style_agent_service import StyleAgentService
from app.api.dependencies import get_llm_service
from app.database import get_db
from app.models.models import Document, Project
from app.services.copywriting_service import CopywritingService
from app.services.fulltext_search_service import FullTextSearchService
from app.utils.document_format import parse_formatted_text_to_blocks

router = APIRouter(prefix="/api/copywriting", tags=["文案写作(compat)"])


def _index_document_async(background_tasks: BackgroundTasks, doc_id: int, content, title: str, project_id: int, project_title: str = ""):
    """后台异步写入全文检索索引（本文件落库路径暂未挂用，保留便于后续接上）。"""
    def do_index():
        try:
            service = FullTextSearchService()
            service.index_document(
                document_id=doc_id,
                document_title=title,
                project_id=project_id,
                content=content,
                metadata={"project_title": project_title},
            )
        except Exception as e:
            print(f"[SearchIndex] 后台索引文档 {doc_id} 失败: {e}")
    background_tasks.add_task(do_index)


def _require_project(db: Session, project_id: int, user_id: int) -> Project:
    """确认项目存在且属于当前用户，否则 403。"""
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project


@router.post("/generate")
async def generate_copywriting(
    payload: Dict[str, Any],
    llm=Depends(get_llm_service),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    仅生成营销/广告/引流文案（不落库；可不登录）。

    Body（字段宽松，见模块头「接口一览」）；可含 style_agent_id。
    成功：{ success: true, data: CopywritingService 结果 + blocks }。
    失败：500。
    """
    try:
        tone = payload.get("tone", "专业且有说服力")
        style_section = StyleAgentService.prompt_style_section(
            db,
            current_user["id"] if current_user else None,
            payload.get("style_agent_id"),
            fallback_label=tone,
        )
        extra = (payload.get("additional_requirements") or "").strip()
        if style_section:
            extra = f"{extra}\n{style_section}".strip()

        result = await CopywritingService.generate_copywriting(
            llm,
            product=payload.get("product", ""),
            target_audience=payload.get("target_audience", ""),
            copy_objective=payload.get("copy_objective", payload.get("objective", "广告")),
            selling_points=payload.get("selling_points", payload.get("sellingPoint", "")),
            pain_points=payload.get("pain_points", payload.get("painPoints", "")),
            evidence_cases=payload.get("evidence_cases", payload.get("cases", "")),
            cta=payload.get("cta", payload.get("call_to_action", "")),
            tone=tone,
            word_count=int(payload.get("word_count", 900) or 900),
            additional_requirements=extra,
        )

        # 生成后直接解析为文档块：保证未保存时 PublishDialog 也能正确按平台排版
        content = str(result.get("content") or "")
        blocks = parse_formatted_text_to_blocks(content, "copywriting")
        return {"success": True, "data": {**result, "blocks": blocks}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/create-document")
async def create_document_from_copywriting(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    将已生成文案保存为项目文档（需登录），供编辑器打开与发布。

    Body：project_id, title, content（均必填）。
    content 经 parse_formatted_text_to_blocks(..., "copy") 写入 Document.content。
    返回：{ document: { id, title, project_id } }。
    """
    project_id = int(payload.get("project_id") or 0)
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()

    if not project_id or not title or not content:
        raise HTTPException(status_code=400, detail="project_id、title、content 均不能为空")

    _require_project(db, project_id, current_user["id"])

    blocks = parse_formatted_text_to_blocks(content, "copy")

    doc = Document(
        title=title,
        project_id=project_id,
        content=blocks,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"document": {"id": doc.id, "title": doc.title, "project_id": doc.project_id}}


@router.post("/quick-write")
async def quick_write_and_save(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    llm=Depends(get_llm_service),
):
    """
    一键：按文案字段生成并直接保存到指定项目（需登录）。

    Body：project_id（必填）+ 与 /generate 相同的生成字段。
    返回：document 元数据 + title/content/keywords/blocks，前端可立刻跳转编辑。
    """
    project_id = int(payload.get("project_id") or 0)
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id 不能为空")

    _require_project(db, project_id, current_user["id"])

    tone = payload.get("tone", "专业且有说服力")
    style_section = StyleAgentService.prompt_style_section(
        db,
        current_user["id"],
        payload.get("style_agent_id"),
        fallback_label=tone,
    )
    extra = (payload.get("additional_requirements") or "").strip()
    if style_section:
        extra = f"{extra}\n{style_section}".strip()

    result = await CopywritingService.generate_copywriting(
        llm,
        product=payload.get("product", ""),
        target_audience=payload.get("target_audience", ""),
        copy_objective=payload.get("copy_objective", payload.get("objective", "广告")),
        selling_points=payload.get("selling_points", payload.get("sellingPoint", "")),
        pain_points=payload.get("pain_points", payload.get("painPoints", "")),
        evidence_cases=payload.get("evidence_cases", payload.get("cases", "")),
        cta=payload.get("cta", payload.get("call_to_action", "")),
        tone=tone,
        word_count=int(payload.get("word_count", 900) or 900),
        additional_requirements=extra,
    )

    title = (result.get("title") or "").strip() or "营销文案"
    content = (result.get("content") or "").strip()
    blocks = parse_formatted_text_to_blocks(content, "copywriting")

    doc = Document(
        title=title,
        project_id=project_id,
        content=blocks,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document": {"id": doc.id, "title": doc.title, "project_id": doc.project_id},
        "title": doc.title,
        "content": content,
        "keywords": result.get("keywords") or [],
        "blocks": blocks,
    }
