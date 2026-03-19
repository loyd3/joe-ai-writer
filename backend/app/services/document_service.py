"""
文档读写服务 — 供自动写作等将块式 content 与 Markdown 字符串互转
"""
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import Document


def _blocks_to_markdown(content: Any) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    lines: List[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        bt = block.get("type", "paragraph")
        c = block.get("content", "") or ""
        if bt == "heading":
            lines.append(f"## {c}")
        elif bt == "quote":
            lines.append(f"> {c}")
        elif bt == "list":
            lines.append(f"- {c}")
        else:
            lines.append(str(c))
    return "\n\n".join(lines)


def _markdown_to_blocks(text: str) -> List[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return [{"id": uuid.uuid4().hex[:8], "type": "paragraph", "content": "", "props": {}}]
    parts = re.split(r"\n(?=## )", text)
    blocks: List[Dict[str, Any]] = []
    for part in parts:
        part = part.strip()
        if part.startswith("## "):
            blocks.append({"id": uuid.uuid4().hex[:8], "type": "heading", "content": part[3:].strip(), "props": {}})
        else:
            blocks.append({"id": uuid.uuid4().hex[:8], "type": "paragraph", "content": part, "props": {}})
    return blocks if blocks else [{"id": uuid.uuid4().hex[:8], "type": "paragraph", "content": text, "props": {}}]


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    async def get_document(
        self, project_id: int, document_id: int
    ) -> Optional[Dict[str, Any]]:
        doc = (
            self.db.query(Document)
            .filter(
                Document.id == document_id,
                Document.project_id == project_id,
            )
            .first()
        )
        if not doc:
            return None
        return {
            "id": doc.id,
            "title": doc.title,
            "content": _blocks_to_markdown(doc.content),
            "project_id": doc.project_id,
        }

    async def update_document(
        self,
        project_id: int,
        document_id: int,
        content: str,
    ) -> None:
        doc = (
            self.db.query(Document)
            .filter(
                Document.id == document_id,
                Document.project_id == project_id,
            )
            .first()
        )
        if not doc:
            raise ValueError(f"文档不存在: {document_id}")
        doc.content = _markdown_to_blocks(content)
        self.db.commit()
