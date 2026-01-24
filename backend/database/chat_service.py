import time
import uuid
import json
from typing import List, Optional, Dict, Any

from sqlalchemy import select, delete

from backend.database.chat_models import ChatSessionORM, ChatMessageORM
from backend.database.sqlite import get_default_sqlite_manager


class ChatService:
    def create_session(self, title: str = "New Chat") -> ChatSessionORM:
        with get_default_sqlite_manager().session_scope() as session:
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
            return chat_session

    def get_sessions(self) -> List[ChatSessionORM]:
        with get_default_sqlite_manager().session_scope() as session:
            stmt = select(ChatSessionORM).order_by(ChatSessionORM.updated_at_ms.desc())
            return list(session.scalars(stmt).all())

    def get_session(self, session_id: str) -> Optional[ChatSessionORM]:
        with get_default_sqlite_manager().session_scope() as session:
            return session.get(ChatSessionORM, session_id)

    def delete_session(self, session_id: str) -> bool:
        with get_default_sqlite_manager().session_scope() as session:
            chat_session = session.get(ChatSessionORM, session_id)
            if chat_session:
                session.delete(chat_session)
                return True
            return False

    def get_messages(self, session_id: str) -> List[ChatMessageORM]:
        with get_default_sqlite_manager().session_scope() as session:
            stmt = select(ChatMessageORM).where(ChatMessageORM.session_id == session_id).order_by(ChatMessageORM.created_at_ms)
            return list(session.scalars(stmt).all())

    def add_message(self, session_id: str, role: str, content: str, citations: Optional[List[Dict[str, Any]]] = None) -> ChatMessageORM:
        with get_default_sqlite_manager().session_scope() as session:
            now = int(time.time() * 1000)
            citations_str = json.dumps(citations) if citations else None
            message = ChatMessageORM(
                session_id=session_id,
                role=role,
                content=content,
                citations=citations_str,
                created_at_ms=now,
            )
            session.add(message)
            
            # Update session updated_at
            chat_session = session.get(ChatSessionORM, session_id)
            if chat_session:
                chat_session.updated_at_ms = now
            
            session.commit()
            session.refresh(message)
            return message

    def edit_message(self, session_id: str, message_id: int, content: str) -> bool:
        with get_default_sqlite_manager().session_scope() as session:
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
