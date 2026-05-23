from __future__ import annotations

import logging
from logging import handlers
import os
from typing import Any, Optional
from backend.modules.config.domain.constants import (
    CONFIG_KEY_LOG_BACKUP_COUNT,
    CONFIG_KEY_LOG_DIR,
    CONFIG_KEY_LOG_FILE,
    CONFIG_KEY_LOG_LEVEL,
    CONFIG_KEY_LOG_LEVEL,
    CONFIG_KEY_LOG_MAX_BYTES,
    CONFIG_KEY_LOG_TO_CONSOLE,
)
from backend.modules.config.infrastructure.env_source import EnvConfigSource


def _get_from_env(key: str) -> Any:
    return EnvConfigSource().get(key)


def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)


def _as_bool(v: Any, default: bool) -> bool:
    if v is None:
        return bool(default)
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _as_str(v: Any, default: str) -> str:
    s = "" if v is None else str(v)
    s = s.strip()
    return s if s else default


def configure_logging(_config: Optional[Any] = None) -> None:
    log_dir = _as_str(_get_from_env(CONFIG_KEY_LOG_DIR), "logs")
    log_file = _as_str(_get_from_env(CONFIG_KEY_LOG_FILE), "app.log")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    root = logging.getLogger()
    level_name = _as_str(_get_from_env(CONFIG_KEY_LOG_LEVEL), "INFO")
    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)

    if root.handlers:
        for h in root.handlers:
            h.setLevel(level)
        root.setLevel(level)
        return

    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    max_bytes = _as_int(_get_from_env(CONFIG_KEY_LOG_MAX_BYTES), 10 * 1024 * 1024)
    backup_count = _as_int(_get_from_env(CONFIG_KEY_LOG_BACKUP_COUNT), 5)
    fh = handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # 专门的错误日志文件
    error_log_path = os.path.join(log_dir, "error.log")
    efh = handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    efh.setLevel(logging.ERROR)
    efh.setFormatter(fmt)
    root.addHandler(efh)

    if _as_bool(_get_from_env(CONFIG_KEY_LOG_TO_CONSOLE), True):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        root.addHandler(ch)
