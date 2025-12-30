from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from enum import Enum


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
    DEEPSEEK_API_KEY: str

    APP_ENV: AppEnv = os.getenv("APP_ENV", AppEnv.development)
    EMBEDDING_BACKEND: EmbeddingBackend | None = None
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
    return EmbeddingBackend.dashscope if env == AppEnv.production else EmbeddingBackend.ollama

