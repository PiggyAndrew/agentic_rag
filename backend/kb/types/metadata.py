from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


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

