from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.modules.config.domain.models import SystemConfig, SystemConfigCreate
from backend.modules.config.infrastructure.repository import SqlAlchemyConfigRepository


@dataclass(frozen=True, slots=True)
class SqliteConfigRepositoryAdapter:
    repo: SqlAlchemyConfigRepository

    def get(self, key: str) -> Optional[Any]:
        row = self.repo.get_config(key)
        return None if row is None else row.value

    def set(self, key: str, value: Any, *, description: Optional[str] = None) -> Any:
        row = self.repo.set_config(SystemConfigCreate(key=key, value=value, description=description))
        return row.value

    def delete(self, key: str) -> None:
        self.repo.delete_config(key)

    def list_all(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for r in self.repo.list_configs():
            out[str(r.key)] = r.value
        return out

    def list_configs(self) -> list[SystemConfig]:
        return [
            SystemConfig(
                key=str(r.key),
                value=r.value,
                description=r.description,
                created_at_ms=int(r.created_at_ms),
                updated_at_ms=int(r.updated_at_ms),
            )
            for r in self.repo.list_configs()
        ]
