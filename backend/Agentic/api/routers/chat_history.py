from fastapi import APIRouter, Depends, HTTPException
from typing import List
from backend.api.models import ApiResponse, ChatSession, ChatMessageResponse, ChatMessageEditRequest, ChatSessionCreateRequest, ChatSessionUpdateRequest
from backend.api.deps import get_chat_usecase
from backend.modules.chat.application.usecase import ChatUseCase

router = APIRouter()

@router.get("/sessions", response_model=ApiResponse)
async def list_sessions(chat: ChatUseCase = Depends(get_chat_usecase)):
    sessions = chat.get_sessions()
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
async def create_session(payload: ChatSessionCreateRequest, chat: ChatUseCase = Depends(get_chat_usecase)):
    title = (payload.title or "").strip() or "New Chat"
    session = chat.create_session(title)
    data = ChatSession(
        id=session.id,
        title=session.title,
        createdAt=session.created_at_ms,
        updatedAt=session.updated_at_ms
    )
    return ApiResponse(ok=True, data=data)

@router.delete("/sessions/{session_id}", response_model=ApiResponse)
async def delete_session(session_id: str, chat: ChatUseCase = Depends(get_chat_usecase)):
    success = chat.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return ApiResponse(ok=True)

@router.get("/sessions/{session_id}/messages", response_model=ApiResponse)
async def get_messages(session_id: str, chat: ChatUseCase = Depends(get_chat_usecase)):
    messages = chat.get_messages(session_id)
    data = []
    for m in messages:
        data.append(ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=m.citations,
            createdAt=m.created_at_ms
        ))
    return ApiResponse(ok=True, data=data)


@router.put("/sessions/{session_id}/messages/{message_id}", response_model=ApiResponse)
async def edit_message(
    session_id: str,
    message_id: int,
    payload: ChatMessageEditRequest,
    chat: ChatUseCase = Depends(get_chat_usecase),
):
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content 不能为空")
    success = chat.edit_message(session_id, message_id, content)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    return ApiResponse(ok=True, data={"ok": True})


@router.put("/sessions/{session_id}", response_model=ApiResponse)
async def update_session(session_id: str, payload: ChatSessionUpdateRequest, chat: ChatUseCase = Depends(get_chat_usecase)):
    """更新会话标题"""
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title 不能为空")
    success = chat.update_session_title(session_id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    session = chat.get_session(session_id)
    if session:
        data = ChatSession(
            id=session.id,
            title=session.title,
            createdAt=session.created_at_ms,
            updatedAt=session.updated_at_ms
        )
        return ApiResponse(ok=True, data=data)
    raise HTTPException(status_code=404, detail="Session not found")
