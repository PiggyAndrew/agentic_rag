import logging
from logging import handlers
import os
from typing import Optional
from backend.config.settings import get_settings
from backend.config.settings_constants import (
    CONFIG_KEY_LOG_DIR,
    CONFIG_KEY_LOG_FILE,
    CONFIG_KEY_LOG_LEVEL,
    CONFIG_KEY_LOG_TO_CONSOLE,
    CONFIG_KEY_LOG_MAX_BYTES,
    CONFIG_KEY_LOG_BACKUP_COUNT,
)


def _truthy(s: Optional[str]) -> bool:
    return str(s or "").lower() in {"1", "true", "yes"}


def configure_logging() -> None:
    """初始化全局日志配置（文件滚动 + 可选控制台输出）

    - 文件输出位置由 Settings.LOG_DIR / LOG_FILE 控制，采用 RotatingFileHandler
    - 控制台输出由环境变量 LOG_TO_CONSOLE 控制（默认开启）
    - 日志级别由 Settings.LOG_LEVEL 控制
    """
    s = get_settings()
    log_dir = str(s.get_config(CONFIG_KEY_LOG_DIR) )
    log_file = str(s.get_config(CONFIG_KEY_LOG_FILE))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    root = logging.getLogger()
    level_name = str(s.get_config(CONFIG_KEY_LOG_LEVEL, s.LOG_LEVEL) or s.LOG_LEVEL)
    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)

    if root.handlers:
        for h in root.handlers:
            h.setLevel(level)
        root.setLevel(level)
        return

    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    max_bytes = int(s.get_config(CONFIG_KEY_LOG_MAX_BYTES, s.LOG_MAX_BYTES) or s.LOG_MAX_BYTES)
    backup_count = int(s.get_config(CONFIG_KEY_LOG_BACKUP_COUNT, s.LOG_BACKUP_COUNT) or s.LOG_BACKUP_COUNT)
    fh = handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    to_console_raw = s.get_config(CONFIG_KEY_LOG_TO_CONSOLE, os.getenv("LOG_TO_CONSOLE", "1"))
    if _truthy(str(to_console_raw)):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        root.addHandler(ch)

