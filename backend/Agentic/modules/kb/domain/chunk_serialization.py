from __future__ import annotations

from typing import Any, Optional

from .chunk_models import ChunkingInfo, DocumentChunk, ElementRefSegment, TextSegment
from .element_models import ChunkElementValue, ImageElement, TableElement
from .enums import ChunkingStrategy, ElementType

DOCUMENT_CHUNK_METADATA_KEY = "_document_chunk"
DOCUMENT_CHUNK_METADATA_VERSION = 1


def _chunking_to_dict(chunking: Optional[ChunkingInfo]) -> Optional[dict[str, Any]]:
    if chunking is None:
        return None
    return {
        "strategy": chunking.strategy.value,
        "rule": chunking.rule,
        "overlap": int(chunking.overlap),
        "generator": chunking.generator,
    }


def _chunking_from_dict(data: Any) -> Optional[ChunkingInfo]:
    if not isinstance(data, dict):
        return None
    strategy = str(data.get("strategy") or "").strip()
    if not strategy:
        return None
    return ChunkingInfo(
        strategy=ChunkingStrategy(strategy),
        rule=str(data.get("rule") or ""),
        overlap=int(data.get("overlap") or 0),
        generator=(str(data.get("generator") or "").strip() or None),
    )


def _segment_to_dict(segment: TextSegment | ElementRefSegment) -> dict[str, Any]:
    if isinstance(segment, TextSegment):
        return {
            "type": segment.type.value,
            "text": segment.text,
        }
    return {
        "type": segment.type.value,
        "ref_id": segment.ref_id,
        "ref_type": segment.ref_type.value,
    }


def _segment_from_dict(data: Any) -> Optional[TextSegment | ElementRefSegment]:
    if not isinstance(data, dict):
        return None
    segment_type = str(data.get("type") or "").strip()
    if segment_type == "text":
        return TextSegment(text=str(data.get("text") or ""))
    if segment_type == "element_ref":
        ref_type = str(data.get("ref_type") or ElementType.image.value).strip() or ElementType.image.value
        return ElementRefSegment(
            ref_id=str(data.get("ref_id") or ""),
            ref_type=ElementType(ref_type),
        )
    return None


def _element_to_dict(element: ChunkElementValue) -> dict[str, Any]:
    if isinstance(element, ImageElement):
        return {
            "id": element.id,
            "type": element.type.value,
            "uri": element.uri,
            "caption": element.caption,
            "alt_text": element.alt_text,
            "ocr_text": element.ocr_text,
        }
    return {
        "id": element.id,
        "type": element.type.value,
        "title": element.title,
        "sheet_name": element.sheet_name,
        "headers": list(element.headers),
        "rows": [list(row) for row in element.rows],
        "markdown": element.markdown,
        "summary": element.summary,
    }


def _element_from_dict(data: Any) -> Optional[ChunkElementValue]:
    if not isinstance(data, dict):
        return None
    element_type = str(data.get("type") or "").strip()
    element_id = str(data.get("id") or "").strip()
    if not element_type or not element_id:
        return None
    if element_type == ElementType.image.value:
        return ImageElement(
            id=element_id,
            uri=str(data.get("uri") or ""),
            caption=(str(data.get("caption") or "").strip() or None),
            alt_text=(str(data.get("alt_text") or "").strip() or None),
            ocr_text=(str(data.get("ocr_text") or "").strip() or None),
        )
    if element_type == ElementType.table.value:
        headers = data.get("headers")
        rows = data.get("rows")
        return TableElement(
            id=element_id,
            title=(str(data.get("title") or "").strip() or None),
            sheet_name=(str(data.get("sheet_name") or "").strip() or None),
            headers=list(headers) if isinstance(headers, list) else [],
            rows=[list(row) for row in rows] if isinstance(rows, list) else [],
            markdown=(str(data.get("markdown") or "").strip() or None),
            summary=(str(data.get("summary") or "").strip() or None),
        )
    return None


def document_chunk_to_metadata(chunk: DocumentChunk) -> dict[str, Any]:
    """把 `DocumentChunk` 编码到可落库存储的 metadata 字典中。"""

    return {
        DOCUMENT_CHUNK_METADATA_KEY: {
            "version": DOCUMENT_CHUNK_METADATA_VERSION,
            "document_id": int(chunk.document_id),
            "chunk_index": int(chunk.chunk_index),
            "segments": [_segment_to_dict(segment) for segment in chunk.segments],
            "elements": [_element_to_dict(element) for element in chunk.elements],
            "structure_path": list(chunk.structure_path),
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
            "chunking": _chunking_to_dict(chunk.chunking),
            "created_at_ms": int(chunk.created_at_ms),
            "updated_at_ms": int(chunk.updated_at_ms),
        }
    }


def metadata_to_document_chunk(metadata: Any) -> Optional[DocumentChunk]:
    """从 metadata 中恢复 `DocumentChunk`，用于获取与检索侧重建新结构。"""

    if not isinstance(metadata, dict):
        return None
    payload = metadata.get(DOCUMENT_CHUNK_METADATA_KEY)
    if not isinstance(payload, dict):
        return None

    segments: list[TextSegment | ElementRefSegment] = []
    for item in payload.get("segments") or []:
        segment = _segment_from_dict(item)
        if segment is not None:
            segments.append(segment)

    elements: list[ChunkElementValue] = []
    for item in payload.get("elements") or []:
        element = _element_from_dict(item)
        if element is not None:
            elements.append(element)

    structure_path = payload.get("structure_path")
    return DocumentChunk(
        document_id=int(payload.get("document_id") or 0),
        chunk_index=int(payload.get("chunk_index") or 0),
        segments=segments,
        elements=elements,
        structure_path=list(structure_path) if isinstance(structure_path, list) else [],
        page_start=payload.get("page_start"),
        page_end=payload.get("page_end"),
        line_start=payload.get("line_start"),
        line_end=payload.get("line_end"),
        chunking=_chunking_from_dict(payload.get("chunking")),
        created_at_ms=int(payload.get("created_at_ms") or 0),
        updated_at_ms=int(payload.get("updated_at_ms") or 0),
    )


__all__ = [
    "DOCUMENT_CHUNK_METADATA_KEY",
    "document_chunk_to_metadata",
    "metadata_to_document_chunk",
]
