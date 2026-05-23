from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from .enums import ElementType


@dataclass(frozen=True, slots=True)
class ChunkElement:
    """Chunk 内结构化元素的公共基类。"""

    id: str
    type: ElementType = field(init=False)


@dataclass(frozen=True, slots=True)
class ImageElement(ChunkElement):
    """图片元素，保存图片资源及其辅助说明信息。"""

    uri: str = ""
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    ocr_text: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", ElementType.image)


@dataclass(frozen=True, slots=True)
class TableElement(ChunkElement):
    """表格元素，保存表格标题、表头和内容摘要。"""

    title: Optional[str] = None
    sheet_name: Optional[str] = None
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    markdown: Optional[str] = None
    summary: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", ElementType.table)


# Chunk 内的结构化元素联合类型，便于上层统一处理图片和表格。
ChunkElementValue = Union[ImageElement, TableElement]


__all__ = [
    "ChunkElement",
    "ChunkElementValue",
    "ImageElement",
    "TableElement",
]
