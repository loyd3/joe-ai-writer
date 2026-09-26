"""
导出 API（`/api/export`）

==============================================================================
定位
------------------------------------------------------------------------------
把文档或整个项目导出为可下载文件：Markdown / TXT / DOCX，
以及可再导入的 JSON 项目包。

装配：`main.py` → `include_router(export.router)`

==============================================================================
调用方
------------------------------------------------------------------------------
  frontend/src/components/ExportMenu.vue
  frontend/src/api/search-export.ts → exportApi.*

  GET /api/export/document/{id}/markdown|txt|docx
  GET /api/export/project/{id}/markdown|json

权限：均需登录；文档走 check_document_access，项目要求 owner。

依赖（可选）：
  python-docx → DOCX；未安装则 /docx 返回 503

==============================================================================
接口一览
------------------------------------------------------------------------------
文档级（块编辑器 Document.content → 目标格式）
  GET .../document/{document_id}/markdown  ?include_memory=true
  GET .../document/{document_id}/txt
  GET .../document/{document_id}/docx      ?include_memory=true

项目级
  GET .../project/{project_id}/markdown   ?include_memory=true
      项目设定 + 全部文档拼成一份 MD
  GET .../project/{project_id}/json       ?include_memory=true
      可导入包：{ version, project, documents, memory }
      （与前端 importApi / import_project 对接）

include_memory：是否附带 AIMemory（大纲/角色/世界观等）。
响应：StreamingResponse 或 FileResponse，中文文件名靠
content_disposition_attachment（RFC 5987）。
==============================================================================
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import json
import tempfile
import os
from datetime import datetime
from urllib.parse import quote

from app.database import get_db
from app.api.auth import get_current_user
from app.api.projects import check_document_access
from app.models.models import Document, Project, AIMemory

# 导出库（可选依赖：缺失时对应格式接口返回 503）
try:
    from docx import Document as DocxDocument
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

router = APIRouter(prefix="/api/export", tags=["export"])


def content_disposition_attachment(filename: str) -> str:
    """生成支持中文文件名的 Content-Disposition 头（RFC 5987）。"""
    ascii_fallback = "export" + (filename[filename.rfind("."):] if "." in filename else "")
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


# ---------- 文档导出 ----------

@router.get("/document/{document_id}/markdown")
async def export_markdown(
    document_id: int,
    include_memory: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出单篇文档为 Markdown（可选附带项目设定）。需登录且有文档权限。"""
    document = check_document_access(db, document_id, current_user["id"])
    project = db.query(Project).filter(Project.id == document.project_id).first()

    md_content = generate_markdown(db, document, project, include_memory)

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
    """导出单篇文档为纯文本（仅正文块，不含设定）。"""
    document = check_document_access(db, document_id, current_user["id"])

    text_content = generate_plain_text(document)

    filename = f"{document.title}_{datetime.now().strftime('%Y%m%d')}.txt"
    return StreamingResponse(
        io.StringIO(text_content),
        media_type="text/plain",
        headers={"Content-Disposition": content_disposition_attachment(filename)}
    )


# ---------- 项目导出 ----------

@router.get("/project/{project_id}/markdown")
async def export_project_markdown(
    project_id: int,
    include_memory: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出整个项目为一份 Markdown（设定 + 全部文档）。仅项目 owner。"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    md_content = generate_project_markdown(db, project, include_memory)

    filename = f"{project.title}_{datetime.now().strftime('%Y%m%d')}.md"
    return StreamingResponse(
        io.StringIO(md_content),
        media_type="text/markdown",
        headers={"Content-Disposition": content_disposition_attachment(filename)}
    )


def build_project_export_payload(db: Session, project: Project, include_memory: bool = True) -> dict:
    """
    构建可再导入的项目 JSON 包。
    documents 用 parent_index（列表下标）表达树，避免导出后 ID 失效。
    """
    documents = (
        db.query(Document)
        .filter(Document.project_id == project.id)
        .order_by(Document.order_index, Document.id)
        .all()
    )
    id_to_index = {d.id: i for i, d in enumerate(documents)}
    doc_list = []
    for d in documents:
        doc_list.append({
            "title": d.title or "",
            "content": d.content if d.content is not None else [],
            "order_index": d.order_index or 0,
            "parent_index": id_to_index.get(d.parent_id) if d.parent_id else None,
        })
    payload = {
        "version": 1,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "project": {
            "title": project.title or "未命名项目",
            "description": project.description or "",
        },
        "documents": doc_list,
    }
    if include_memory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project.id).first()
        if memory:
            payload["memory"] = {
                "outline": memory.outline if memory.outline is not None else [],
                "storyline": memory.storyline or "",
                "characters": memory.characters if memory.characters is not None else [],
                "world_building": memory.world_building if memory.world_building is not None else {},
                "writing_style": memory.writing_style or "",
                "key_points": memory.key_points if memory.key_points is not None else [],
                "notes": memory.notes or "",
            }
        else:
            payload["memory"] = {
                "outline": [], "storyline": "", "characters": [], "world_building": {},
                "writing_style": "", "key_points": [], "notes": "",
            }
    else:
        payload["memory"] = {
            "outline": [], "storyline": "", "characters": [], "world_building": {},
            "writing_style": "", "key_points": [], "notes": "",
        }
    return payload


@router.get("/project/{project_id}/json")
async def export_project_json(
    project_id: int,
    include_memory: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出项目 JSON 包，供「导入项目」还原为新项目。仅 owner。"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user["id"]
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    payload = build_project_export_payload(db, project, include_memory)
    filename = f"{project.title or 'project'}_{datetime.now().strftime('%Y%m%d')}.json"
    return StreamingResponse(
        io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": content_disposition_attachment(filename)},
    )


# ---------- 内容生成辅助（块 → 文本） ----------

def generate_markdown(db: Session, document: Document, project: Project, include_memory: bool) -> str:
    """单文档 → Markdown：标题/元信息 + 可选设定 + 正文块。"""
    lines = []

    lines.append(f"# {document.title}")
    lines.append("")
    lines.append(f"> 所属项目: {project.title}")
    lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if include_memory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project.id).first()
        if memory and has_memory_content(memory):
            lines.append("## 📚 项目设定")
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
    """单文档 → 纯文本：标题 + 各块 content 拼接。"""
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
    """整项目 → Markdown：设定 + 按 order_index 的全部文档。"""
    lines = []

    lines.append(f"# {project.title}")
    lines.append("")
    if project.description:
        lines.append(f"> {project.description}")
    lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("=" * 50)
    lines.append("")

    if include_memory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project.id).first()
        if memory and has_memory_content(memory):
            lines.append("## 📚 项目设定")
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
    """检查 AIMemory 是否有可导出的非空设定。"""
    return bool(
        memory.outline or
        memory.storyline or
        memory.characters or
        memory.world_building or
        memory.writing_style or
        memory.key_points
    )


# ---------- DOCX（需可选依赖 python-docx） ----------

@router.get("/document/{document_id}/docx")
async def export_docx(
    document_id: int,
    include_memory: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出文档为 Word DOCX（python-docx）。依赖缺失 → 503。"""
    if not DOCX_AVAILABLE:
        raise HTTPException(status_code=503, detail="Word 导出功能不可用，请安装 python-docx")

    document = check_document_access(db, document_id, current_user["id"])
    project = db.query(Project).filter(Project.id == document.project_id).first()

    doc = DocxDocument()

    title = doc.add_heading(document.title, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER if hasattr(WD_ALIGN_PARAGRAPH, 'CENTER') else 1

    meta = doc.add_paragraph()
    meta.add_run(f"所属项目: {project.title}\n").italic = True
    meta.add_run(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").italic = True

    doc.add_paragraph()

    if include_memory:
        memory = db.query(AIMemory).filter(AIMemory.project_id == project.id).first()
        if memory and has_memory_content(memory):
            doc.add_heading("项目设定", level=1)

            if memory.outline:
                doc.add_heading("大纲", level=2)
                for item in memory.outline:
                    doc.add_paragraph(item.get("title", ""), style='List Bullet')

            if memory.storyline:
                doc.add_heading("故事线", level=2)
                doc.add_paragraph(memory.storyline)

            if memory.characters:
                doc.add_heading("角色设定", level=2)
                for char in memory.characters:
                    p = doc.add_paragraph()
                    p.add_run(char.get("name", "")).bold = True
                    p.add_run(f": {char.get('description', '')}")

            doc.add_page_break()

    doc.add_heading("正文", level=1)

    for block in (document.content or []):
        block_type = block.get("type", "paragraph")
        content = block.get("content", "")

        if not content.strip():
            continue

        if block_type == "heading":
            doc.add_heading(content, level=2)
        elif block_type == "subheading":
            doc.add_heading(content, level=3)
        elif block_type == "quote":
            p = doc.add_paragraph(content)
            p.style = 'Intense Quote'
        elif block_type == "list":
            doc.add_paragraph(content, style='List Bullet')
        elif block_type == "code":
            p = doc.add_paragraph(content)
            p.style = 'No Spacing'
            p.runs[0].font.name = 'Courier New'
            p.runs[0].font.size = Pt(10)
        elif block_type == "divider":
            doc.add_paragraph("* * *")
        else:
            doc.add_paragraph(content)

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc.save(tmp_path)
        filename = f"{document.title}_{datetime.now().strftime('%Y%m%d')}.docx"

        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename,
            headers={"Content-Disposition": content_disposition_attachment(filename)}
        )
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Word 导出失败: {str(e)}")
