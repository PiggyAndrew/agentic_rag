from __future__ import annotations

from typing import List
import os

from sqlalchemy import Engine, text


class MigrationError(RuntimeError):
    """迁移执行失败。"""


def _ensure_migrations_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at_ms INTEGER NOT NULL
                )
                """
            )
        )


def _list_sql_files(migrations_dir: str) -> List[str]:
    base = os.path.abspath(migrations_dir)
    sqlite_dir = os.path.join(base, "sqlite")
    if not os.path.isdir(sqlite_dir):
        return []
    files = [os.path.join(sqlite_dir, f) for f in os.listdir(sqlite_dir) if f.lower().endswith(".sql")]
    files.sort(key=lambda p: os.path.basename(p))
    return files


def _applied_versions(engine: Engine) -> set[str]:
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {str(r[0]) for r in rows}


def apply_sql_migrations(engine: Engine, *, migrations_dir: str) -> None:
    """应用 migrations/sqlite 目录下的 SQL 脚本。

    - 脚本文件名作为版本号，按字典序执行。
    - 每个脚本在独立事务中执行，失败会回滚并抛出异常。
    """
    _ensure_migrations_table(engine)
    files = _list_sql_files(migrations_dir)
    if not files:
        return
    applied = _applied_versions(engine)
    for path in files:
        version = os.path.basename(path)
        if version in applied:
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
        except OSError as e:
            raise MigrationError(f"无法读取迁移脚本: {path}: {e}") from e

        with engine.begin() as conn:
            raw = conn.connection
            try:
                raw.executescript(sql)
                conn.execute(
                    text(
                        "INSERT INTO schema_migrations(version, applied_at_ms) VALUES (:v, CAST(strftime('%s','now') AS INTEGER) * 1000)"
                    ),
                    {"v": version},
                )
            except Exception as e:
                raise MigrationError(f"迁移失败: {version}: {type(e).__name__}: {e}") from e

