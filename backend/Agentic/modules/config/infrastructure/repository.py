from __future__ import annotations

from typing import Any, List, Optional
import json
import time

from sqlalchemy import select

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.modules.config.domain.models import SystemConfig, SystemConfigCreate
from backend.modules.config.infrastructure.persistence.models import SystemConfigORM


def _config_from_row(row: SystemConfigORM) -> SystemConfig:
    val: Any = row.value
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:
            pass
    return SystemConfig(
        key=row.key,
        value=val,
        description=row.description,
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
    )


class SqlAlchemyConfigRepository:
    def __init__(self, manager: Optional[SqliteSessionManager] = None):
        self._manager = manager or get_default_sqlite_manager()

    def get_config(self, key: str) -> Optional[SystemConfig]:
        with self._manager.session_scope() as session:
            row = session.get(SystemConfigORM, key)
            return _config_from_row(row) if row is not None else None

    def set_config(self, config: SystemConfigCreate) -> SystemConfig:
        key = config.key
        val_str = json.dumps(config.value, ensure_ascii=False)
        now_ms = int(time.time() * 1000)

        with self._manager.session_scope() as session:
            row = session.get(SystemConfigORM, key)
            if row:
                row.value = val_str
                if config.description is not None:
                    row.description = config.description
                row.updated_at_ms = config.updated_at_ms or now_ms
            else:
                row = SystemConfigORM(
                    key=key,
                    value=val_str,
                    description=config.description,
                    created_at_ms=config.created_at_ms or now_ms,
                    updated_at_ms=config.updated_at_ms or now_ms,
                )
                session.add(row)
            session.flush()
            return _config_from_row(row)

    def delete_config(self, key: str) -> None:
        with self._manager.session_scope() as session:
            row = session.get(SystemConfigORM, key)
            if row:
                session.delete(row)

    def list_configs(self) -> List[SystemConfig]:
        with self._manager.session_scope() as session:
            rows = session.execute(select(SystemConfigORM).order_by(SystemConfigORM.key.asc())).scalars().all()
            return [_config_from_row(r) for r in rows]

