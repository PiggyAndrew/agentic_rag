from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class FileStatus(str, Enum):
    uploaded = "uploaded"
    chunked = "chunked"
    vectorized = "vectorized"
    done = "done"
    error = "error"

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def coerce(cls, value: Any) -> FileStatus:
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.done
        s = str(value)
        for item in cls:
            if item.value == s:
                return item
        return cls.done


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    kb_id: int
    name: str
    description: Optional[str]
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True, slots=True)
class KnowledgeBaseCreate:
    kb_id: int
    name: str
    description: Optional[str]
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True, slots=True)
class KnowledgeBasePatch:
    name: Optional[str] = None
    description: Optional[str] = None
    updated_at_ms: Optional[int] = None


@dataclass(frozen=True, slots=True)
class KnowledgeFile:
    kb_id: int
    file_id: int
    name: str
    mime_type: str
    created_at_ms: int
    updated_at_ms: int
    chunk_count: int
    status: FileStatus
    source_path: Optional[str]


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


@dataclass
class ChunkMetadata:
    data: Dict[str, Any]

    @classmethod
    def coerce(cls, value: Any) -> Optional[ChunkMetadata]:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(data=value)
        return cls(data={"value": value})


@dataclass
class FileMeta:
    id: int
    filename: str
    chunk_count: int
    status: FileStatus | str = FileStatus.done

    def __post_init__(self) -> None:
        self.status = FileStatus.coerce(self.status)



@dataclass
class FileChunk:
    file_id: int
    chunk_index: int
    content: str
    metadata: Optional[ChunkMetadata | Dict[str, Any] | Any] = None
    embedding: Optional[list[float]] = None

    def __post_init__(self) -> None:
        self.metadata = ChunkMetadata.coerce(self.metadata)


@dataclass
class FileInfo:
    id: int
    filename: str
    chunk_count: int
    status: FileStatus | str = FileStatus.done

    def __post_init__(self) -> None:
        self.status = FileStatus.coerce(self.status)


@dataclass
class KnowledgeFileCreate:
    file_id: int
    name: str
    mime_type: str
    created_at_ms: int
    updated_at_ms: int
    chunk_count: int
    status: FileStatus | str
    source_path: Optional[str] = None

    def __post_init__(self) -> None:
        self.status = FileStatus.coerce(self.status)


@dataclass
class KnowledgeFilePatch:
    name: Optional[str] = None
    mime_type: Optional[str] = None
    chunk_count: Optional[int] = None
    status: Optional[FileStatus | str] = None
    source_path: Optional[str] = None
    updated_at_ms: Optional[int] = None

