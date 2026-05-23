from typing import List

from backend.modules.kb.domain.chunk_models import DocumentChunk


class Splitter:
    name: str = "base"

    def split(self, text: str, kb_id: int, document_id: int) -> List[DocumentChunk]:
        raise NotImplementedError
