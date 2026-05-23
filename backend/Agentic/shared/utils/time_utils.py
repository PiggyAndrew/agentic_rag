from __future__ import annotations

from datetime import datetime


def now_ms() -> int:
    """获取当前时间戳（毫秒）"""
    return int(datetime.utcnow().timestamp() * 1000)


def now_iso() -> str:
    """获取当前时间（ISO 格式）"""
    return datetime.utcnow().isoformat()
