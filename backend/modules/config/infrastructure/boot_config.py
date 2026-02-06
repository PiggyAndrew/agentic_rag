from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    development = "development"
    production = "production"


class BootConfig(BaseSettings):
    APP_ENV: AppEnv = AppEnv.development
    KB_SQLITE_URL: str = "sqlite:///data/kb/knowledge.sqlite3"
    KB_SQLITE_ECHO: bool = False
    KB_SQLITE_MIGRATIONS_DIR: str = "backend/database/migrations"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


_boot: Optional[BootConfig] = None


def get_boot_config() -> BootConfig:
    global _boot
    if _boot is None:
        _boot = BootConfig()
    return _boot

