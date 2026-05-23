from __future__ import annotations

import os
import time


class KbPaths:
    def __init__(self, base_dir: str):
        self.base_dir = str(base_dir or "data/kb")

    def kb_dir(self, kb_id: int) -> str:
        return os.path.join(self.base_dir, str(int(kb_id)))

    def uploads_dir(self, kb_id: int) -> str:
        return os.path.join(self.kb_dir(kb_id), "uploads")

    def assets_images_dir(self, kb_id: int, document_id: int) -> str:
        return os.path.join(self.kb_dir(kb_id), "assets", "images", str(int(document_id)))

    def ensure_kb_dir(self, kb_id: int) -> str:
        p = self.kb_dir(kb_id)
        os.makedirs(p, exist_ok=True)
        return p

    def kb_created_at_ms(self, kb_id: int) -> int:
        p = self.kb_dir(kb_id)
        if os.path.exists(p):
            try:
                return int(os.path.getmtime(p) * 1000)
            except Exception:
                pass
        return int(time.time() * 1000)
