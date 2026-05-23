from __future__ import annotations

from typing import Any, Optional, Protocol

from backend.modules.config.domain.models import SystemConfig


class ConfigSource(Protocol):
    def get(self, key: str) -> Optional[Any]: ...


class ConfigRepositoryPort(Protocol):
    def get(self, key: str) -> Optional[Any]: ...

    def set(self, key: str, value: Any, *, description: Optional[str] = None) -> Any: ...

    def delete(self, key: str) -> None: ...

    def list_all(self) -> dict[str, Any]: ...

    def list_configs(self) -> list[SystemConfig]: ...
