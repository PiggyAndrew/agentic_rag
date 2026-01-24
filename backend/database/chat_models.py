from __future__ import annotations

from typing import Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ChatBase(DeclarativeBase):
    """Chat SQLite ORM Base."""


class ChatSessionORM(ChatBase):
    """聊天会话表"""
    
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    messages: Mapped[list[ChatMessageORM]] = relationship(
        "ChatMessageORM", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessageORM.created_at_ms"
    )


class ChatMessageORM(ChatBase):
    """聊天消息表"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of citations
    created_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped[ChatSessionORM] = relationship("ChatSessionORM", back_populates="messages")
