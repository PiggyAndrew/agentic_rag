from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，集中管理环境变量与默认值"""
    DEEPSEEK_API_KEY: str = ""

    KB_SQLITE_URL: str = "sqlite:///data/kb/knowledge.sqlite3"
    KB_SQLITE_ECHO: bool = False
    KB_SQLITE_MIGRATIONS_DIR: str = "backend/database/migrations"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取 Settings 单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

