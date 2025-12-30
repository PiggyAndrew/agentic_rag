from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import os
import re

from backend.database.sqlite import SqliteSessionManager, init_sqlite_database
from backend.kb.knowledge_base import PersistentKnowledgeBaseController
from backend.kb.knowledge_repository import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
    SqlAlchemyKnowledgeRepository,
)


def _now_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)


def format_kb_id(kb_int: int) -> str:
    return f"kb-{kb_int}"


def parse_kb_id(kb_id: str) -> int:
    m = re.match(r"^kb-(\d+)$", str(kb_id))
    if m:
        return int(m.group(1))
    return int(kb_id)


def parse_file_id(file_id: str) -> int:
    m = re.match(r"^f-(\d+)$", str(file_id))
    if not m:
        raise ValueError("文件ID格式错误")
    return int(m.group(1))


@dataclass(frozen=True, slots=True)
class KnowledgeService:
    controller: PersistentKnowledgeBaseController
    repo: SqlAlchemyKnowledgeRepository

    def list_kbs(self) -> List[Dict[str, Any]]:
        rows = self.repo.list_kbs()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": format_kb_id(int(r["kb_id"])),
                    "name": r["name"],
                    "description": r.get("description"),
                    "createdAt": int(r["created_at_ms"]),
                }
            )
        out.sort(key=lambda m: m.get("createdAt", 0), reverse=True)
        return out

    def create_kb(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing_ids = [int(r["kb_id"]) for r in self.repo.list_kbs()]
        start_id = (max(existing_ids) + 1) if existing_ids else 1
        ts = _now_ms()
        name = str(payload.get("name", "")).strip()
        desc = (str(payload.get("description", "")).strip() or None)
        for candidate in range(start_id, start_id + 50):
            try:
                self.controller.createKnowledgeBase(candidate, reset_sqlite=False)
                self.repo.create_kb(
                    {
                        "kb_id": candidate,
                        "name": name,
                        "description": desc,
                        "created_at_ms": ts,
                        "updated_at_ms": ts,
                    }
                )
                return {"id": format_kb_id(candidate), "name": name, "description": desc, "createdAt": ts}
            except KnowledgeConflictError:
                continue
        raise KnowledgeConflictError("创建知识库失败：KB ID 已被占用")

    def update_kb(self, kb_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        kb_int = parse_kb_id(kb_id)
        self.controller._ensure_kb(kb_int)
        ts = _now_ms()
        patch: Dict[str, Any] = {"updated_at_ms": ts}
        if "name" in payload and payload["name"] is not None:
            patch["name"] = str(payload["name"]).strip()
        if "description" in payload:
            patch["description"] = (str(payload["description"]).strip() or None) if payload["description"] is not None else None
        try:
            row = self.repo.update_kb(kb_int, patch)
        except KnowledgeNotFoundError:
            created_at = self._disk_kb_created_at(kb_int)
            self.repo.create_kb(
                {
                    "kb_id": kb_int,
                    "name": patch.get("name") or f"知识库 {kb_int}",
                    "description": patch.get("description"),
                    "created_at_ms": created_at,
                    "updated_at_ms": ts,
                }
            )
            row = self.repo.get_kb(kb_int)
            if row is None:
                raise KnowledgeNotFoundError(f"知识库不存在: kb_id={kb_int}")
        return {
            "id": format_kb_id(kb_int),
            "name": row["name"],
            "description": row.get("description"),
            "createdAt": int(row["created_at_ms"]),
        }

    def delete_kb(self, kb_id: str) -> None:
        kb_int = parse_kb_id(kb_id)
        try:
            self.repo.delete_kb(kb_int)
        except KnowledgeNotFoundError:
            pass
        self.controller.deleteKnowledgeBase(kb_int)

    def list_files(self, kb_id: str) -> List[Dict[str, Any]]:
        kb_int = parse_kb_id(kb_id)
        self.controller._ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        rows = self.repo.list_files(kb_int)
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": f"f-{int(r['file_id'])}",
                    "kbId": format_kb_id(kb_int),
                    "name": r["name"],
                    "type": r["mime_type"],
                    "createdAt": int(r["created_at_ms"]),
                    "chunkCount": int(r["chunk_count"]),
                    "status": r["status"],
                }
            )
        return out

    def save_upload(self, kb_id: str, name: str, content_b64: Optional[str]) -> Dict[str, Any]:
        kb_int = parse_kb_id(kb_id)
        self.controller._ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        lower = name.lower()
        uploads_dir = os.path.join(self.controller._kb_dir(kb_int), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        saved_path = os.path.join(uploads_dir, name)
        if content_b64:
            import base64

            with open(saved_path, "wb") as f:
                f.write(base64.b64decode(content_b64))

        ts = _now_ms()
        rows = self.repo.list_files(kb_int)
        existing_row = None
        for r in rows:
            if str(r.get("name") or "") == name:
                existing_row = r
                break

        if existing_row is not None:
            fid = int(existing_row["file_id"])
        else:
            used_ids = [int(r["file_id"]) for r in rows]
            start_id = (max(used_ids) + 1) if used_ids else 1
            fid = start_id
            for candidate in range(start_id, start_id + 50):
                try:
                    self.repo.create_file(
                        kb_int,
                        {
                            "file_id": candidate,
                            "name": name,
                            "mime_type": "application/octet-stream",
                            "created_at_ms": ts,
                            "updated_at_ms": ts,
                            "chunk_count": 0,
                            "status": "uploaded",
                            "source_path": saved_path,
                        },
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
            status="uploaded",
            source_path=saved_path,
        )
        return {
            "id": f"f-{fid}",
            "kbId": format_kb_id(kb_int),
            "name": name,
            "type": mime,
            "createdAt": ts,
            "chunkCount": 0,
            "status": "uploaded",
        }

    def ingest_uploaded_file(self, kb_id: str, filename: str) -> Dict[str, Any]:
        kb_int = parse_kb_id(kb_id)
        self.controller._ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        lower = filename.lower()
        uploads_dir = os.path.join(self.controller._kb_dir(kb_int), "uploads")
        src_path = os.path.join(uploads_dir, filename)
        if not os.path.exists(src_path):
            raise FileNotFoundError("文件不存在，请先上传")

        from backend.kb.ingestion import ingest_excel, ingest_pdf

        if lower.endswith(".pdf"):
            info = ingest_pdf(self.controller, kb_int, src_path)
            mime = "application/pdf"
        elif lower.endswith(".xlsx"):
            info = ingest_excel(self.controller, kb_int, src_path)
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
        return {
            "id": f"f-{info.id}",
            "kbId": format_kb_id(kb_int),
            "name": info.filename,
            "type": mime,
            "createdAt": ts,
            "chunkCount": int(info.chunk_count),
            "status": "done",
        }

    def read_file_chunks(self, kb_id: str, file_id: str) -> List[Dict[str, Any]]:
        kb_int = parse_kb_id(kb_id)
        fid = parse_file_id(file_id)
        self.controller._ensure_kb(kb_int)
        self._ensure_kb_row(kb_int)
        rows = self.repo.list_chunks(kb_int, fid)
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "file_id": fid,
                    "chunk_index": int(r["chunk_index"]),
                    "content": r["content"],
                    "metadata": r.get("metadata"),
                    "embedding": None,
                }
            )
        return out

    def delete_file_global(self, file_id: str) -> None:
        fid = parse_file_id(file_id)
        if not os.path.exists(self.controller.base_dir):
            raise FileNotFoundError("文件不存在")
        for name in os.listdir(self.controller.base_dir):
            try:
                kb_int = int(name)
            except Exception:
                continue
            if self.controller.deleteFile(kb_int, fid):
                try:
                    self.repo.delete_file(kb_int, fid)
                except KnowledgeNotFoundError:
                    pass
                return
        raise FileNotFoundError("文件不存在")

    def _disk_kb_created_at(self, kb_int: int) -> int:
        p = self.controller._kb_dir(kb_int)
        if os.path.exists(p):
            return int(os.path.getmtime(p) * 1000)
        return _now_ms()

    def _ensure_kb_row(self, kb_int: int) -> None:
        row = self.repo.get_kb(kb_int)
        if row is not None:
            return
        created_at = self._disk_kb_created_at(kb_int)
        self.repo.create_kb(
            {
                "kb_id": kb_int,
                "name": f"知识库 {kb_int}",
                "description": None,
                "created_at_ms": created_at,
                "updated_at_ms": created_at,
            }
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
                {
                    "file_id": file_id,
                    "name": name,
                    "mime_type": mime_type,
                    "created_at_ms": created_at_ms,
                    "updated_at_ms": updated_at_ms,
                    "chunk_count": chunk_count,
                    "status": status,
                    "source_path": source_path,
                },
            )
        else:
            self.repo.update_file(
                kb_int,
                file_id,
                {
                    "name": name,
                    "mime_type": mime_type,
                    "chunk_count": chunk_count,
                    "status": status,
                    "source_path": source_path,
                    "updated_at_ms": updated_at_ms,
                },
            )


_default_service: Optional[KnowledgeService] = None


def get_default_knowledge_service(
    *,
    controller: Optional[PersistentKnowledgeBaseController] = None,
    manager: Optional[SqliteSessionManager] = None,
) -> KnowledgeService:
    global _default_service
    if _default_service is not None:
        return _default_service
    init_sqlite_database(manager=manager)
    ctrl = controller or PersistentKnowledgeBaseController(base_dir=os.path.join("data", "kb"), manager=manager)
    repo = SqlAlchemyKnowledgeRepository(manager=manager)
    _default_service = KnowledgeService(controller=ctrl, repo=repo)
    return _default_service
