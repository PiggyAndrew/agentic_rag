from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.models import ChatRequest
from backend.protocols.streaming import stream_generator as protocol_stream_generator


router = APIRouter()


@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """聊天接口：支持指定单个参与检索的知识库ID"""
    return StreamingResponse(
        protocol_stream_generator(request.messages, request.kbId),
        media_type="text/plain; charset=utf-8",
    )
