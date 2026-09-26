"""
用户级文风智能体 API（`/api/style-agents`）

系统层级文风库：跨项目复用；可从范文提炼后保存使用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.schemas.schemas import (
    StyleAgentCreate,
    StyleAgentFromPreset,
    StyleAgentResponse,
    StyleAgentUpdate,
)
from app.services.style_agent_service import StyleAgentService

router = APIRouter(prefix="/api", tags=["文风智能体"])


class StyleExtractSource(BaseModel):
    name: str = Field("范文", description="文件名或标签")
    text: str = Field(..., min_length=1, description="该来源正文")


class StyleExtractRequest(BaseModel):
    text: Optional[str] = Field(None, description="粘贴的范文原文")
    texts: Optional[List[str]] = Field(None, description="多段纯文本")
    sources: Optional[List[StyleExtractSource]] = Field(
        None, description="多文件来源 [{name, text}]"
    )
    name: Optional[str] = Field(None, description="可选文风名")
    save: bool = Field(False, description="是否直接保存为智能体")
    set_default: bool = Field(False, description="保存时是否设为默认")


class StyleExtractResponse(BaseModel):
    name: str
    description: str = ""
    config: Dict[str, Any] = {}
    compiled_preview: str = ""
    source_chunks: int = 1
    source_files: int = 1
    source_names: List[str] = []
    agent: Optional[StyleAgentResponse] = None


@router.get("/style-agent-presets")
def list_style_presets(current_user: dict = Depends(get_current_user)):
    """内置文风预设列表。"""
    return StyleAgentService.list_presets()


@router.get("/style-agents", response_model=List[StyleAgentResponse])
def list_style_agents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """当前用户的文风库。"""
    agents = StyleAgentService.list_agents(db, current_user["id"])
    return [StyleAgentService.to_dict(a) for a in agents]


@router.post("/style-agents", response_model=StyleAgentResponse)
def create_style_agent(
    body: StyleAgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    agent = StyleAgentService.create_agent(
        db,
        user_id=current_user["id"],
        name=body.name,
        description=body.description or "",
        config=body.config,
        preset_key=body.preset_key,
        is_default=body.is_default,
        source="manual",
    )
    return StyleAgentService.to_dict(agent)


@router.post("/style-agents/from-preset", response_model=StyleAgentResponse)
def create_style_agent_from_preset(
    body: StyleAgentFromPreset,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        agent = StyleAgentService.create_from_preset(
            db, current_user["id"], body.preset_key, set_default=body.set_default
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StyleAgentService.to_dict(agent)


@router.post("/style-agents/extract-from-text", response_model=StyleExtractResponse)
async def extract_style_from_text(
    body: StyleExtractRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    从范文提炼文风（支持多文件/多段；长文分段采样 + LLM）。
    save=true 时写入用户文风库并可设为默认。
    """
    sources = []
    if body.sources:
        sources.extend([(s.name or "范文", s.text) for s in body.sources])
    if body.texts:
        for i, t in enumerate(body.texts, 1):
            if (t or "").strip():
                sources.append((f"文本{i}", t))

    if not sources and not (body.text or "").strip():
        raise HTTPException(status_code=400, detail="请提供 text、texts 或 sources")

    try:
        extracted = await StyleAgentService.extract_style_from_text(
            text=body.text or "",
            preferred_name=body.name,
            sources=sources or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提炼失败: {e}")

    agent_dict = None
    if body.save:
        agent = StyleAgentService.create_agent(
            db,
            user_id=current_user["id"],
            name=extracted["name"],
            description=extracted.get("description") or "",
            config=extracted.get("config"),
            is_default=body.set_default,
            source="extract",
        )
        agent_dict = StyleAgentService.to_dict(agent)

    return {
        "name": extracted["name"],
        "description": extracted.get("description") or "",
        "config": extracted.get("config") or {},
        "compiled_preview": extracted.get("compiled_preview") or "",
        "source_chunks": extracted.get("source_chunks") or 1,
        "source_files": extracted.get("source_files") or 1,
        "source_names": extracted.get("source_names") or [],
        "agent": agent_dict,
    }


@router.put("/style-agents/{agent_id}", response_model=StyleAgentResponse)
def update_style_agent(
    agent_id: int,
    body: StyleAgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        agent = StyleAgentService.update_agent(
            db,
            current_user["id"],
            agent_id,
            name=body.name,
            description=body.description,
            config=body.config,
            is_default=body.is_default,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StyleAgentService.to_dict(agent)


@router.post("/style-agents/{agent_id}/set-default", response_model=StyleAgentResponse)
def set_default_style_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        agent = StyleAgentService.set_default(db, current_user["id"], agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StyleAgentService.to_dict(agent)


@router.delete("/style-agents/{agent_id}")
def delete_style_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        StyleAgentService.delete_agent(db, current_user["id"], agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}
