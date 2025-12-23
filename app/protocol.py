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

def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                t = item.get("text")
                if isinstance(t, str):
                    parts.append(t)
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(value)

def _extract_partial_json_string_field(s: str, field: str) -> str:
    key = f"\"{field}\""
    start = s.find(key)
    if start == -1:
        return ""
    i = start + len(key)
    while i < len(s) and s[i] != ":":
        i += 1
    if i >= len(s):
        return ""
    i += 1
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s) or s[i] != "\"":
        return ""
    i += 1
    out = []
    escaped = False
    while i < len(s):
        ch = s[i]
        if escaped:
            if ch in ("\"", "\\", "/"):
                out.append(ch)
                escaped = False
                i += 1
                continue
            if ch == "n":
                out.append("\n")
                escaped = False
                i += 1
                continue
            if ch == "r":
                out.append("\r")
                escaped = False
                i += 1
                continue
            if ch == "t":
                out.append("\t")
                escaped = False
                i += 1
                continue
            if ch == "b":
                out.append("\b")
                escaped = False
                i += 1
                continue
            if ch == "f":
                out.append("\f")
                escaped = False
                i += 1
                continue
            if ch == "u":
                if i + 4 < len(s):
                    hexpart = s[i + 1 : i + 5]
                    try:
                        out.append(chr(int(hexpart, 16)))
                        escaped = False
                        i += 5
                        continue
                    except Exception:
                        return "".join(out)
                break
            out.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\":
            escaped = True
            i += 1
            continue
        if ch == "\"":
            break
        out.append(ch)
        i += 1
    return "".join(out)

async def stream_generator(messages):
    """
    生成符合 Vercel AI SDK Data Stream Protocol 的流式响应
    使用 agent.astream_events (v2)
    参考: https://python.langchain.com/docs/how_to/streaming/
    """
    if not rag_agent:
        yield '0:"Error: Agent not initialized"\n'
        return

    inputs = {"messages": convert_messages(messages)}
    
    try:
        saw_text = False
        emitted_final = False
        tool_call_names = {}
        tool_call_args = {}
        answer_emitted = {}
        async for event in rag_agent.astream_events(inputs, version="v2"):
            kind = event["event"]
            
            # 1. 文本流 (Chat Model Streaming)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if isinstance(chunk, AIMessageChunk):
                    tccs = getattr(chunk, "tool_call_chunks", None) or []
                    for tcc in tccs:
                        idx = tcc.get("index")
                        if idx is None:
                            continue
                        name = tcc.get("name")
                        if name:
                            tool_call_names[idx] = name
                        args_piece = tcc.get("args") or ""
                        if not args_piece:
                            continue
                        tool_call_args[idx] = tool_call_args.get(idx, "") + args_piece
                        if tool_call_names.get(idx) == "RAGAnswer":
                            current = _extract_partial_json_string_field(tool_call_args[idx], "answer")
                            prev = answer_emitted.get(idx, 0)
                            if len(current) > prev:
                                delta = current[prev:]
                                answer_emitted[idx] = len(current)
                                saw_text = True
                                yield f'0:{json.dumps(delta)}\n'
            elif kind == "on_llm_new_token":
                token = event.get("data", {}).get("token")
                if token:
                    saw_text = True
                    yield f'0:{json.dumps(_as_text(token))}\n'
            elif kind in ("on_chat_model_end", "on_llm_end"):
                output = event.get("data", {}).get("output")
                content = getattr(output, "content", None)
                if content:
                    saw_text = True
                    yield f'0:{json.dumps(_as_text(content))}\n'
            elif kind in ("on_chain_end", "on_agent_finish"):
                if emitted_final:
                    continue
                if saw_text:
                    continue
                data = event.get("data", {}) or {}
                candidate = data.get("output") or data.get("return_values") or data
                if kind == "on_chain_end" and isinstance(candidate, dict) and "structured_response" not in candidate:
                    continue
                text = _extract_text(candidate)
                if text:
                    emitted_final = True
                    saw_text = True
                    yield f'0:{json.dumps(text)}\n'
            
            # 2. 工具调用开始 (Tool Start)
            elif kind == "on_tool_start":
                # 过滤掉不需要展示的内部工具
                if event["name"].startswith("_"):
                    continue
                
                # 特殊处理：如果是最终答案的结构化输出（通常包含 answer 字段）
                # 我们将其作为文本直接输出，而不是显示为工具调用
                inputs_data = event["data"].get("input") or {}
                if "answer" in inputs_data:
                    yield f'0:{json.dumps(inputs_data["answer"])}\n'
                else:
                    data = {
                        "type": "tool_start",
                        "tool": event["name"],
                        "input": inputs_data,
                        "id": event["run_id"]
                    }
                    yield f'8:{json.dumps([data])}\n'

            # 3. 工具执行结束 (Tool End)
            elif kind == "on_tool_end":
                if event["name"].startswith("_"):
                    continue
                print(event)
                output_jsonable = _to_jsonable(event["data"].get("output"))
                if isinstance(output_jsonable, dict):
                    answer = output_jsonable.get("content")
                    if isinstance(answer, str) and answer:
                        saw_text = True
                        yield f'0:{json.dumps(answer)}\n'

                data = {
                    "type": "tool_end",
                    "tool": event["name"],
                    "output": output_jsonable,
                    "id": event["run_id"]
                }
                yield f'8:{json.dumps([data])}\n'
            elif kind == "on_tool_error":
                if event["name"].startswith("_"):
                    continue
                err = event.get("data", {}).get("error")
                data = {
                    "type": "tool_end",
                    "tool": event["name"],
                    "output": None,
                    "id": event["run_id"],
                    "error": _as_text(err),
                }
                yield f'8:{json.dumps([data])}\n'

    except Exception as e:
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
        if "structured_response" in obj:
            text = _extract_text(obj.get("structured_response"))
            if text:
                return text
        for key in ("answer", "content"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        # 如果 output 是包含 messages 的结构
        msgs = obj.get("messages") or obj.get("message")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict) and isinstance(last.get("content"), str):
                return last.get("content")
            if hasattr(last, "content"):
                try:
                    if isinstance(last, ToolMessage):
                        return None
                    c = getattr(last, "content")
                    return c if isinstance(c, str) else json.dumps(_to_jsonable(c))
                except Exception:
                    pass
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
