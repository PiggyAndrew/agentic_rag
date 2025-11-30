from typing import List, Dict, Any
from .base import Splitter


class NormalSplitter(Splitter):
    """定长切片拆分器：返回标准片段字典列表。"""

    name = "normal"

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须为正数")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap 必须为非负且小于 chunk_size")
        self.chunk_size = int(chunk_size)
        self.overlap = int(overlap)

    def split(self, text: str) -> List[Dict[str, Any]]:
        text = (text or "").strip()
        chunks: List[Dict[str, Any]] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(start + self.chunk_size, n)
            chunk = text[start:end]
            chunks.append({
                "content": chunk,
                "metadata": {"number": "", "title": "", "path": []},
            })
            if end == n:
                break
            start = end - self.overlap
        return chunks

