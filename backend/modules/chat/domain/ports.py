from __future__ import annotations

from typing import Any, Protocol

from .models import ChatMessage, ChatSession


class ChatRepositoryPort(Protocol):
    def create_session(self, title: str = "New Chat") -> ChatSession: ...

    def get_sessions(self) -> list[ChatSession]: ...

    def get_session(self, session_id: str) -> ChatSession | None: ...

    def delete_session(self, session_id: str) -> bool: ...

    def get_messages(self, session_id: str) -> list[ChatMessage]: ...

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        citations: list[dict[str, Any]] | None = None,
    ) -> ChatMessage: ...

    def edit_message(self, session_id: str, message_id: int, content: str) -> bool: ...

    def update_session_title(self, session_id: str, title: str) -> bool: ...

