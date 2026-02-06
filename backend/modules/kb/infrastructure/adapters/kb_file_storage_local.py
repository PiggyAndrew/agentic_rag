from __future__ import annotations

import os
from typing import List

from backend.modules.kb.domain.ports import KbFileStoragePort


class LocalKbFileStorage(KbFileStoragePort):
    def __init__(self, *, kb_dir_resolver: object):
        self._kb_dir_resolver = kb_dir_resolver

    def ensure_uploads_dir(self, kb_id: int) -> str:
        kb_dir = getattr(self._kb_dir_resolver, "kb_dir")(int(kb_id))
        uploads_dir = os.path.join(kb_dir, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        return uploads_dir

    def upload_path(self, kb_id: int, filename: str) -> str:
        uploads_dir = self.ensure_uploads_dir(int(kb_id))
        return os.path.join(uploads_dir, filename)

    def write_bytes(self, path: str, data: bytes) -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def list_kb_ids(self, base_dir: str) -> List[int]:
        out: List[int] = []
        if not os.path.exists(base_dir):
            return out
        for name in os.listdir(base_dir):
            try:
                out.append(int(name))
            except Exception:
                continue
        return out

    def kb_created_at_ms(self, kb_dir: str) -> int:
        if os.path.exists(kb_dir):
            return int(os.path.getmtime(kb_dir) * 1000)
        return int(os.path.getmtime(os.path.dirname(kb_dir) or ".") * 1000)
