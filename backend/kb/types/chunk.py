from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .metadata import ChunkMetadata


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    kb_id: int
    file_id: int
    chunk_index: int
    content: str
    metadata: Optional[ChunkMetadata]
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True, slots=True)
class KnowledgeChunkUpsert:
    chunk_index: int
    content: str
    metadata: Optional[ChunkMetadata] = None
    created_at_ms: Optional[int] = None
    updated_at_ms: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", ChunkMetadata.coerce(self.metadata))

