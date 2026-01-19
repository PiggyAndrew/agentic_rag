from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
import json


@dataclass(frozen=True, slots=True)
class SystemConfig:
    key: str
    value: Any  # 可以是 str, int, bool, dict, list 等，底层存储为 JSON 字符串
    description: Optional[str]
    created_at_ms: int
    updated_at_ms: int

    @property
    def value_json(self) -> str:
        """返回 value 的 JSON 字符串表示"""
        return json.dumps(self.value, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class SystemConfigCreate:
    key: str
    value: Any
    description: Optional[str] = None
    created_at_ms: Optional[int] = None
    updated_at_ms: Optional[int] = None


@dataclass(frozen=True, slots=True)
class SystemConfigPatch:
    value: Optional[Any] = None
    description: Optional[str] = None
    updated_at_ms: Optional[int] = None
