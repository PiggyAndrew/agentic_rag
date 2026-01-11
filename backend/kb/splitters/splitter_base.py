from typing import List, Dict, Any
from backend.kb.types.chunk import KnowledgeChunk


class Splitter:
    """抽象拆分器接口：返回标准片段字典列表。

    片段字典结构：
    {
      "content": str,
      "metadata": {
         "number": str,
         "title": str,
         "path": list[ {"number": str, "title": str} ]
      }
    }
    """

    name: str = "base"

    def split(self, text: str, kb_id: int, file_id: int) -> List[KnowledgeChunk]:  # pragma: no cover - interface
        raise NotImplementedError
