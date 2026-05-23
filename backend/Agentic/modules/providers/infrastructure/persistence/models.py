from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ProvidersBase(DeclarativeBase):
    pass


class LLMProviderORM(ProvidersBase):
    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Integer, default=1)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)

