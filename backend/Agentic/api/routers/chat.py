import json
import re
import time
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.api.models import ChatRequest
from backend.modules.agents.application.streaming import stream_generator as protocol_stream_generator
from backend.api.deps import get_chat_usecase, get_kb_usecase, get_provider_service, get_llm_config_from_headers
from backend.modules.chat.application.usecase import ChatUseCase
from backend.modules.kb.application.usecase import KnowledgeBaseUseCase
from backend.modules.providers.application.provider_service import ProviderService

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_thinking_tags(text: str) -> tuple[str, str]:
    """
    从文本中提取 ```` 标签内容
    返回: (thinking_content, remaining_text)
    """
    pattern = r'<think>(.*?)</think>'
    matches = re.findall(pattern, text, re.DOTALL)
    thinking_parts = []
    remaining = text

    for match in matches:
        # 移除匹配的标签，从 remaining 中提取
        remaining = remaining.replace(f'<think>{match}</think>', '', 1)
        thinking_parts.append(match.strip())

    thinking = '\n'.join(thinking_parts) if thinking_parts else None
    return thinking, remaining


async def chat_stream_wrapper(generator, session_id: str, user_content: str, skip_save_user: bool, chat: ChatUseCase):

    # Save user message
    if session_id and not skip_save_user:
        chat.add_message(session_id, "user", user_content)

    full_response = []
    citations = []
    # 记录当前正在处理的工具调用
    active_tools = {}
    # 是否正在流式输出文本
    is_streaming_text = False
    text_buffer = []

    # Reasoning 状态跟踪
    reasoning_buffer = []
    reasoning_start_time = None
    in_reasoning = False

    # 每个reasoning块生成唯一ID
    reasoning_counter = 0
    current_reasoning_id = None

    async for chunk in generator:
        # 先 yield 原始事件
        yield chunk
        if session_id:
            try:
                # Chunk is a JSON string line
                data = json.loads(chunk)
                event = data.get("event")

                if event == "on_chat_model_stream":
                    chunk_data = data.get("data", {}).get("chunk", {})
                    content = chunk_data.get("content", "")

                    if content:
                        # 检查并提取 reasoning 内容
                        thinking, remaining = _extract_thinking_tags(content)

                        if thinking:
                            if not in_reasoning:
                                # 开始新的 reasoning 块
                                in_reasoning = True
                                reasoning_start_time = time.time() * 1000
                                current_reasoning_id = f"reasoning-{reasoning_counter}"
                                reasoning_counter += 1
                                reasoning_buffer = [thinking]
                            else:
                                # 继续 reasoning
                                reasoning_buffer.append(thinking)

                            # 发送 reasoning 流式事件
                            yield _make_reasoning_event(
                                current_reasoning_id,
                                ''.join(reasoning_buffer),
                                reasoning_start_time
                            )
                        elif in_reasoning and not thinking:
                            # Reasoning 结束
                            in_reasoning = False
                            duration = int((time.time() * 1000) - reasoning_start_time)
                            final_reasoning = ''.join(reasoning_buffer)
                            reasoning_buffer = []
                            # 发送最终的 reasoning 事件（带 duration）
                            yield _make_reasoning_event(
                                current_reasoning_id,
                                final_reasoning,
                                reasoning_start_time,
                                duration
                            )

                        if remaining:
                            # 普通文本内容 - 实时流式发送
                            if not is_streaming_text:
                                is_streaming_text = True
                                text_buffer = []
                            text_buffer.append(remaining)
                            full_response.append(remaining)

                            # 实时发送 content_part 事件以支持流式显示
                            current_text = "".join(text_buffer)
                            yield _make_content_part_event("text", current_text)

                elif event == "on_chat_model_end":
                    # 流式结束，发送最终内容

                    # 处理可能残留的 reasoning
                    if in_reasoning and reasoning_buffer:
                        duration = int((time.time() * 1000) - reasoning_start_time)
                        final_reasoning = ''.join(reasoning_buffer)
                        reasoning_buffer = []
                        in_reasoning = False
                        yield _make_reasoning_event(
                            current_reasoning_id,
                            final_reasoning,
                            reasoning_start_time,
                            duration
                        )

                    # 处理文本缓冲区
                    if text_buffer:
                        final_text = "".join(text_buffer)
                        yield _make_content_part_event("text", final_text)
                        text_buffer = []
                        is_streaming_text = False

                elif event == "on_tool_start":
                    name = data.get("name")
                    run_id = data.get("run_id")
                    if name:
                        # 发送 tool-call 事件（call 状态）
                        input_data = data.get("data", {}).get("input", {})
                        yield _make_tool_call_event(run_id, name, input_data, "call")
                        active_tools[run_id] = {
                            "name": name,
                            "args": input_data
                        }

                elif event == "on_tool_end":
                    name = data.get("name")
                    run_id = data.get("run_id")
                    output = data.get("data", {}).get("output")
                    if name:
                        # 发送 tool-call 事件（result 状态）
                        normalized_output = _normalize_tool_output(output)
                        yield _make_tool_call_event(run_id, name, active_tools.get(run_id, {}).get("args", {}), "result", normalized_output)

                        # 解析引用信息
                        if name in ["read_document_chunks", "read_document_chunks_multi"]:
                            raw_data = normalized_output
                            if isinstance(normalized_output, str):
                                try:
                                    raw_data = json.loads(normalized_output)
                                except:
                                    raw_data = []

                            if isinstance(raw_data, list):
                                for item in raw_data:
                                    if isinstance(item, dict):
                                        document_id = item.get("document_id") or item.get("documentId") or item.get("file_id") or item.get("fileId")
                                        chunk_index = item.get("chunk_index") or item.get("chunkIndex")
                                        if document_id is not None and chunk_index is not None:
                                            citations.append({
                                                "document_id": int(document_id),
                                                "chunk_index": int(chunk_index),
                                                "filename": str(item.get("filename", "unknown")),
                                                "content": str(item.get("content", "")),
                                                "metadata": item.get("metadata")
                                            })

                        # 清理已完成的工具
                        if run_id in active_tools:
                            del active_tools[run_id]

                elif event == "on_tool_error":
                    name = data.get("name")
                    run_id = data.get("run_id")
                    error = data.get("data", {}).get("error")
                    if name:
                        # 发送 tool-call 事件（error 状态）
                        yield _make_tool_call_event(run_id, name, active_tools.get(run_id, {}).get("args", {}), "error", error=error)

                        # 清理出错的工具
                        if run_id in active_tools:
                            del active_tools[run_id]

            except Exception as e:
                logger.error("Error in tool execution: %s", e)
                raise

    # 确保发送所有缓冲的 reasoning
    if in_reasoning and reasoning_buffer:
        duration = int((time.time() * 1000) - reasoning_start_time)
        final_reasoning = ''.join(reasoning_buffer)
        reasoning_buffer = []
        in_reasoning = False
        yield _make_reasoning_event(
            current_reasoning_id,
            final_reasoning,
            reasoning_start_time,
            duration
        )

    # 确保发送所有缓冲的文本
    if text_buffer:
        yield _make_content_part_event("text", "".join(text_buffer))
        full_response.extend(text_buffer)

    # Save assistant message
    if session_id and full_response:
        chat.add_message(session_id, "assistant", "".join(full_response), citations=citations if citations else None)


def _normalize_tool_output(output):
    """规范化工具输出"""
    if output is None:
        return None
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        return output.get("content") or output.get("output") or output
    return output


def _make_content_part_event(part_type: str, text: str, duration: int = None) -> str:
    """创建 content_part 事件（符合 AI SDK UIMessage 格式）"""
    import time
    event_data = {
        "event": "content_part",
        "data": {
            "type": part_type,
            "text": text
        }
    }
    # 兼容 AI SDK 格式 - duration 放在顶层而不是 data 中
    if duration is not None:
        event_data["duration"] = duration
    return json.dumps(event_data, ensure_ascii=False) + "\n"


def _make_reasoning_event(reasoning_id: str, text: str, start_time: int, duration: int = None) -> str:
    """创建 reasoning content_part 事件（符合 AI SDK UIMessage 格式）

    Args:
        reasoning_id: reasoning 内容的唯一标识符
        text: reasoning 文本内容
        start_time: reasoning 开始时间（毫秒时间戳）
        duration: reasoning 持续时间（毫秒），可选
    """
    event_data = {
        "event": "content_part",
        "data": {
            "type": "reasoning",
            "reasoningId": reasoning_id,
            "text": text,
            "startTime": start_time
        }
    }
    # duration 放在顶层符合 AI SDK 格式
    if duration is not None:
        event_data["duration"] = duration
    return json.dumps(event_data, ensure_ascii=False) + "\n"


def _make_tool_call_event(tool_call_id: str, tool_name: str, args: dict, state: str, result: str = None, error: str = None) -> str:
    """创建 tool-call content_part 事件（符合 AI SDK UIMessage 格式）

    状态映射到 ToolUIPart 定义：
    - call -> input-available (Running)
    - result -> output-available (Completed)
    - error -> output-error (Error)
    """
    # 映射状态到 ToolUIPart 定义的值
    state_mapping = {
        "call": "input-available",    # Running
        "result": "output-available",  # Completed
        "error": "output-error",      # Error
    }
    mapped_state = state_mapping.get(state, "input-available")

    event_data = {
        "event": "content_part",
        "data": {
            "type": "tool-call",
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "state": mapped_state,
            "args": args
        }
    }
    # result 和 error 放在 data 层级中（与 AI SDK 格式保持一致）
    if result is not None:
        event_data["data"]["result"] = result
    if error is not None:
        event_data["data"]["error"] = error
    return json.dumps(event_data, ensure_ascii=False) + "\n"


@router.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest,
    raw_request: Request,
    chat: ChatUseCase = Depends(get_chat_usecase),
    kb: KnowledgeBaseUseCase = Depends(get_kb_usecase),
    providers: ProviderService = Depends(get_provider_service),
):
    """聊天接口：支持指定单个参与检索的知识库ID"""
    llm_config = get_llm_config_from_headers(raw_request)
    
    generator = protocol_stream_generator(
        request.messages,
        request.kbId,
        llm_config=llm_config,
        kb=kb,
        providers=providers,
        event_logger=getattr(getattr(raw_request, "app", None), "state", None) and getattr(raw_request.app.state, "stream_event_logger", None),
    )
    
    # Get user content from the last message
    user_content = ""
    if request.messages:
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_content = msg.content
                break

    return StreamingResponse(
        chat_stream_wrapper(generator, request.sessionId, user_content, bool(request.skipSaveUser), chat),
        media_type="text/plain; charset=utf-8",
    )
