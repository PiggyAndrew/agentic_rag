from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from .element_models import ChunkElementValue, ImageElement, TableElement
from .enums import ChunkingStrategy, ElementType, SegmentType


@dataclass(frozen=True, slots=True)
class ChunkingInfo:
    """描述一个 chunk 是按什么规则生成出来的。"""

    strategy: ChunkingStrategy
    rule: str
    overlap: int = 0
    generator: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TextSegment:
    """Chunk 中按顺序出现的一段纯文本。"""

    type: SegmentType = SegmentType.text
    text: str = ""


@dataclass(frozen=True, slots=True)
class ElementRefSegment:
    """Chunk 中对结构化元素的顺序引用，不重复存元素内容。"""

    type: SegmentType = SegmentType.element_ref
    ref_id: str = ""
    ref_type: ElementType = ElementType.image


# Chunk 内部片段的联合类型，用于表达文本与元素引用的顺序。
ChunkSegmentValue = Union[TextSegment, ElementRefSegment]


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """文档中的一个上下文单元，按 segments 和 elements 共同表达内容。"""

    document_id: int
    chunk_index: int
    segments: list[ChunkSegmentValue] = field(default_factory=list)
    elements: list[ChunkElementValue] = field(default_factory=list)
    structure_path: list[str] = field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    chunking: Optional[ChunkingInfo] = None
    created_at_ms: int = 0
    updated_at_ms: int = 0

    @staticmethod
    def render_element_marker(ref_type: str, ref_id: str) -> str:
        return f"[[{ref_type.upper()}:{ref_id}]]"

    def inline_text(self) -> str:
        pieces: list[str] = []
        for segment in self.segments:
            if isinstance(segment, TextSegment):
                pieces.append(segment.text)
                continue
            if isinstance(segment, ElementRefSegment):
                pieces.append(self.render_element_marker(segment.ref_type.value, segment.ref_id))
        return "".join(pieces).strip()

    def ai_text(self) -> str:
        elements_by_id = {element.id: element for element in self.elements}
        parts: list[str] = []

        if self.structure_path:
            parts.append(f"[STRUCTURE] {' > '.join(self.structure_path)}")

        location: list[str] = []
        if self.page_start is not None and self.page_end is not None:
            if self.page_start == self.page_end:
                location.append(f"page={self.page_start}")
            else:
                location.append(f"pages={self.page_start}-{self.page_end}")
        if self.line_start is not None and self.line_end is not None:
            if self.line_start == self.line_end:
                location.append(f"line={self.line_start}")
            else:
                location.append(f"lines={self.line_start}-{self.line_end}")
        if location:
            parts.append(f"[LOCATION] {' '.join(location)}")

        if self.chunking is not None:
            parts.append(
                "[CHUNKING] "
                f"strategy={self.chunking.strategy.value} "
                f"rule={self.chunking.rule}"
            )

        for segment in self.segments:
            if isinstance(segment, TextSegment):
                text = segment.text.strip()
                if text:
                    parts.append(text)
                continue

            if isinstance(segment, ElementRefSegment):
                token = self.render_element_marker(segment.ref_type.value, segment.ref_id)
                element = elements_by_id.get(segment.ref_id)
                if element is None:
                    parts.append(token)
                    continue
                parts.append(f"{token}\n{self._render_element_block(element)}")

        return "\n\n".join(part for part in parts if part.strip()).strip()

    @staticmethod
    def _render_element_block(element: ChunkElementValue) -> str:
        if isinstance(element, ImageElement):
            lines = [f"[IMAGE:{element.id}]"]
            if element.caption:
                lines.append(f"caption: {element.caption}")
            if element.alt_text:
                lines.append(f"alt_text: {element.alt_text}")
            if element.ocr_text:
                lines.append(f"ocr_text: {element.ocr_text}")
            lines.append(f"uri: {element.uri}")
            return "\n".join(lines).strip()

        if isinstance(element, TableElement):
            lines = [f"[TABLE:{element.id}]"]
            if element.title:
                lines.append(f"title: {element.title}")
            if element.sheet_name:
                lines.append(f"sheet_name: {element.sheet_name}")
            if element.summary:
                lines.append(f"summary: {element.summary}")
            if element.markdown:
                lines.append("content:")
                lines.append(element.markdown)
            return "\n".join(lines).strip()

        return f"[ELEMENT:{element.id}]"


__all__ = [
    "ChunkingInfo",
    "ChunkSegmentValue",
    "DocumentChunk",
    "ElementRefSegment",
    "TextSegment",
]
