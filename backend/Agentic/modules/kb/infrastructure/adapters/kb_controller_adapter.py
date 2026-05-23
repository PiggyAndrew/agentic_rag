from __future__ import annotations

import os
from typing import Any, Optional

from backend.modules.kb.domain.kb_models import KnowledgeBaseCreate
from backend.modules.kb.domain.ports import KnowledgeBaseControllerPort
from backend.modules.kb.domain.errors import KnowledgeNotFoundError
from backend.modules.kb.infrastructure.legacy_kb.services.paths import KbPaths


class KnowledgeBaseControllerAdapter(KnowledgeBaseControllerPort):
    def __init__(self, base_dir: str = "data/kb", repo: Optional[Any] = None):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._paths = KbPaths(self.base_dir)
        self._repo = repo

    def kb_dir(self, kb_id: int) -> str:
        return self._paths.kb_dir(kb_id)

    def assets_images_dir(self, kb_id: int, document_id: int) -> str:
        return self._paths.assets_images_dir(kb_id, document_id)

    def ensure_kb(self, kb_id: int) -> None:
        self._ensure_kb(kb_id)

    def find_document_id_by_name(self, kb_id: int, filename: str) -> int:
        self._ensure_kb(kb_id)
        name = (filename or "").strip()
        if self._repo is None:
            raise RuntimeError("Repository not configured")
        rows = self._repo.list_documents(int(kb_id))
        row = next((r for r in rows if str(r.filename) == name), None)
        if row is None:
            raise RuntimeError(f"文件未在知识库中登记：{name}")
        return int(row.document_id)

    def _ensure_kb(self, kb_id: int) -> None:
        self._paths.ensure_kb_dir(kb_id)
        self._ensure_kb_row(kb_id)

    def _ensure_kb_row(self, kb_id: int) -> None:
        if self._repo is None:
            return
        existing = self._repo.get_kb(int(kb_id))
        if existing is not None:
            return
        created_at = self._paths.kb_created_at_ms(kb_id)
        self._repo.create_kb(
            KnowledgeBaseCreate(
                kb_id=int(kb_id),
                name=f"知识库 {kb_id}",
                description=None,
                created_at_ms=created_at,
                updated_at_ms=created_at,
            )
        )

    def createKnowledgeBase(self, kb_id: int, *, reset_sqlite: bool = True) -> None:
        self._paths.ensure_kb_dir(kb_id)
        if reset_sqlite and self._repo is not None:
            try:
                self._repo.delete_kb(int(kb_id))
            except KnowledgeNotFoundError:
                pass
            self._ensure_kb_row(kb_id)

    def deleteKnowledgeBase(self, kb_id: int) -> None:
        import shutil

        if self._repo is not None:
            try:
                self._repo.delete_kb(int(kb_id))
            except KnowledgeNotFoundError:
                pass
        shutil.rmtree(self._paths.kb_dir(kb_id), ignore_errors=True)

    def deleteDocument(self, kb_id: int, document_id: int) -> bool:
        self._ensure_kb(kb_id)
        if self._repo is None:
            return False
        existing = self._repo.get_document(int(kb_id), int(document_id))
        if existing is None:
            return False
        import shutil

        source_path = getattr(existing, "source_path", None)
        try:
            assets_dir = self._paths.assets_images_dir(int(kb_id), int(document_id))
            shutil.rmtree(assets_dir, ignore_errors=True)
        except Exception:
            pass

        if source_path:
            try:
                if os.path.isfile(source_path):
                    os.remove(source_path)
            except Exception:
                pass

        try:
            name = str(getattr(existing, "name", "") or "").strip()
            if name:
                p = os.path.join(self._paths.uploads_dir(int(kb_id)), name)
                if os.path.isfile(p):
                    os.remove(p)
        except Exception:
            pass
        return True
