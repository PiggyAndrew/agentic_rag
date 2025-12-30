from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
import json
import time

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.kb.knowledge_models import KnowledgeBaseORM, KnowledgeChunkORM, KnowledgeFileORM

class KnowledgeRepositoryError(RuntimeError):
    """知识库仓储层错误基类。"""


class KnowledgeNotFoundError(KnowledgeRepositoryError):
    """目标记录不存在。"""


class KnowledgeConflictError(KnowledgeRepositoryError):
    """目标记录冲突（已存在或违反唯一约束）。"""


class KnowledgeRepository(Protocol):
    """知识库数据访问层接口（CRUD）。"""

    def list_kbs(self) -> List[Dict[str, Any]]: ...

    def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: ...

    def create_kb(self, kb: Dict[str, Any]) -> Dict[str, Any]: ...

    def update_kb(self, kb_id: int, patch: Dict[str, Any]) -> Dict[str, Any]: ...

    def delete_kb(self, kb_id: int) -> None: ...

    def list_files(self, kb_id: int) -> List[Dict[str, Any]]: ...

    def get_file(self, kb_id: int, file_id: int) -> Optional[Dict[str, Any]]: ...

    def create_file(self, kb_id: int, file: Dict[str, Any]) -> Dict[str, Any]: ...

    def update_file(self, kb_id: int, file_id: int, patch: Dict[str, Any]) -> Dict[str, Any]: ...

    def delete_file(self, kb_id: int, file_id: int) -> None: ...

    def list_chunks(self, kb_id: int, file_id: int) -> List[Dict[str, Any]]: ...

    def upsert_chunks(self, kb_id: int, file_id: int, chunks: List[Dict[str, Any]]) -> None: ...

    def delete_chunks(self, kb_id: int, file_id: int) -> None: ...


class SqlAlchemyKnowledgeRepository:
    """基于 SQLAlchemy 的知识库仓储实现（SQLite）。"""

    def __init__(self, manager: Optional[SqliteSessionManager] = None):
        self._manager = manager or get_default_sqlite_manager()

    def list_kbs(self) -> List[Dict[str, Any]]:
        with self._manager.session_scope() as session:
            rows = session.execute(
                select(KnowledgeBaseORM).order_by(KnowledgeBaseORM.created_at_ms.desc())
            ).scalars().all()
            return [_kb_to_dict(r) for r in rows]

    def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]:
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeBaseORM, int(kb_id))
            return _kb_to_dict(row) if row is not None else None

    def create_kb(self, kb: Dict[str, Any]) -> Dict[str, Any]:
        kb_row = KnowledgeBaseORM(
            kb_id=int(kb["kb_id"]),
            name=str(kb["name"]),
            description=kb.get("description"),
            created_at_ms=int(kb["created_at_ms"]),
            updated_at_ms=int(kb["updated_at_ms"]),
        )
        try:
            with self._manager.session_scope() as session:
                session.add(kb_row)
        except IntegrityError as e:
            raise KnowledgeConflictError(f"知识库已存在: kb_id={kb_row.kb_id}") from e
        return _kb_to_dict(kb_row)

    def update_kb(self, kb_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        kb_int = int(kb_id)
        values: Dict[str, Any] = {}
        if "name" in patch and patch["name"] is not None:
            values["name"] = str(patch["name"])
        if "description" in patch:
            values["description"] = patch["description"]
        if "updated_at_ms" in patch and patch["updated_at_ms"] is not None:
            values["updated_at_ms"] = int(patch["updated_at_ms"])
        if not values:
            existing = self.get_kb(kb_int)
            if existing is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
            return existing
        with self._manager.session_scope() as session:
            res = session.execute(update(KnowledgeBaseORM).where(KnowledgeBaseORM.kb_id == kb_int).values(**values))
            if res.rowcount == 0:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
            row = session.get(KnowledgeBaseORM, kb_int)
            if row is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
            return _kb_to_dict(row)

    def delete_kb(self, kb_id: int) -> None:
        kb_int = int(kb_id)
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeBaseORM, kb_int)
            if row is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
            session.delete(row)

    def list_files(self, kb_id: int) -> List[Dict[str, Any]]:
        kb_int = int(kb_id)
        with self._manager.session_scope() as session:
            rows = session.execute(
                select(KnowledgeFileORM)
                .where(KnowledgeFileORM.kb_id == kb_int)
                .order_by(KnowledgeFileORM.created_at_ms.desc(), KnowledgeFileORM.file_id.desc())
            ).scalars().all()
            return [_file_to_dict(r) for r in rows]

    def get_file(self, kb_id: int, file_id: int) -> Optional[Dict[str, Any]]:
        kb_int = int(kb_id)
        fid = int(file_id)
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": fid})
            return _file_to_dict(row) if row is not None else None

    def create_file(self, kb_id: int, file: Dict[str, Any]) -> Dict[str, Any]:
        kb_int = int(kb_id)
        file_row = KnowledgeFileORM(
            kb_id=kb_int,
            file_id=int(file["file_id"]),
            name=str(file["name"]),
            mime_type=str(file["mime_type"]),
            created_at_ms=int(file["created_at_ms"]),
            updated_at_ms=int(file["updated_at_ms"]),
            chunk_count=int(file.get("chunk_count", 0)),
            status=str(file.get("status", "done")),
            source_path=file.get("source_path"),
        )
        try:
            with self._manager.session_scope() as session:
                if session.get(KnowledgeBaseORM, kb_int) is None:
                    raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
                session.add(file_row)
        except IntegrityError as e:
            raise KnowledgeConflictError(f"文件已存在: kb_id={kb_int} file_id={file_row.file_id}") from e
        return _file_to_dict(file_row)

    def update_file(self, kb_id: int, file_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        kb_int = int(kb_id)
        fid = int(file_id)
        values: Dict[str, Any] = {}
        if "name" in patch and patch["name"] is not None:
            values["name"] = str(patch["name"])
        if "mime_type" in patch and patch["mime_type"] is not None:
            values["mime_type"] = str(patch["mime_type"])
        if "chunk_count" in patch and patch["chunk_count"] is not None:
            values["chunk_count"] = int(patch["chunk_count"])
        if "status" in patch and patch["status"] is not None:
            values["status"] = str(patch["status"])
        if "source_path" in patch:
            values["source_path"] = patch["source_path"]
        if "updated_at_ms" in patch and patch["updated_at_ms"] is not None:
            values["updated_at_ms"] = int(patch["updated_at_ms"])
        if not values:
            existing = self.get_file(kb_int, fid)
            if existing is None:
                raise KnowledgeNotFoundError(f"文件不存在: kb_id={kb_int} file_id={fid}")
            return existing
        with self._manager.session_scope() as session:
            res = session.execute(
                update(KnowledgeFileORM)
                .where(KnowledgeFileORM.kb_id == kb_int, KnowledgeFileORM.file_id == fid)
                .values(**values)
            )
            if res.rowcount == 0:
                raise KnowledgeNotFoundError(f"文件不存在: kb_id={kb_int} file_id={fid}")
            row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": fid})
            if row is None:
                raise KnowledgeNotFoundError(f"文件不存在: kb_id={kb_int} file_id={fid}")
            return _file_to_dict(row)

    def delete_file(self, kb_id: int, file_id: int) -> None:
        kb_int = int(kb_id)
        fid = int(file_id)
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": fid})
            if row is None:
                raise KnowledgeNotFoundError(f"文件不存在: kb_id={kb_int} file_id={fid}")
            session.execute(
                delete(KnowledgeChunkORM).where(KnowledgeChunkORM.kb_id == kb_int, KnowledgeChunkORM.file_id == fid)
            )
            session.delete(row)

    def list_chunks(self, kb_id: int, file_id: int) -> List[Dict[str, Any]]:
        kb_int = int(kb_id)
        fid = int(file_id)
        with self._manager.session_scope() as session:
            rows = session.execute(
                select(KnowledgeChunkORM)
                .where(KnowledgeChunkORM.kb_id == kb_int, KnowledgeChunkORM.file_id == fid)
                .order_by(KnowledgeChunkORM.chunk_index.asc())
            ).scalars().all()
            return [_chunk_to_dict(r) for r in rows]

    def upsert_chunks(self, kb_id: int, file_id: int, chunks: List[Dict[str, Any]]) -> None:
        kb_int = int(kb_id)
        fid = int(file_id)
        with self._manager.session_scope() as session:
            file_row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": fid})
            if file_row is None:
                raise KnowledgeNotFoundError(f"文件不存在: kb_id={kb_int} file_id={fid}")
            session.execute(
                delete(KnowledgeChunkORM).where(KnowledgeChunkORM.kb_id == kb_int, KnowledgeChunkORM.file_id == fid)
            )
            now_ms = int(time.time() * 1000)
            new_rows: List[KnowledgeChunkORM] = []
            for i, c in enumerate(chunks):
                chunk_index = c.get("chunk_index")
                if chunk_index is None:
                    chunk_index = c.get("chunkIndex")
                if chunk_index is None:
                    chunk_index = i
                meta = c.get("metadata")
                meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
                new_rows.append(
                    KnowledgeChunkORM(
                        kb_id=kb_int,
                        file_id=fid,
                        chunk_index=int(chunk_index),
                        content=str(c.get("content", "")),
                        metadata_json=meta_json,
                        created_at_ms=int(c.get("created_at_ms", now_ms)),
                        updated_at_ms=int(c.get("updated_at_ms", now_ms)),
                    )
                )
            if new_rows:
                session.add_all(new_rows)
            file_row.chunk_count = len(chunks)
            file_row.updated_at_ms = int(now_ms)

    def delete_chunks(self, kb_id: int, file_id: int) -> None:
        kb_int = int(kb_id)
        fid = int(file_id)
        with self._manager.session_scope() as session:
            session.execute(
                delete(KnowledgeChunkORM).where(KnowledgeChunkORM.kb_id == kb_int, KnowledgeChunkORM.file_id == fid)
            )


def _kb_to_dict(row: KnowledgeBaseORM) -> Dict[str, Any]:
    return {
        "kb_id": int(row.kb_id),
        "name": row.name,
        "description": row.description,
        "created_at_ms": int(row.created_at_ms),
        "updated_at_ms": int(row.updated_at_ms),
    }


def _file_to_dict(row: KnowledgeFileORM) -> Dict[str, Any]:
    return {
        "kb_id": int(row.kb_id),
        "file_id": int(row.file_id),
        "name": row.name,
        "mime_type": row.mime_type,
        "created_at_ms": int(row.created_at_ms),
        "updated_at_ms": int(row.updated_at_ms),
        "chunk_count": int(row.chunk_count),
        "status": row.status,
        "source_path": row.source_path,
    }


def _chunk_to_dict(row: KnowledgeChunkORM) -> Dict[str, Any]:
    metadata: Any = None
    if row.metadata_json:
        try:
            metadata = json.loads(row.metadata_json)
        except Exception:
            metadata = row.metadata_json
    return {
        "kb_id": int(row.kb_id),
        "file_id": int(row.file_id),
        "chunk_index": int(row.chunk_index),
        "content": row.content,
        "metadata": metadata,
        "created_at_ms": int(row.created_at_ms),
        "updated_at_ms": int(row.updated_at_ms),
    }
