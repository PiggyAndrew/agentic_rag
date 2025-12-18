import json
from app.agent import agent as rag_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, AIMessageChunk

def convert_messages(messages):
    """
    将前端消息转换为 LangChain 消息对象用于 Agent 输入
    支持两种输入：
    1) Pydantic BaseModel（fastapi 请求体解析出的对象）
    2) 原始 dict（直接从 JSON 转换而来）
    """
    lc_messages = []
    for msg in messages:
        role = None
        content = None
        if isinstance(msg, dict):
            role = msg.get('role')
            content = msg.get('content')
        else:
            # Pydantic/BaseModel 或具备属性访问的对象
            role = getattr(msg, 'role', None)
            content = getattr(msg, 'content', None)

        if role == "user":
            lc_messages.append(HumanMessage(content=content or ""))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content or ""))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content or ""))
    return lc_messages

async def stream_generator(messages):
    """
    生成符合 Vercel AI SDK Data Stream Protocol 的流式响应
    使用 agent.astream_events 以同时获取 token 增量与中间步骤事件
    参考: https://python.langchain.com/docs/how_to/streaming/
    """
    if not rag_agent:
        # 0: text part
        yield '0:"Error: Agent not initialized"\n'
        return

    inputs = {"messages": convert_messages(messages)}
    
    try:
        if hasattr(rag_agent, "astream_events"):
            emitted_text = False
            async for event in rag_agent.astream_events(inputs, version="v2"):
                event_type = event.get("event")
                name = event.get("name")
                run_id = event.get("run_id")
                data = event.get("data") or {}

                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if isinstance(chunk, AIMessageChunk) and chunk.content:
                        emitted_text = True
                        yield f'0:{json.dumps(chunk.content)}\n'

                elif event_type == "on_chat_model_end":
                    if not emitted_text:
                        text = _extract_text(data.get("output"))
                        if text:
                            emitted_text = True
                            yield f'0:{json.dumps(text)}\n'

                elif event_type == "on_tool_start":
                    tool_input = data.get("input")
                    payload = {
                        "type": "tool_start",
                        "tool": name,
                        "input": _to_jsonable(tool_input),
                        "id": str(run_id),
                    }
                    yield f'8:{json.dumps([payload])}\n'

                elif event_type == "on_tool_end":
                    tool_output = data.get("output")
                    payload = {
                        "type": "tool_end",
                        "tool": name,
                        "output": _to_jsonable(tool_output),
                        "id": str(run_id),
                    }
                    yield f'8:{json.dumps([payload])}\n'

                elif event_type in {"on_tool_error", "on_chain_error", "on_chat_model_error"}:
                    err = data.get("error")
                    yield f'3:{json.dumps(str(err))}\n'
        else:
            async for mode, chunk in rag_agent.astream(inputs, stream_mode=["messages", "updates"]):
                if mode == "messages":
                    msg, _metadata = chunk
                    if isinstance(msg, AIMessageChunk) and msg.content:
                        yield f'0:{json.dumps(msg.content)}\n'

    except Exception as e:
        # 3: error part
        yield f'3:{json.dumps(str(e))}\n'

def _to_jsonable(obj):
    """将任意 Python/SDK 对象转为可 JSON 序列化的数据结构"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    # Pydantic BaseModel
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return _to_jsonable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return _to_jsonable(obj.dict())
        except Exception:
            pass
    # LangChain Message 或通用对象，优先提取 content
    if hasattr(obj, "content"):
        try:
            return _to_jsonable(getattr(obj, "content"))
        except Exception:
            pass
    # 通用对象：展开 __dict__
    if hasattr(obj, "__dict__"):
        try:
            return {k: _to_jsonable(v) for k, v in obj.__dict__.items() if not str(k).startswith("_")}
        except Exception:
            pass
    return str(obj)

def _extract_text(obj):
    """尽可能从对象中提取可展示的文本内容"""
    if obj is None:
        return None
    # 直接字符串
    if isinstance(obj, str):
        return obj
    # LangChain Message 类：尝试 .content
    if hasattr(obj, "content"):
        try:
            c = getattr(obj, "content")
            return c if isinstance(c, str) else json.dumps(_to_jsonable(c))
        except Exception:
            pass
    # dict: 可能有 answer 或 content
    if isinstance(obj, dict):
        for key in ("answer", "content"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        # 如果 output 是包含 messages 的结构
        msgs = obj.get("messages") or obj.get("message")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict) and isinstance(last.get("content"), str):
                return last.get("content")
        # 兜底：如果是未知结构的字典/对象，不要盲目序列化，否则会泄漏内部状态 JSON
        # 除非明确知道这是一个需要展示的对象
        return None
    # pydantic / dataclass：尝试字典化
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            d = obj.model_dump()
            return _extract_text(d)
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            d = obj.dict()
            return _extract_text(d)
        except Exception:
            pass
    return None
