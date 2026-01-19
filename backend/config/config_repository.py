from __future__ import annotations

from typing import List, Optional, Protocol
import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.config.config_models import SystemConfigORM
from backend.config.types import (
    SystemConfig,
    SystemConfigCreate,
)


def _config_from_row(row: SystemConfigORM) -> SystemConfig:
    val = row.value
    try:
        val = json.loads(row.value)
    except Exception:
        pass  # Keep as string if not valid json

    return SystemConfig(
        key=row.key,
        value=val,
        description=row.description,
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
    )


class ConfigRepositoryError(RuntimeError):
    """配置仓储层错误基类。"""


class ConfigNotFoundError(ConfigRepositoryError):
    """配置不存在。"""


class ConfigRepository(Protocol):
    """配置数据访问层接口。"""

    def get_config(self, key: str) -> Optional[SystemConfig]: ...

    def set_config(self, config: SystemConfigCreate) -> SystemConfig: ...

    def delete_config(self, key: str) -> None: ...

    def list_configs(self) -> List[SystemConfig]: ...


class SqlAlchemyConfigRepository:
    """基于 SQLAlchemy 的配置仓储实现。"""

    def __init__(self, manager: Optional[SqliteSessionManager] = None):
        self._manager = manager or get_default_sqlite_manager()

    def get_config(self, key: str) -> Optional[SystemConfig]:
        with self._manager.session_scope() as session:
            row = session.get(SystemConfigORM, key)
            return _config_from_row(row) if row is not None else None

    def set_config(self, config: SystemConfigCreate) -> SystemConfig:
        """创建或更新配置。"""
        key = config.key
        val_str = json.dumps(config.value, ensure_ascii=False)
        now_ms = int(time.time() * 1000)

        with self._manager.session_scope() as session:
            row = session.get(SystemConfigORM, key)
            if row:
                # Update
                row.value = val_str
                if config.description is not None:
                    row.description = config.description
                row.updated_at_ms = config.updated_at_ms or now_ms
                # session.add(row) is not strictly needed as it's attached
            else:
                # Create
                row = SystemConfigORM(
                    key=key,
                    value=val_str,
                    description=config.description,
                    created_at_ms=config.created_at_ms or now_ms,
                    updated_at_ms=config.updated_at_ms or now_ms,
                )
                session.add(row)
            
            # We must flush to ensure the object is ready, but session scope handles commit.
            # To return the object with correct values, we construct it from the row inside the session
            # or from the input + updated fields.
            # Reading from row is safer.
            session.flush() # Ensure defaults etc are populated if any (none here really)
            return _config_from_row(row)

    def delete_config(self, key: str) -> None:
        with self._manager.session_scope() as session:
            row = session.get(SystemConfigORM, key)
            if row:
                session.delete(row)

    def list_configs(self) -> List[SystemConfig]:
        with self._manager.session_scope() as session:
            rows = session.execute(
                select(SystemConfigORM).order_by(SystemConfigORM.key.asc())
            ).scalars().all()
            return [_config_from_row(r) for r in rows]
