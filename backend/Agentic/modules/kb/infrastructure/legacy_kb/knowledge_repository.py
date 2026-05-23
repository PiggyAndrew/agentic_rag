from __future__ import annotations

from typing import Any, List, Optional, Protocol
import json
import time

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.modules.kb.infrastructure.persistence.models import KnowledgeBaseORM, KnowledgeChunkORM, KnowledgeFileORM
from backend.modules.kb.domain.errors import KnowledgeConflictError, KnowledgeNotFoundError
from backend.modules.kb.domain.chunk_models import DocumentChunk
from backend.modules.kb.domain.chunk_serialization import document_chunk_to_metadata, metadata_to_document_chunk
from backend.modules.kb.domain.document_models import Document
from backend.modules.kb.domain.enums import DocumentStatus
from backend.modules.kb.domain.kb_models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBasePatch


def _kb_from_row(row: KnowledgeBaseORM) -> KnowledgeBase:
    return KnowledgeBase(
        kb_id=int(row.kb_id),
        name=str(row.name),
        description=row.description,
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
    )


def _file_from_row(row: KnowledgeFileORM) -> Document:
    return Document(
        kb_id=int(row.kb_id),
        document_id=int(row.file_id),
        filename=str(row.name),
        mime_type=str(row.mime_type),
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
        chunk_count=int(row.chunk_count),
        status=DocumentStatus.coerce(row.status),
        source_path=row.source_path,
    )


def _chunk_from_row(row: KnowledgeChunkORM) -> DocumentChunk:
    raw_meta: Any = None
    if row.metadata_json:
        try:
            raw_meta = json.loads(row.metadata_json)
        except Exception:
            raw_meta = row.metadata_json
    restored = metadata_to_document_chunk(raw_meta)
    if restored is not None:
        return restored
    return DocumentChunk(
        document_id=int(row.file_id),
        chunk_index=int(row.chunk_index),
        segments=[],
        elements=[],
        created_at_ms=int(row.created_at_ms),
        updated_at_ms=int(row.updated_at_ms),
    )


class KnowledgeRepository(Protocol):
    def list_kbs(self) -> List[KnowledgeBase]: ...

    def get_kb(self, kb_id: int) -> Optional[KnowledgeBase]: ...

    def create_kb(self, kb: KnowledgeBaseCreate) -> KnowledgeBase: ...

    def update_kb(self, kb_id: int, patch: KnowledgeBasePatch) -> KnowledgeBase: ...

    def delete_kb(self, kb_id: int) -> None: ...

    def list_documents(self, kb_id: int) -> List[Document]: ...

    def get_document(self, kb_id: int, document_id: int) -> Optional[Document]: ...

    def create_document(self, kb_id: int, document: Document) -> Document: ...

    def update_document(self, kb_id: int, document_id: int, document: Document) -> Document: ...

    def delete_document(self, kb_id: int, document_id: int) -> None: ...

    def list_document_chunks(self, kb_id: int, document_id: int) -> List[DocumentChunk]: ...

    def upsert_document_chunks(self, kb_id: int, document_id: int, chunks: List[DocumentChunk]) -> None: ...

    def delete_document_chunks(self, kb_id: int, document_id: int) -> None: ...


class SqlAlchemyKnowledgeRepository:
    def __init__(self, manager: Optional[SqliteSessionManager] = None):
        self._manager = manager or get_default_sqlite_manager()

    def list_kbs(self) -> List[KnowledgeBase]:
        with self._manager.session_scope() as session:
            rows = session.execute(select(KnowledgeBaseORM).order_by(KnowledgeBaseORM.created_at_ms.desc())).scalars().all()
            return [_kb_from_row(r) for r in rows]

    def get_kb(self, kb_id: int) -> Optional[KnowledgeBase]:
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeBaseORM, int(kb_id))
            return _kb_from_row(row) if row is not None else None

    def create_kb(self, kb: KnowledgeBaseCreate) -> KnowledgeBase:
        kb_row = KnowledgeBaseORM(
            kb_id=int(kb.kb_id),
            name=str(kb.name),
            description=kb.description,
            created_at_ms=int(kb.created_at_ms),
            updated_at_ms=int(kb.updated_at_ms),
        )
        try:
            with self._manager.session_scope() as session:
                session.add(kb_row)
        except IntegrityError as e:
            raise KnowledgeConflictError(f"知识库已存在: kb_id={kb_row.kb_id}") from e
        return _kb_from_row(kb_row)

    def update_kb(self, kb_id: int, patch: KnowledgeBasePatch) -> KnowledgeBase:
        kb_int = int(kb_id)
        values: dict[str, Any] = {}
        if patch.name is not None:
            values["name"] = str(patch.name)
        if patch.description is not None:
            values["description"] = patch.description
        if patch.updated_at_ms is not None:
            values["updated_at_ms"] = int(patch.updated_at_ms)
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
            return _kb_from_row(row)

    def delete_kb(self, kb_id: int) -> None:
        kb_int = int(kb_id)
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeBaseORM, kb_int)
            if row is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
            session.delete(row)

    def list_documents(self, kb_id: int) -> List[Document]:
        kb_int = int(kb_id)
        with self._manager.session_scope() as session:
            rows = session.execute(
                select(KnowledgeFileORM)
                .where(KnowledgeFileORM.kb_id == kb_int)
                .order_by(KnowledgeFileORM.created_at_ms.desc(), KnowledgeFileORM.file_id.desc())
            ).scalars().all()
            return [_file_from_row(r) for r in rows]

    def get_document(self, kb_id: int, document_id: int) -> Optional[Document]:
        kb_int = int(kb_id)
        storage_document_id = int(document_id)
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": storage_document_id})
            return _file_from_row(row) if row is not None else None

    def create_document(self, kb_id: int, document: Document) -> Document:
        kb_int = int(kb_id)
        document_row = KnowledgeFileORM(
            kb_id=kb_int,
            file_id=int(document.document_id),
            name=str(document.filename),
            mime_type=str(document.mime_type),
            created_at_ms=int(document.created_at_ms),
            updated_at_ms=int(document.updated_at_ms),
            chunk_count=int(document.chunk_count),
            status=str(DocumentStatus.coerce(document.status).value),
            source_path=document.source_path,
        )
        try:
            with self._manager.session_scope() as session:
                if session.get(KnowledgeBaseORM, kb_int) is None:
                    raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
                session.add(document_row)
        except IntegrityError as e:
            raise KnowledgeConflictError(f"文档已存在: kb_id={kb_int} file_id={document_row.file_id}") from e
        return _file_from_row(document_row)

    def update_document(self, kb_id: int, document_id: int, document: Document) -> Document:
        kb_int = int(kb_id)
        storage_document_id = int(document_id)
        values: dict[str, Any] = {
            "name": str(document.filename),
            "mime_type": str(document.mime_type),
            "chunk_count": int(document.chunk_count),
            "status": str(DocumentStatus.coerce(document.status).value),
            "source_path": document.source_path,
            "updated_at_ms": int(document.updated_at_ms),
        }
        with self._manager.session_scope() as session:
            res = session.execute(
                update(KnowledgeFileORM)
                .where(KnowledgeFileORM.kb_id == kb_int, KnowledgeFileORM.file_id == storage_document_id)
                .values(**values)
            )
            if res.rowcount == 0:
                raise KnowledgeNotFoundError(f"文档不存在: kb_id={kb_int} file_id={storage_document_id}")
            row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": storage_document_id})
            if row is None:
                raise KnowledgeNotFoundError(f"文档不存在: kb_id={kb_int} file_id={storage_document_id}")
            return _file_from_row(row)

    def delete_document(self, kb_id: int, document_id: int) -> None:
        kb_int = int(kb_id)
        storage_document_id = int(document_id)
        with self._manager.session_scope() as session:
            row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": storage_document_id})
            if row is None:
                raise KnowledgeNotFoundError(f"文档不存在: kb_id={kb_int} file_id={storage_document_id}")
            session.execute(
                delete(KnowledgeChunkORM).where(
                    KnowledgeChunkORM.kb_id == kb_int,
                    KnowledgeChunkORM.file_id == storage_document_id,
                )
            )
            session.delete(row)

    def list_document_chunks(self, kb_id: int, document_id: int) -> List[DocumentChunk]:
        kb_int = int(kb_id)
        storage_document_id = int(document_id)
        with self._manager.session_scope() as session:
            rows = session.execute(
                select(KnowledgeChunkORM)
                .where(KnowledgeChunkORM.kb_id == kb_int, KnowledgeChunkORM.file_id == storage_document_id)
                .order_by(KnowledgeChunkORM.chunk_index.asc())
            ).scalars().all()
            return [_chunk_from_row(r) for r in rows]

    def upsert_document_chunks(self, kb_id: int, document_id: int, chunks: List[DocumentChunk]) -> None:
        kb_int = int(kb_id)
        storage_document_id = int(document_id)
        with self._manager.session_scope() as session:
            document_row = session.get(KnowledgeFileORM, {"kb_id": kb_int, "file_id": storage_document_id})
            if document_row is None:
                raise KnowledgeNotFoundError(f"文档不存在: kb_id={kb_int} file_id={storage_document_id}")
            session.execute(
                delete(KnowledgeChunkORM).where(
                    KnowledgeChunkORM.kb_id == kb_int,
                    KnowledgeChunkORM.file_id == storage_document_id,
                )
            )
            now_ms = int(time.time() * 1000)
            new_rows: List[KnowledgeChunkORM] = []
            for i, c in enumerate(chunks):
                chunk_index = int(c.chunk_index) if c.chunk_index is not None else i
                meta_json = json.dumps(document_chunk_to_metadata(c), ensure_ascii=False)
                new_rows.append(
                    KnowledgeChunkORM(
                        kb_id=kb_int,
                        file_id=storage_document_id,
                        chunk_index=int(chunk_index),
                        content=c.ai_text(),
                        metadata_json=meta_json,
                        created_at_ms=int(c.created_at_ms or now_ms),
                        updated_at_ms=int(c.updated_at_ms or now_ms),
                    )
                )
            if new_rows:
                session.add_all(new_rows)
            document_row.chunk_count = len(chunks)
            document_row.updated_at_ms = int(now_ms)

    def delete_document_chunks(self, kb_id: int, document_id: int) -> None:
        kb_int = int(kb_id)
        storage_document_id = int(document_id)
        with self._manager.session_scope() as session:
            session.execute(
                delete(KnowledgeChunkORM).where(
                    KnowledgeChunkORM.kb_id == kb_int,
                    KnowledgeChunkORM.file_id == storage_document_id,
                )
            )
