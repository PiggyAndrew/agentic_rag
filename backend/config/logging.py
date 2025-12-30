import logging
from logging import handlers
import os
from typing import Optional
from backend.config.settings import get_settings


def _truthy(s: Optional[str]) -> bool:
    return str(s or "").lower() in {"1", "true", "yes"}


def configure_logging() -> None:
    """初始化全局日志配置（文件滚动 + 可选控制台输出）

    - 文件输出位置由 Settings.LOG_DIR / LOG_FILE 控制，采用 RotatingFileHandler
    - 控制台输出由环境变量 LOG_TO_CONSOLE 控制（默认开启）
    - 日志级别由 Settings.LOG_LEVEL 控制
    """
    s = get_settings()
    os.makedirs(s.LOG_DIR, exist_ok=True)
    log_path = os.path.join(s.LOG_DIR, s.LOG_FILE)

    root = logging.getLogger()
    level = getattr(logging, (s.LOG_LEVEL or "INFO").upper(), logging.INFO)

    if root.handlers:
        for h in root.handlers:
            h.setLevel(level)
        root.setLevel(level)
        return

    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    fh = handlers.RotatingFileHandler(
        log_path,
        maxBytes=int(s.LOG_MAX_BYTES),
        backupCount=int(s.LOG_BACKUP_COUNT),
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    if _truthy(os.getenv("LOG_TO_CONSOLE", "1")):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        root.addHandler(ch)

