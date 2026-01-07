from __future__ import annotations

from enum import Enum
from typing import Any


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

