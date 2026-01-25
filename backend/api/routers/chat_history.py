from fastapi import APIRouter
from typing import List
import json

from backend.api.models import ApiResponse, ChatSession, ChatMessageResponse, ChatMessageEditRequest
from backend.database.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()

@router.get("/sessions", response_model=ApiResponse)
async def list_sessions():
    sessions = chat_service.get_sessions()
    data = [
        ChatSession(
            id=s.id,
            title=s.title,
            createdAt=s.created_at_ms,
            updatedAt=s.updated_at_ms
        ) for s in sessions
    ]
    return ApiResponse(ok=True, data=data)

@router.post("/sessions", response_model=ApiResponse)
async def create_session(title: str = "New Chat"):
    session = chat_service.create_session(title)
    data = ChatSession(
        id=session.id,
        title=session.title,
        createdAt=session.created_at_ms,
        updatedAt=session.updated_at_ms
    )
    return ApiResponse(ok=True, data=data)

@router.delete("/sessions/{session_id}", response_model=ApiResponse)
async def delete_session(session_id: str):
    success = chat_service.delete_session(session_id)
    if not success:
        return ApiResponse(ok=False, error={"code": 404, "message": "Session not found"})
    return ApiResponse(ok=True)

@router.get("/sessions/{session_id}/messages", response_model=ApiResponse)
async def get_messages(session_id: str):
    messages = chat_service.get_messages(session_id)
    data = []
    for m in messages:
        citations = None
        if m.citations:
            try:
                citations = json.loads(m.citations)
            except:
                pass
        data.append(ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=citations,
            createdAt=m.created_at_ms
        ))
    return ApiResponse(ok=True, data=data)


@router.put("/sessions/{session_id}/messages/{message_id}", response_model=ApiResponse)
async def edit_message(session_id: str, message_id: int, payload: ChatMessageEditRequest):
    content = (payload.content or "").strip()
    if not content:
        return ApiResponse(ok=False, error={"code": 400, "message": "content 不能为空"})
    success = chat_service.edit_message(session_id, message_id, content)
    if not success:
        return ApiResponse(ok=False, error={"code": 404, "message": "Message not found"})
    return ApiResponse(ok=True, data={"ok": True})


@router.put("/sessions/{session_id}", response_model=ApiResponse)
async def update_session(session_id: str, title: str = ""):
    """更新会话标题"""
    title = (title or "").strip()
    if not title:
        return ApiResponse(ok=False, error={"code": 400, "message": "title 不能为空"})
    success = chat_service.update_session_title(session_id, title)
    if not success:
        return ApiResponse(ok=False, error={"code": 404, "message": "Session not found"})
    session = chat_service.get_session(session_id)
    if session:
        data = ChatSession(
            id=session.id,
            title=session.title,
            createdAt=session.created_at_ms,
            updatedAt=session.updated_at_ms
        )
        return ApiResponse(ok=True, data=data)
    return ApiResponse(ok=False, error={"code": 404, "message": "Session not found"})
