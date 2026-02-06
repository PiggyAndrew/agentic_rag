from typing import List

from backend.modules.kb.domain.models import KnowledgeChunk


class Splitter:
    name: str = "base"

    def split(self, text: str, kb_id: int, file_id: int) -> List[KnowledgeChunk]:
        raise NotImplementedError
