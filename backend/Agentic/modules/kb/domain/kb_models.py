from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    """知识库主实体，承载知识库级稳定信息。"""

    kb_id: int
    name: str
    description: Optional[str]
    created_at_ms: int
    updated_at_ms: int
    files: list[object] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KnowledgeBaseCreate:
    """创建知识库时使用的输入模型。"""

    kb_id: int
    name: str
    description: Optional[str]
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True, slots=True)
class KnowledgeBasePatch:
    """更新知识库时使用的局部变更模型。"""

    name: Optional[str] = None
    description: Optional[str] = None
    updated_at_ms: Optional[int] = None


__all__ = [
    "KnowledgeBase",
    "KnowledgeBaseCreate",
    "KnowledgeBasePatch",
]
