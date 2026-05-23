from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.modules.chat.domain.models import ChatMessage, ChatSession
from backend.modules.chat.domain.ports import ChatRepositoryPort


@dataclass(frozen=True, slots=True)
class ChatUseCase:
    repo: ChatRepositoryPort

    def create_session(self, title: str = "New Chat") -> ChatSession:
        return self.repo.create_session(title)

    def get_sessions(self) -> list[ChatSession]:
        return self.repo.get_sessions()

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.repo.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self.repo.delete_session(session_id)

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        return self.repo.get_messages(session_id)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        citations: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        return self.repo.add_message(session_id, role, content, citations=citations)

    def edit_message(self, session_id: str, message_id: int, content: str) -> bool:
        return self.repo.edit_message(session_id, message_id, content)

    def update_session_title(self, session_id: str, title: str) -> bool:
        return self.repo.update_session_title(session_id, title)
