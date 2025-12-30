from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """KB SQLite ORM Base。"""


class KnowledgeBaseORM(Base):
    """知识库元数据表。"""

    __tablename__ = "knowledge_bases"

    kb_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)


class KnowledgeFileORM(Base):
    """知识库文件元数据表（复合主键：kb_id + file_id）。"""

    __tablename__ = "knowledge_files"

    kb_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_bases.kb_id", ondelete="CASCADE"), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    source_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class KnowledgeChunkORM(Base):
    """知识库文件分片表（复合主键：kb_id + file_id + chunk_index）。"""

    __tablename__ = "knowledge_chunks"

    kb_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_bases.kb_id", ondelete="CASCADE"), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
