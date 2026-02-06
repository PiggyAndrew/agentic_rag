from __future__ import annotations

import json
import time
import uuid
from typing import Any, Optional

from sqlalchemy import delete, select

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.modules.chat.domain.models import ChatMessage, ChatSession
from backend.modules.chat.domain.ports import ChatRepositoryPort
from backend.modules.chat.infrastructure.persistence.models import ChatMessageORM, ChatSessionORM


class ChatService(ChatRepositoryPort):
    def __init__(self, manager: Optional[SqliteSessionManager] = None):
        self._manager = manager or get_default_sqlite_manager()

    @staticmethod
    def _session_from_orm(row: ChatSessionORM) -> ChatSession:
        return ChatSession(
            id=row.id,
            title=row.title,
            created_at_ms=int(row.created_at_ms),
            updated_at_ms=int(row.updated_at_ms),
        )

    @staticmethod
    def _message_from_orm(row: ChatMessageORM) -> ChatMessage:
        citations: list[dict[str, Any]] | None = None
        if row.citations:
            try:
                raw = json.loads(row.citations)
                if isinstance(raw, list):
                    citations = [x for x in raw if isinstance(x, dict)] or None
            except Exception:
                citations = None
        return ChatMessage(
            id=int(row.id),
            session_id=str(row.session_id),
            role=str(row.role),
            content=str(row.content),
            citations=citations,
            created_at_ms=int(row.created_at_ms),
        )

    def create_session(self, title: str = "New Chat") -> ChatSession:
        with self._manager.session_scope() as session:
            now = int(time.time() * 1000)
            chat_session = ChatSessionORM(
                id=str(uuid.uuid4()),
                title=title,
                created_at_ms=now,
                updated_at_ms=now,
            )
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return self._session_from_orm(chat_session)

    def get_sessions(self) -> list[ChatSession]:
        with self._manager.session_scope() as session:
            stmt = select(ChatSessionORM).order_by(ChatSessionORM.updated_at_ms.desc())
            return [self._session_from_orm(x) for x in session.scalars(stmt).all()]

    def get_session(self, session_id: str) -> ChatSession | None:
        with self._manager.session_scope() as session:
            row = session.get(ChatSessionORM, session_id)
            return None if row is None else self._session_from_orm(row)

    def delete_session(self, session_id: str) -> bool:
        with self._manager.session_scope() as session:
            chat_session = session.get(ChatSessionORM, session_id)
            if chat_session:
                session.delete(chat_session)
                return True
            return False

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        with self._manager.session_scope() as session:
            stmt = (
                select(ChatMessageORM)
                .where(ChatMessageORM.session_id == session_id)
                .order_by(ChatMessageORM.created_at_ms)
            )
            return [self._message_from_orm(x) for x in session.scalars(stmt).all()]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        citations: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        with self._manager.session_scope() as session:
            now = int(time.time() * 1000)
            citations_str = json.dumps(citations, ensure_ascii=False) if citations else None
            message = ChatMessageORM(
                session_id=session_id,
                role=role,
                content=content,
                citations=citations_str,
                created_at_ms=now,
            )
            session.add(message)
            chat_session = session.get(ChatSessionORM, session_id)
            if chat_session:
                chat_session.updated_at_ms = now
            session.commit()
            session.refresh(message)
            return self._message_from_orm(message)

    def edit_message(self, session_id: str, message_id: int, content: str) -> bool:
        with self._manager.session_scope() as session:
            message = session.get(ChatMessageORM, message_id)
            if not message or message.session_id != session_id:
                return False
            message.content = content
            session.execute(
                delete(ChatMessageORM).where(
                    ChatMessageORM.session_id == session_id,
                    ChatMessageORM.id > message_id,
                )
            )
            now = int(time.time() * 1000)
            chat_session = session.get(ChatSessionORM, session_id)
            if chat_session:
                chat_session.updated_at_ms = now
            return True

    def update_session_title(self, session_id: str, title: str) -> bool:
        with self._manager.session_scope() as session:
            chat_session = session.get(ChatSessionORM, session_id)
            if not chat_session:
                return False
            chat_session.title = title
            chat_session.updated_at_ms = int(time.time() * 1000)
            return True
