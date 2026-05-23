from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"


class AppEnv(str, Enum):
    development = "development"
    production = "production"


class BootConfig(BaseSettings):
    APP_ENV: AppEnv = AppEnv.development
    KB_ROOT_DIR: str = "data/kb"
    KB_SQLITE_URL: str = "sqlite:///data/kb/knowledge.sqlite3"
    KB_SQLITE_ECHO: bool = False
    KB_SQLITE_MIGRATIONS_DIR: str = "backend/database/migrations"

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_prefix="", extra="ignore")

    @model_validator(mode="after")
    def _normalize_paths(self) -> "BootConfig":
        self.KB_ROOT_DIR = _resolve_repo_path(self.KB_ROOT_DIR)
        self.KB_SQLITE_URL = _resolve_sqlite_url(self.KB_SQLITE_URL)
        self.KB_SQLITE_MIGRATIONS_DIR = _resolve_repo_path(self.KB_SQLITE_MIGRATIONS_DIR)
        return self


def _resolve_repo_path(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return str(REPO_ROOT)
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return str(path.resolve())


def _resolve_sqlite_url(value: str) -> str:
    raw = (value or "").strip()
    prefix = "sqlite:///"
    if not raw.startswith(prefix):
        return raw
    file_part = raw[len(prefix) :]
    if not file_part:
        return raw
    path = Path(file_part)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return prefix + path.resolve().as_posix()


_boot: Optional[BootConfig] = None


def get_boot_config() -> BootConfig:
    global _boot
    if _boot is None:
        _boot = BootConfig()
    return _boot
