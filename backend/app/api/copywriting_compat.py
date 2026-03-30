"""
兼容前端旧接口的“文案写作”API（生成 + 保存到文档）

前端当前实现方式参照：
- 热点写作：`backend/app/api/hot_topics_compat.py`
- 脑洞写作：`backend/app/api/brainstorm_compat.py`
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.dependencies import get_llm_service
from app.database import get_db
from app.models.models import Document, Project
from app.services.copywriting_service import CopywritingService
from app.services.fulltext_search_service import FullTextSearchService
from app.utils.document_format import parse_formatted_text_to_blocks

router = APIRouter(prefix="/api/copywriting", tags=["文案写作(compat)"])


def _index_document_async(background_tasks: BackgroundTasks, doc_id: int, content: str, title: str, project_id: int, project_title: str = ""):
    """后台异步索引文档"""
    def do_index():
        try:
            service = FullTextSearchService()
            service.index_document(doc_id, content, title, project_id, project_title)
        except Exception as e:
            print(f"[SearchIndex] 后台索引文档 {doc_id} 失败: {e}")
    background_tasks.add_task(do_index)


def _require_project(db: Session, project_id: int, user_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not project:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project


@router.post("/generate")
async def generate_copywriting(
    payload: Dict[str, Any],
    llm=Depends(get_llm_service),
):
    """
    生成营销/广告/引流文案

    Request body（字段尽量宽松）：
    {
      "product": "产品/服务",
      "target_audience": "目标人群",
      "copy_objective": "广告/推销/引流",
      "selling_points": "核心卖点/差异化",
      "pain_points": "...(可选)",
      "evidence_cases": "...(可选)",
      "cta": "...(可选)",
      "tone": "...(可选)",
      "word_count": 900,
      "additional_requirements": "...(可选)"
    }
    """
    try:
        result = await CopywritingService.generate_copywriting(
            llm,
            product=payload.get("product", ""),
            target_audience=payload.get("target_audience", ""),
            copy_objective=payload.get("copy_objective", payload.get("objective", "广告")),
            selling_points=payload.get("selling_points", payload.get("sellingPoint", "")),
            pain_points=payload.get("pain_points", payload.get("painPoints", "")),
            evidence_cases=payload.get("evidence_cases", payload.get("cases", "")),
            cta=payload.get("cta", payload.get("call_to_action", "")),
            tone=payload.get("tone", "专业且有说服力"),
            word_count=int(payload.get("word_count", 900) or 900),
            additional_requirements=payload.get("additional_requirements", ""),
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
    将生成文案保存为文档（供编辑/发布）
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
    快速：直接生成并保存到文档
    """
    project_id = int(payload.get("project_id") or 0)
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id 不能为空")

    _require_project(db, project_id, current_user["id"])

    result = await CopywritingService.generate_copywriting(
        llm,
        product=payload.get("product", ""),
        target_audience=payload.get("target_audience", ""),
        copy_objective=payload.get("copy_objective", payload.get("objective", "广告")),
        selling_points=payload.get("selling_points", payload.get("sellingPoint", "")),
        pain_points=payload.get("pain_points", payload.get("painPoints", "")),
        evidence_cases=payload.get("evidence_cases", payload.get("cases", "")),
        cta=payload.get("cta", payload.get("call_to_action", "")),
        tone=payload.get("tone", "专业且有说服力"),
        word_count=int(payload.get("word_count", 900) or 900),
        additional_requirements=payload.get("additional_requirements", ""),
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

