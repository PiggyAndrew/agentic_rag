from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .enums import FileStatus
from .metadata import ChunkMetadata


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

