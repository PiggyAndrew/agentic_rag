from __future__ import annotations

from enum import Enum


class DocumentStatus(str, Enum):
    """文档在录入、解析、分块和索引过程中的生命周期状态。"""

    uploaded = "uploaded"
    parsed = "parsed"
    chunked = "chunked"
    indexed = "indexed"
    done = "done"
    error = "error"

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def coerce(cls, value: object) -> "DocumentStatus":
        if isinstance(value, cls):
            return value
        raw = str(value or "").strip()
        if raw == "vectorized":
            return cls.indexed
        for item in cls:
            if item.value == raw:
                return item
        return cls.done


class ElementType(str, Enum):
    """Chunk 内结构化元素的类型。"""

    image = "image"
    table = "table"


class SegmentType(str, Enum):
    """Chunk 顺序片段的类型。"""

    text = "text"
    element_ref = "element_ref"


class ChunkingStrategy(str, Enum):
    """Chunk 的生成策略。"""

    fixed_size = "fixed_size"
    heading_based = "heading_based"
    page_based = "page_based"
    table_based = "table_based"
    hybrid = "hybrid"


class PdfDocumentType(str, Enum):
    """PDF 文档的业务类型，由调用方在导入前显式指定。"""

    document = "document"
    drawing = "drawing"

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def coerce(cls, value: object) -> "PdfDocumentType":
        if isinstance(value, cls):
            return value
        raw = str(value or "").strip().lower()
        for item in cls:
            if item.value == raw:
                return item
        raise ValueError(f"不支持的 PDF 文档类型: {value}")


__all__ = [
    "ChunkingStrategy",
    "DocumentStatus",
    "ElementType",
    "PdfDocumentType",
    "SegmentType",
]
