from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from backend.shared.ids import parse_file_id, parse_kb_id
from backend.modules.kb.application.services.file_ingestion import FileIngestionService
from backend.modules.kb.domain.errors import KnowledgeConflictError, KnowledgeNotFoundError
from backend.modules.kb.domain.models import (
    FileChunk,
    FileInfo,
    FileStatus,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBasePatch,
    KnowledgeFile,
    KnowledgeFileCreate,
    KnowledgeFilePatch,
)
from backend.modules.kb.domain.ports import KbFileStoragePort, KnowledgeBaseControllerPort, KnowledgeRepositoryPort


def _now_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)


@dataclass(frozen=True, slots=True)
class KnowledgeBaseUseCase:
    controller: KnowledgeBaseControllerPort
    repo: KnowledgeRepositoryPort
    ingestion: FileIngestionService
    storage: KbFileStoragePort

    def list_kbs(self) -> List[KnowledgeBase]:
        rows = list(self.repo.list_kbs())
        rows.sort(key=lambda m: int(getattr(m, "created_at_ms", 0)), reverse=True)
        return rows

    def create_kb(self, payload: Any) -> KnowledgeBase:
        existing_ids = [int(r.kb_id) for r in self.repo.list_kbs()]
        start_id = (max(existing_ids) + 1) if existing_ids else 1
        ts = _now_ms()
        name = str(getattr(payload, "name", "") or "").strip()
        desc = (str(getattr(payload, "description", "") or "").strip() or None)
        for candidate in range(start_id, start_id + 50):
            try:
                self.controller.createKnowledgeBase(candidate, reset_sqlite=False)
                self.repo.create_kb(
                    KnowledgeBaseCreate(
                        kb_id=candidate,
                        name=name,
                        description=desc,
                        created_at_ms=ts,
                        updated_at_ms=ts,
                    )
                )
                created = self.repo.get_kb(int(candidate))
                if created is None:
                    raise RuntimeError("创建知识库失败：持久化后未找到记录")
                return created
            except KnowledgeConflictError:
                continue
        raise KnowledgeConflictError("创建知识库失败：KB ID 已被占用")

    def update_kb(self, kb_id: str, payload: Any) -> KnowledgeBase:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        ts = _now_ms()
        patch = KnowledgeBasePatch(
            name=str(getattr(payload, "name", "")).strip() if (getattr(payload, "name", None) is not None) else None,
            description=(str(getattr(payload, "description", "")).strip() or None) if (getattr(payload, "description", None) is not None) else None,
            updated_at_ms=ts,
        )
        try:
            row = self.repo.update_kb(kb_int, patch)
        except KnowledgeNotFoundError:
            created_at = self._disk_kb_created_at(kb_int)
            self.repo.create_kb(
                KnowledgeBaseCreate(
                    kb_id=kb_int,
                    name=patch.name or f"知识库 {kb_int}",
                    description=patch.description,
                    created_at_ms=created_at,
                    updated_at_ms=ts,
                )
            )
            row = self.repo.get_kb(kb_int)
            if row is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
        return row

    def delete_kb(self, kb_id: str) -> None:
        kb_int = parse_kb_id(kb_id)
        try:
            self.repo.delete_kb(kb_int)
        except KnowledgeNotFoundError:
            pass
        self.controller.deleteKnowledgeBase(kb_int)

    def list_files(self, kb_id: str) -> List[KnowledgeFile]:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        return list(self.repo.list_files(kb_int))

    def save_upload(self, kb_id: str, name: str, content_b64: Optional[str]) -> KnowledgeFile:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        lower = name.lower()
        self.storage.ensure_uploads_dir(kb_int)
        saved_path = self.storage.upload_path(kb_int, name)
        if content_b64:
            import base64

            self.storage.write_bytes(saved_path, base64.b64decode(content_b64))

        ts = _now_ms()
        rows = self.repo.list_files(kb_int)
        existing_row = None
        for r in rows:
            if str(r.name or "") == name:
                existing_row = r
                break

        if existing_row is not None:
            fid = int(existing_row.file_id)
        else:
            used_ids = [int(r.file_id) for r in rows]
            start_id = (max(used_ids) + 1) if used_ids else 1
            fid = start_id
            for candidate in range(start_id, start_id + 50):
                try:
                    self.repo.create_file(
                        kb_int,
                        KnowledgeFileCreate(
                            file_id=candidate,
                            name=name,
                            mime_type="application/octet-stream",
                            created_at_ms=ts,
                            updated_at_ms=ts,
                            chunk_count=0,
                            status=FileStatus.uploaded,
                            source_path=saved_path,
                        ),
                    )
                    fid = candidate
                    break
                except KnowledgeConflictError:
                    continue

        mime = (
            "application/pdf"
            if lower.endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if lower.endswith(".xlsx")
            else "application/octet-stream"
        )
        self._upsert_file_row(
            kb_int,
            fid,
            name=name,
            mime_type=mime,
            created_at_ms=ts,
            updated_at_ms=ts,
            chunk_count=0,
            status=str(FileStatus.uploaded),
            source_path=saved_path,
        )
        row = self.repo.get_file(int(kb_int), int(fid))
        if row is None:
            raise RuntimeError("上传文件登记失败：持久化后未找到文件记录")
        return row

    def ingest_uploaded_file(self, kb_id: str, filename: str) -> KnowledgeFile:
        kb_int = parse_kb_id(kb_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        lower = filename.lower()
        src_path = self.storage.upload_path(kb_int, filename)
        if not self.storage.exists(src_path):
            raise FileNotFoundError("文件不存在，请先上传")

        if lower.endswith(".pdf"):
            info = self.ingestion.ingest_pdf(kb_id=kb_int, pdf_path=src_path)
            mime = "application/pdf"
        elif lower.endswith(".xlsx"):
            info = self.ingestion.ingest_excel(kb_id=kb_int, excel_path=src_path)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise ValueError("仅支持 PDF 或 Excel(xlsx)")

        ts = _now_ms()
        self._upsert_file_row(
            kb_int,
            int(info.id),
            name=info.filename,
            mime_type=mime,
            created_at_ms=ts,
            updated_at_ms=ts,
            chunk_count=int(info.chunk_count),
            status="done",
            source_path=src_path,
        )
        row = self.repo.get_file(int(kb_int), int(info.id))
        if row is None:
            raise RuntimeError("文件 ingestion 持久化失败：未找到文件记录")
        return row

    def read_file_chunks(self, kb_id: str, file_id: str) -> List[FileChunk]:
        kb_int = parse_kb_id(kb_id)
        fid = parse_file_id(file_id)
        self.controller.ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        rows = self.repo.list_chunks(kb_int, fid)
        out: List[FileChunk] = []
        for r in rows:
            out.append(
                FileChunk(
                    file_id=int(fid),
                    chunk_index=int(r.chunk_index),
                    content=str(r.content or ""),
                    metadata=r.metadata,
                    embedding=None,
                )
            )
        return out

    def delete_file_global(self, file_id: str) -> None:
        fid = parse_file_id(file_id)
        for kb_int in self.storage.list_kb_ids(self.controller.base_dir):
            if self.controller.deleteFile(kb_int, fid):
                try:
                    self.repo.delete_file(kb_int, fid)
                except KnowledgeNotFoundError:
                    pass
                return
        raise FileNotFoundError("文件不存在")

    def _disk_kb_created_at(self, kb_int: int) -> int:
        return int(self.storage.kb_created_at_ms(self.controller.kb_dir(kb_int)) or _now_ms())

    def _ensure_kb_row(self, kb_int: int) -> None:
        row = self.repo.get_kb(kb_int)
        if row is not None:
            return
        created_at = self._disk_kb_created_at(kb_int)
        self.repo.create_kb(
            KnowledgeBaseCreate(
                kb_id=kb_int,
                name=f"知识库 {kb_int}",
                description=None,
                created_at_ms=created_at,
                updated_at_ms=created_at,
            )
        )

    def _upsert_file_row(
        self,
        kb_int: int,
        file_id: int,
        *,
        name: str,
        mime_type: str,
        created_at_ms: int,
        updated_at_ms: int,
        chunk_count: int,
        status: str,
        source_path: Optional[str],
    ) -> None:
        existing = self.repo.get_file(kb_int, file_id)
        if existing is None:
            self.repo.create_file(
                kb_int,
                KnowledgeFileCreate(
                    file_id=int(file_id),
                    name=name,
                    mime_type=mime_type,
                    created_at_ms=int(created_at_ms),
                    updated_at_ms=int(updated_at_ms),
                    chunk_count=int(chunk_count),
                    status=FileStatus.coerce(status),
                    source_path=source_path,
                ),
            )
        else:
            self.repo.update_file(
                kb_int,
                file_id,
                KnowledgeFilePatch(
                    name=name,
                    mime_type=mime_type,
                    chunk_count=chunk_count,
                    status=FileStatus.coerce(status),
                    source_path=source_path,
                    updated_at_ms=updated_at_ms,
                ),
            )
