from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from backend.modules.config.domain.models import SystemConfig
from backend.modules.config.domain.ports import ConfigRepositoryPort, ConfigSource


@dataclass(frozen=True, slots=True)
class ConfigService:
    sources: tuple[ConfigSource, ...]
    repository: ConfigRepositoryPort

    def get(self, key: str, default: Any = None) -> Any:
        k = str(key or "").strip()
        if not k:
            return default
        for src in self.sources:
            v = src.get(k)
            if v is not None:
                return v
        v = self.repository.get(k)
        return default if v is None else v

    def get_str(self, key: str, default: str = "") -> str:
        v = self.get(key, default)
        return default if v is None else str(v)

    def get_int(self, key: str, default: int = 0) -> int:
        v = self.get(key, default)
        if v is None:
            return default
        try:
            return int(v)
        except Exception:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        v = self.get(key, default)
        if isinstance(v, bool):
            return v
        if v is None:
            return default
        s = str(v).strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def get_json(self, key: str, default: Any = None) -> Any:
        v = self.get(key, None)
        if v is None:
            return default
        if isinstance(v, (dict, list)):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return default
        return default

    def list_persisted(self) -> dict[str, Any]:
        return self.repository.list_all()

    def list_configs(self) -> list[SystemConfig]:
        return self.repository.list_configs()

    def set(self, key: str, value: Any, *, description: Optional[str] = None) -> Any:
        return self.repository.set(key, value, description=description)

    def delete(self, key: str) -> None:
        self.repository.delete(key)


def build_config_service(*, sources: Iterable[ConfigSource], repository: ConfigRepositoryPort) -> ConfigService:
    return ConfigService(sources=tuple(sources), repository=repository)
