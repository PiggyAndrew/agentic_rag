from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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

