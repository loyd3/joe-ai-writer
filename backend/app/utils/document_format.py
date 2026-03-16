"""
将带格式的 AI 文本解析为文档块列表。
约定：## 小节标题、### 子标题、> 引用/对话、- 列表、--- 分隔线，段落之间空一行。
"""
import re
import time
from typing import List, Dict, Any


def _gen_id(prefix: str, index: int) -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{index}"


def parse_formatted_text_to_blocks(text: str, id_prefix: str = "block") -> List[Dict[str, Any]]:
    if not text or not isinstance(text, str):
        return [{"id": _gen_id(id_prefix, 0), "type": "paragraph", "content": "", "props": {}}]

    lines = text.splitlines()
    blocks: List[Dict[str, Any]] = []
    paragraph_lines: List[str] = []
    index = 0

    def flush_paragraph() -> None:
        nonlocal index
        s = "\n".join(paragraph_lines).strip()
        if s:
            blocks.append({
                "id": _gen_id(id_prefix, index),
                "type": "paragraph",
                "content": s,
                "props": {},
            })
            index += 1
        paragraph_lines.clear()

    for line in lines:
        trimmed = line.strip()

        if not trimmed:
            flush_paragraph()
            continue

        if re.match(r"^---+$|^——+$", trimmed):
            flush_paragraph()
            blocks.append({"id": _gen_id(id_prefix, index), "type": "divider", "content": "", "props": {}})
            index += 1
            continue

        if trimmed.startswith("### "):
            flush_paragraph()
            blocks.append({
                "id": _gen_id(id_prefix, index),
                "type": "subheading",
                "content": trimmed[4:].strip(),
                "props": {},
            })
            index += 1
            continue

        if trimmed.startswith("## ") or trimmed.startswith("##"):
            flush_paragraph()
            content = trimmed[3:].strip() if trimmed.startswith("## ") else trimmed[2:].strip()
            blocks.append({
                "id": _gen_id(id_prefix, index),
                "type": "heading",
                "content": content,
                "props": {"level": 2},
            })
            index += 1
            continue

        if trimmed.startswith(">"):
            flush_paragraph()
            content = trimmed[1:].lstrip()
            blocks.append({
                "id": _gen_id(id_prefix, index),
                "type": "quote",
                "content": content,
                "props": {},
            })
            index += 1
            continue

        if trimmed.startswith("- "):
            flush_paragraph()
            blocks.append({
                "id": _gen_id(id_prefix, index),
                "type": "list",
                "content": trimmed[2:].strip(),
                "props": {},
            })
            index += 1
            continue

        paragraph_lines.append(line)

    flush_paragraph()

    if not blocks:
        blocks = [{"id": _gen_id(id_prefix, 0), "type": "paragraph", "content": text.strip(), "props": {}}]

    return blocks
