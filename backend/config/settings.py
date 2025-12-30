from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
from logging import handlers
import os


class Settings(BaseSettings):
    """应用配置，集中管理环境变量与默认值"""
    DEEPSEEK_API_KEY: str

    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10_485_760
    LOG_BACKUP_COUNT: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取 Settings 单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def configure_logging() -> None:
    """配置全局日志文件与控制台输出"""
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

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)

    root.addHandler(fh)
    root.addHandler(ch)

