from __future__ import annotations

import re


def format_kb_id(kb_id: int) -> str:
    return f"kb-{int(kb_id)}"


def parse_kb_id(kb_id: str | int) -> int:
    if isinstance(kb_id, int):
        return kb_id
    m = re.match(r"^kb-(\d+)$", str(kb_id))
    if m:
        return int(m.group(1))
    return int(kb_id)


def format_document_id(document_id: int) -> str:
    """格式化文档 ID，统一对外使用 document 语义。"""
    return f"d-{int(document_id)}"


def parse_document_id(document_id: str | int) -> int:
    """解析文档 ID，兼容历史 `f-*` 与新的 `d-*` 格式。"""
    if isinstance(document_id, int):
        return document_id
    raw = str(document_id)
    m = re.match(r"^[df]-(\d+)$", raw)
    if m:
        return int(m.group(1))
    return int(raw)
