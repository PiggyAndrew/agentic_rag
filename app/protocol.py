import json
import os
from app.agent import agent as rag_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, AIMessageChunk
from langchain_core.runnables import RunnableConfig
 
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



def _truncate_text(text: str, max_len: int = 800) -> str:
    """
    截断文本到指定长度，避免将超长内容塞进流式事件导致前端渲染卡顿
    """
    if not text:
        return ""
    t = str(text)
    if max_len <= 0 or len(t) <= max_len:
        return t
    return t[:max_len] + "..."


def _try_parse_json(value):
    """
    尝试将字符串解析为 JSON；失败则返回 None
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _extract_partial_json_string_field(s: str, field: str) -> str:
    """
    从不完整的 JSON 片段字符串中提取指定字段的字符串值（不支持嵌套对象）
    处理常见的转义序列，其中 \\n 会被还原为实际换行符
    """
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
    变更：严格区分模型文本与工具输出，工具输出只通过 data 事件返回，不注入文本消息
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
        citations_map = {}
        recursion_limit = int(os.getenv("AGENT_RECURSION_LIMIT", "80"))
        cfg = RunnableConfig(recursion_limit=recursion_limit)
        async for event in rag_agent.astream_events(inputs, version="v2", config=cfg):
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
                                yield f'0:{json.dumps(delta)}\n'
            elif kind == "on_llm_new_token":
                token = event.get("data", {}).get("token")
                if token:
                    yield f'0:{json.dumps(token)}\n'
            elif kind in ("on_chat_model_end", "on_llm_end"):
                output = event.get("data", {}).get("output")
                content = getattr(output, "content", None)
                if content:
                    yield f'0:{json.dumps(content)}\n'
            # 2. 工具调用开始 (Tool Start)
            elif kind == "on_tool_start":
                # 过滤掉不需要展示的内部工具
                if event["name"].startswith("_"):
                    continue
                
                inputs_data = event["data"].get("input") or {}
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
                output_jsonable = _to_jsonable(event["data"].get("output"))

                data = {
                    "type": "tool_end",
                    "tool": event["name"],
                    "output": output_jsonable,
                    "id": event["run_id"]
                }
                yield f'8:{json.dumps([data])}\n'

                if event["name"] == "read_file_chunks":
                    parsed = _try_parse_json(output_jsonable)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if not isinstance(item, dict):
                                continue
                            fid = item.get("file_id")
                            cidx = item.get("chunk_index")
                            try:
                                fid_int = int(fid)
                                cidx_int = int(cidx)
                            except Exception:
                                continue
                            key = (fid_int, cidx_int)
                            citations_map[key] = {
                                "file_id": fid_int,
                                "chunk_index": cidx_int,
                                "filename": str(item.get("filename") or ""),
                                "content": _truncate_text(item.get("content") or ""),
                            }
                        citations_payload = {
                            "type": "citations",
                            "citations": [citations_map[k] for k in sorted(citations_map.keys())],
                        }
                        yield f'8:{json.dumps([citations_payload], ensure_ascii=False)}\n'
            elif kind == "on_tool_error":
                if event["name"].startswith("_"):
                    continue
                err = event.get("data", {}).get("error")
                data = {
                    "type": "tool_end",
                    "tool": event["name"],
                    "output": None,
                    "id": event["run_id"],
                    "error": err,
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

