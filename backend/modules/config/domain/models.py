from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import json


@dataclass(frozen=True, slots=True)
class SystemConfig:
    key: str
    value: Any
    description: Optional[str]
    created_at_ms: int
    updated_at_ms: int

    @property
    def value_json(self) -> str:
        return json.dumps(self.value, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class SystemConfigCreate:
    key: str
    value: Any
    description: Optional[str] = None
    created_at_ms: Optional[int] = None
    updated_at_ms: Optional[int] = None

