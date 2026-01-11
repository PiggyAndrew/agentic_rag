from typing import List
from .splitter_base import Splitter
from backend.kb.types.chunk import KnowledgeChunk
from backend.kb.types.metadata import ChunkMetadata
import time


class NormalSplitter(Splitter):
    """定长切片拆分器：返回标准片段字典列表。"""

    name = "normal"

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须为正数")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap 必须为非负且小于 chunk_size")
        self.chunk_size = int(chunk_size)
        self.overlap = int(overlap)

    def split(self, text: str, kb_id: int, file_id: int) -> List[KnowledgeChunk]:
        text = (text or "").strip()
        chunks: List[KnowledgeChunk] = []
        start = 0
        n = len(text)
        now_ms = int(time.time() * 1000)
        while start < n:
            end = min(start + self.chunk_size, n)
            chunk = text[start:end]
            meta = ChunkMetadata.coerce({"number": "", "title": "", "path": []})
            chunks.append(
                KnowledgeChunk(
                    kb_id=int(kb_id),
                    file_id=int(file_id),
                    chunk_index=len(chunks),
                    content=chunk,
                    metadata=meta,
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            )
            if end == n:
                break
            start = end - self.overlap
        return chunks

