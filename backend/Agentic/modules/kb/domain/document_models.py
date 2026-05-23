from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import DocumentStatus


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    """文档概述信息，面向摘要和快速理解场景。"""

    title: Optional[str] = None
    abstract: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DocumentDetails:
    """文档详细信息，面向解析记录和附加元信息场景。"""

    source_path: Optional[str] = None
    parser_name: Optional[str] = None
    parser_version: Optional[str] = None
    parsed_at_ms: Optional[int] = None
    page_count: Optional[int] = None
    image_count: Optional[int] = None
    table_count: Optional[int] = None
    language: Optional[str] = None
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Document:
    """知识库中的文档主实体，承载文档级稳定信息。"""

    kb_id: int
    document_id: int
    filename: str
    mime_type: str
    status: DocumentStatus
    created_at_ms: int
    updated_at_ms: int
    chunk_count: int = 0
    source_path: Optional[str] = None
    summary: Optional[DocumentSummary] = None
    details: Optional[DocumentDetails] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", DocumentStatus.coerce(self.status))


__all__ = [
    "Document",
    "DocumentDetails",
    "DocumentSummary",
]
