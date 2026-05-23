from __future__ import annotations

from backend.modules.kb.domain.chunk_models import DocumentChunk


def render_element_marker(ref_type: str, ref_id: str) -> str:
    """兼容旧调用，转发到 `DocumentChunk` 内聚的渲染能力。"""
    return DocumentChunk.render_element_marker(ref_type, ref_id)


def render_document_chunk_inline_text(chunk: DocumentChunk) -> str:
    """兼容旧调用，转发到 `DocumentChunk` 内聚的渲染能力。"""
    return chunk.inline_text()


def render_document_chunk_for_ai(chunk: DocumentChunk) -> str:
    """兼容旧调用，转发到 `DocumentChunk` 内聚的渲染能力。"""
    return chunk.ai_text()


__all__ = [
    "render_element_marker",
    "render_document_chunk_for_ai",
    "render_document_chunk_inline_text",
]
