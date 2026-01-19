from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from enum import Enum
import json
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from backend.config.settings_constants import (
    ENV_TO_CONFIG_MAP,
)


class AppEnv(str, Enum):
    """环境枚举，用于区分开发与生产模式"""

    development = "development"
    production = "production"


class EmbeddingBackend(str, Enum):
    """嵌入后端枚举，用于选择具体提供者"""

    ollama = "ollama"
    dashscope = "dashscope"


class Settings(BaseSettings):
    """应用配置，集中管理环境变量与默认值"""

    APP_ENV: AppEnv = AppEnv.development
    EMBEDDING_BACKEND: Optional[EmbeddingBackend] = None
    KB_SQLITE_URL: str = "sqlite:///data/kb/knowledge.sqlite3"
    KB_SQLITE_ECHO: bool = False
    KB_SQLITE_MIGRATIONS_DIR: str = "backend/database/migrations"
    RUNTIME_CONFIG: Dict[str, Any] = {}

    # Logging defaults
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"
    LOG_TO_CONSOLE: bool = True
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    # model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    def _load_runtime_config_from_env(self) -> Dict[str, Any]:
        def _get(name: str) -> Any:
            v = os.getenv(name, "")
            return v if v is not None else ""

        kv: Dict[str, Any] = {}
        for env_name, cfg_key in ENV_TO_CONFIG_MAP.items():
            val = _get(env_name)
            if val:
                kv[cfg_key] = val
        return {k: v for k, v in kv.items() if v}

    def _load_runtime_config_from_db(self) -> Dict[str, Any]:
        """生产环境：从 SQLite system_configs 表加载全部键值对"""
        from backend.config.config_models import SystemConfigORM  # 局部导入避免循环

        url = (self.KB_SQLITE_URL or "").strip()
        echo = bool(self.KB_SQLITE_ECHO)
        engine: Engine = create_engine(
            url, echo=echo, connect_args={"check_same_thread": False, "timeout": 30}
        )
        with Session(
            bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
        ) as session:
            rows = session.execute(select(SystemConfigORM)).scalars().all()
        kv: Dict[str, Any] = {}
        for r in rows:
            key = str(r.key or "").strip()
            if not key:
                continue
            val: Any = r.value
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            kv[key] = val
        return kv

    def init_runtime_config(self) -> None:
        """根据环境加载运行时配置字典，供全局统一访问"""
        env = self.APP_ENV or AppEnv.development
        if env == AppEnv.development:
            self.RUNTIME_CONFIG = self._load_runtime_config_from_env()
        else:
            self.RUNTIME_CONFIG = self._load_runtime_config_from_db()

    def get_config(self, key: str, default: Any = None) -> Any:
        """统一入口：获取配置键的值，不关心来源（env/db）

        - key 采用点分命名，如 'llm.baseUrl'
        - 若未初始化，将按需初始化
        """
        if not isinstance(self.RUNTIME_CONFIG, dict) or not self.RUNTIME_CONFIG:
            try:
                self.init_runtime_config()
            except Exception:
                pass
        return self.RUNTIME_CONFIG.get(key, default)


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取 Settings 单例"""
    global _settings
    if _settings is None:
        s = Settings()
        # 初始化运行时配置（不同环境来源不同）
        try:
            s.init_runtime_config()
        except Exception:
            # 初始化失败不影响应用启动，按需延迟加载
            pass
        _settings = s
    return _settings


# 日志配置已迁移至 backend.config.logging.configure_logging


def resolve_embedding_backend() -> EmbeddingBackend:
    """根据 APP_ENV 与显式配置选择嵌入后端

    - 若 EMBEDDING_BACKEND 明确设置则优先使用
    - 否则 production → dashscope，其他 → ollama
    """
    s = get_settings()
    if s.EMBEDDING_BACKEND:
        return s.EMBEDDING_BACKEND
    env = s.APP_ENV or AppEnv.development
    return (
        EmbeddingBackend.dashscope
        if env == AppEnv.production
        else EmbeddingBackend.ollama
    )
