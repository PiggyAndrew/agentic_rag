from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.api.models import ChatRequest
from backend.protocols.streaming import stream_generator as protocol_stream_generator


router = APIRouter()


@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest, raw_request: Request):
    """聊天接口：支持指定单个参与检索的知识库ID"""
    llm_config = {
        "api_key": (raw_request.headers.get("x-llm-api-key") or "").strip(),
        "base_url": (raw_request.headers.get("x-llm-base-url") or "").strip(),
        "model": (raw_request.headers.get("x-llm-model") or "").strip(),
    }
    if not any(llm_config.values()):
        llm_config = None
    return StreamingResponse(
        protocol_stream_generator(request.messages, request.kbId, llm_config=llm_config),
        media_type="text/plain; charset=utf-8",
    )
