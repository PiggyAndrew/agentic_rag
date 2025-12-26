from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class FileMeta:
    id: int
    filename: str
    chunk_count: int
    status: str = "done"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": int(self.id),
            "filename": self.filename,
            "chunk_count": int(self.chunk_count),
            "status": self.status,
        }
