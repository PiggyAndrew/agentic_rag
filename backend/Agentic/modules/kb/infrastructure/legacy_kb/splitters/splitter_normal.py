from typing import List
import time

from .splitter_base import Splitter
from backend.modules.kb.domain.chunk_models import ChunkingInfo, DocumentChunk, TextSegment
from backend.modules.kb.domain.enums import ChunkingStrategy


class NormalSplitter(Splitter):
    name = "normal"

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须为正数")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap 必须为非负且小于 chunk_size")
        self.chunk_size = int(chunk_size)
        self.overlap = int(overlap)

    def split(self, text: str, kb_id: int, document_id: int) -> List[DocumentChunk]:
        text = (text or "").strip()
        chunks: List[DocumentChunk] = []
        start = 0
        n = len(text)
        now_ms = int(time.time() * 1000)
        while start < n:
            end = min(start + self.chunk_size, n)
            chunk = text[start:end]
            chunks.append(
                DocumentChunk(
                    document_id=int(document_id),
                    chunk_index=len(chunks),
                    segments=[TextSegment(text=chunk)],
                    chunking=ChunkingInfo(
                        strategy=ChunkingStrategy.fixed_size,
                        rule="normal_splitter",
                        overlap=int(self.overlap),
                        generator=self.name,
                    ),
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            )
            if end == n:
                break
            start = end - self.overlap
        return chunks
