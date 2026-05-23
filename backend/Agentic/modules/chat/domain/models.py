from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChatSession:
    id: str
    title: str
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True, slots=True)
class ChatMessage:
    id: int
    session_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] | None
    created_at_ms: int

