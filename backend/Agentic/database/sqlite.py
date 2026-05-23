from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional, Sequence
import os

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import MetaData


@dataclass(frozen=True, slots=True)
class SqliteSessionManager:
    """SQLite 会话管理器：为每次调用提供独立 Session 与事务边界。"""

    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def from_url(cls, url: str, *, echo: bool = False, timeout_s: int = 30) -> "SqliteSessionManager":
        """从 SQLite URL 构建引擎与 SessionFactory。"""
        if url.startswith("sqlite:///"):
            file_path = url[len("sqlite:///") :]
            dirp = os.path.dirname(os.path.abspath(file_path))
            if dirp:
                os.makedirs(dirp, exist_ok=True)

        engine = create_engine(
            url,
            echo=echo,
            connect_args={"check_same_thread": False, "timeout": timeout_s},
        )

        # @event.listens_for(engine, "connect")
        # def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        #     cursor = dbapi_connection.cursor()
        #     try:
        #         cursor.execute("PRAGMA foreign_keys=ON")
        #         cursor.execute("PRAGMA journal_mode=WAL")
        #     finally:
        #         cursor.close()

        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        return cls(engine=engine, session_factory=factory)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """创建一个事务性 Session，上下文退出时自动提交/回滚。"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """关闭数据库引擎，释放所有连接池。"""
        self.engine.dispose()


_default_manager: Optional[SqliteSessionManager] = None


def get_default_sqlite_manager() -> SqliteSessionManager:
    """获取默认 SQLite SessionManager（基于 Settings 单例）。"""
    global _default_manager
    if _default_manager is not None:
        return _default_manager
    from backend.modules.config.infrastructure.boot_config import get_boot_config

    settings = get_boot_config()
    _default_manager = SqliteSessionManager.from_url(
        settings.KB_SQLITE_URL,
        echo=bool(settings.KB_SQLITE_ECHO),
    )
    return _default_manager


def build_sqlite_manager(*, url: Optional[str] = None, echo: Optional[bool] = None) -> SqliteSessionManager:
    from backend.modules.config.infrastructure.boot_config import get_boot_config

    settings = get_boot_config()
    return SqliteSessionManager.from_url(
        url or settings.KB_SQLITE_URL,
        echo=bool(settings.KB_SQLITE_ECHO) if echo is None else bool(echo),
    )


def init_sqlite_database(
    *,
    manager: Optional[SqliteSessionManager] = None,
    migrations_dir: Optional[str] = None,
    metadatas: Optional[Sequence[MetaData]] = None,
) -> None:
    """初始化数据库：优先执行迁移脚本，随后创建 ORM 表结构。"""
    mgr = manager or get_default_sqlite_manager()

    from backend.database.migrations.runner import apply_sql_migrations

    apply_sql_migrations(
        mgr.engine,
        migrations_dir=migrations_dir or _default_migrations_dir(),
    )
    if metadatas:
        for metadata in metadatas:
            metadata.create_all(bind=mgr.engine)


def _default_migrations_dir() -> str:
    from backend.modules.config.infrastructure.boot_config import get_boot_config

    return get_boot_config().KB_SQLITE_MIGRATIONS_DIR
