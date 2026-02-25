from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import json
from datetime import datetime
from urllib.parse import quote

from app.database import get_db
from app.api.auth import get_current_user
from app.api.projects import check_document_access
from app.models.models import Document, Project, AIMemory

router = APIRouter(prefix="/api/export", tags=["export"])


def content_disposition_attachment(filename: str) -> str:
    """生成支持中文文件名的 Content-Disposition 头（RFC 5987）。"""
    ascii_fallback = "export" + (filename[filename.rfind("."):] if "." in filename else "")
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@router.get("/document/{document_id}/markdown")
async def export_markdown(
    document_id: int,
    include_memory: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出文档为 Markdown 格式"""
    document = check_document_access(db, document_id, current_user["id"])
    project = db.query(Project).filter(Project.id == document.project_id).first()
    
    # 生成 Markdown 内容
    md_content = generate_markdown(db, document, project, include_memory)
    
    # 创建文件流
    filename = f"{document.title}_{datetime.now().strftime('%Y%m%d')}.md"
    return StreamingResponse(
        io.StringIO(md_content),
        media_type="text/markdown",
        headers={"Content-Disposition": content_disposition_attachment(filename)}
    )


@router.get("/document/{document_id}/txt")
async def export_txt(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出文档为纯文本格式"""
    document = check_document_access(db, document_id, current_user["id"])
    
    # 生成纯文本内容
    text_content = generate_plain_text(document)
    
    filename = f"{document.title}_{datetime.now().strftime('%Y%m%d')}.txt"
    return StreamingResponse(
        io.StringIO(text_content),
        media_type="text/plain",
        headers={"Content-Disposition": content_disposition_attachment(filename)}
    )


@router.get("/project/{project_id}/markdown")
async def export_project_markdown(
    project_id: int,
    include_memory: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出整个项目为 Markdown 格式"""
    # 检查权限
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 生成项目 Markdown
    md_content = generate_project_markdown(db, project, include_memory)
    
    filename = f"{project.title}_{datetime.now().strftime('%Y%m%d')}.md"
    return StreamingResponse(
        io.StringIO(md_content),
        media_type="text/markdown",
        headers={"Content-Disposition": content_disposition_attachment(filename)}
    )


def generate_markdown(db: Session, document: Document, project: Project, include_memory: bool) -> str:
    """生成 Markdown 格式内容"""
    lines = []
    
    # 文档标题
    lines.append(f"# {document.title}")
    lines.append("")
    lines.append(f"> 所属项目: {project.title}")
    lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 添加 AI 记忆
    if include_memory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project.id).first()
        if memory and has_memory_content(memory):
            lines.append("## 📚 项目记忆")
            lines.append("")
            
            if memory.outline:
                lines.append("### 大纲")
                for item in memory.outline:
                    lines.append(f"- {item.get('title', '')}")
                lines.append("")
            
            if memory.storyline:
                lines.append("### 故事线")
                lines.append(memory.storyline)
                lines.append("")
            
            if memory.characters:
                lines.append("### 角色设定")
                for char in memory.characters:
                    lines.append(f"**{char.get('name', '')}**: {char.get('description', '')}")
                    if char.get('personality'):
                        lines.append(f"- 性格: {char['personality']}")
                    if char.get('goals'):
                        lines.append(f"- 目标: {char['goals']}")
                    lines.append("")
            
            if memory.writing_style:
                lines.append("### 写作风格")
                lines.append(memory.writing_style)
                lines.append("")
            
            lines.append("---")
            lines.append("")
    
    # 文档内容
    lines.append("## 正文")
    lines.append("")
    
    for block in (document.content or []):
        block_type = block.get("type", "paragraph")
        content = block.get("content", "")
        
        if block_type == "heading":
            lines.append(f"## {content}")
        elif block_type == "quote":
            lines.append(f"> {content}")
        elif block_type == "list":
            lines.append(f"- {content}")
        else:
            lines.append(content)
        
        lines.append("")
    
    return "\n".join(lines)

def generate_plain_text(document: Document) -> str:
    """生成纯文本格式内容"""
    lines = []
    lines.append(document.title)
    lines.append("=" * len(document.title))
    lines.append("")
    
    for block in (document.content or []):
        content = block.get("content", "")
        if content.strip():
            lines.append(content)
            lines.append("")
    
    return "\n".join(lines)

def generate_project_markdown(db: Session, project: Project, include_memory: bool) -> str:
    """生成项目 Markdown"""
    lines = []
    
    # 项目标题
    lines.append(f"# {project.title}")
    lines.append("")
    if project.description:
        lines.append(f"> {project.description}")
    lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("=" * 50)
    lines.append("")
    
    # 添加 AI 记忆
    if include_memory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project.id).first()
        if memory and has_memory_content(memory):
            lines.append("## 📚 项目记忆")
            lines.append("")
            
            if memory.outline:
                lines.append("### 大纲")
                for i, item in enumerate(memory.outline, 1):
                    lines.append(f"{i}. {item.get('title', '')}")
                lines.append("")
            
            if memory.storyline:
                lines.append("### 故事线")
                lines.append(memory.storyline)
                lines.append("")
            
            if memory.characters:
                lines.append("### 角色设定")
                for char in memory.characters:
                    lines.append(f"**{char.get('name', '')}**")
                    lines.append(f"- 描述: {char.get('description', '')}")
                    if char.get('personality'):
                        lines.append(f"- 性格: {char['personality']}")
                    if char.get('background'):
                        lines.append(f"- 背景: {char['background']}")
                    if char.get('goals'):
                        lines.append(f"- 目标: {char['goals']}")
                    lines.append("")
            
            if memory.world_building:
                lines.append("### 世界观")
                for key, value in memory.world_building.items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            if memory.writing_style:
                lines.append("### 写作风格")
                lines.append(memory.writing_style)
                lines.append("")
            
            if memory.key_points:
                lines.append("### 关键情节点")
                for point in memory.key_points:
                    lines.append(f"- {point}")
                lines.append("")
            
            lines.append("=" * 50)
            lines.append("")
    
    # 添加所有文档
    documents = db.query(Document).filter(
        Document.project_id == project.id
    ).order_by(Document.order_index).all()
    
    if documents:
        lines.append(f"## 📄 文档列表 ({len(documents)} 篇)")
        lines.append("")
        
        for i, doc in enumerate(documents, 1):
            lines.append(f"### {i}. {doc.title}")
            lines.append("")
            
            for block in (doc.content or []):
                block_type = block.get("type", "paragraph")
                content = block.get("content", "")
                
                if block_type == "heading":
                    lines.append(f"**{content}**")
                elif block_type == "quote":
                    lines.append(f"> {content}")
                elif block_type == "list":
                    lines.append(f"- {content}")
                else:
                    lines.append(content)
                
                lines.append("")
            
            lines.append("---")
            lines.append("")
    
    return "\n".join(lines)

def has_memory_content(memory: AIMemory) -> bool:
    """检查是否有记忆内容"""
    return bool(
        memory.outline or
        memory.storyline or
        memory.characters or
        memory.world_building or
        memory.writing_style or
        memory.key_points
    )
