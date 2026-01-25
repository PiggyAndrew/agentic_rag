from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ChunkMetadata:
    """片段元数据：包含用于定位引用的额外信息

    支持的字段：
    - line_start: 片段起始行号（从1开始）
    - line_end: 片段结束行号
    - page: 页码（对于PDF）
    - heading_path: 章节路径数组
    - heading_number: 章节编号
    - heading_title: 章节标题
    - custom: 自定义数据（如表格位置等）
    """
    data: Dict[str, Any]

    @property
    def line_start(self) -> Optional[int]:
        """片段起始行号（从1开始）"""
        return self.data.get("line_start")

    @property
    def line_end(self) -> Optional[int]:
        """片段结束行号"""
        return self.data.get("line_end")

    @property
    def page(self) -> Optional[int]:
        """页码（主要用于PDF）"""
        return self.data.get("page")

    @property
    def heading_path(self) -> Optional[List[Dict[str, Any]]]:
        """章节路径：[{"number": "1", "title": "Introduction"}, ...]"""
        return self.data.get("heading_path")

    @property
    def heading_number(self) -> Optional[str]:
        """章节编号（如 "1.1.1"）"""
        return self.data.get("heading_number")

    @property
    def heading_title(self) -> Optional[str]:
        """章节标题"""
        return self.data.get("heading_title")

    @classmethod
    def coerce(cls, value: Any) -> Optional[ChunkMetadata]:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(data=value)
        return cls(data={"value": value})

