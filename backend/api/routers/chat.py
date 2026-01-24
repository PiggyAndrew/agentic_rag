import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.api.models import ChatRequest
from backend.protocols.streaming import stream_generator as protocol_stream_generator
from backend.database.chat_service import ChatService


router = APIRouter()


async def chat_stream_wrapper(generator, session_id: str, user_content: str, skip_save_user: bool):
    chat_service = ChatService()
    
    # Save user message
    if session_id and not skip_save_user:
        chat_service.add_message(session_id, "user", user_content)

    full_response = []
    citations = []
    
    async for chunk in generator:
        yield chunk
        if session_id:
            try:
                # Chunk is a JSON string line
                data = json.loads(chunk)
                event = data.get("event")
                # Accumulate content from on_chat_model_stream
                if event == "on_chat_model_stream":
                    content = data.get("data", {}).get("chunk", {}).get("content", "")
                    if content:
                        full_response.append(content)
                elif event == "on_tool_end":
                    name = data.get("name")
                    if name in ["read_file_chunks", "read_file_chunks_multi"]:
                        output = data.get("data", {}).get("output")
                        # Parse output
                        normalized = output
                        if isinstance(output, dict):
                            normalized = output.get("content") or output.get("output") or output
                        
                        raw_data = normalized
                        if isinstance(normalized, str):
                            try:
                                raw_data = json.loads(normalized)
                            except:
                                raw_data = []
                        
                        if isinstance(raw_data, list):
                            for item in raw_data:
                                if isinstance(item, dict):
                                    fid = item.get("file_id") or item.get("fileId")
                                    idx = item.get("chunk_index") or item.get("chunkIndex")
                                    if fid is not None and idx is not None:
                                        citations.append({
                                            "file_id": int(fid),
                                            "chunk_index": int(idx),
                                            "filename": str(item.get("filename", "unknown")),
                                            "content": str(item.get("content", "")),
                                            "metadata": item.get("metadata")
                                        })
            except Exception:
                pass
    
    # Save assistant message
    if session_id and full_response:
        chat_service.add_message(session_id, "assistant", "".join(full_response), citations=citations if citations else None)


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
    
    generator = protocol_stream_generator(request.messages, request.kbId, llm_config=llm_config)
    
    # Get user content from the last message
    user_content = ""
    if request.messages:
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_content = msg.content
                break

    return StreamingResponse(
        chat_stream_wrapper(generator, request.sessionId, user_content, bool(request.skipSaveUser)),
        media_type="text/plain; charset=utf-8",
    )
