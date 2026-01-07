from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .enums import FileStatus


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

