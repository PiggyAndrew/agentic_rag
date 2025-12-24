from email import message
import json
import os
import time
from langchain.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage

def convert_messages(messages):
    """
    将前端消息转换为 LangChain 消息对象用于 Agent 输入
    仅构造 HumanMessage / AIMessage / SystemMessage
    """
    lc_messages = []
    for msg in messages:
        role = None
        content = None
        if isinstance(msg, dict):
            role = msg.get('role')
            content = msg.get('content')
        else:
            role = getattr(msg, 'role', None)
            content = getattr(msg, 'content', None)

        text = content or ""
        if role == "user":
            lc_messages.append(HumanMessage(content=text))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=text))
        elif role == "system":
            lc_messages.append(SystemMessage(content=text))
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

def _log_event_json(event, path: str = os.path.join("data", "logs", "stream_events.json")):
    """
    追加保存单条事件为 JSON 行，确保可被外部工具读取与分析
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "ts": int(time.time() * 1000),
            "event": event.get("event"),
            "name": event.get("name"),
            "run_id": event.get("run_id"),
            "data": _to_jsonable(event.get("data")),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
async def stream_generator(messages, kb_id=None):
    """
    流式输出 LangChain astream_events 原始事件（逐行 JSON）：
    - 每行一个事件对象：{ event, name, run_id, data }
    - data 字段通过 _to_jsonable 转为可 JSON 的安全结构
    - 前端负责判断与组织展示（文本/工具等）
    """
    os.environ.setdefault("OTEL_PYTHON_DISABLED", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    from app.agent import agent as rag_agent, create_agentic_rag_system
    active_agent = rag_agent
    if kb_id:
        try:
            s = str(kb_id)
            kb_int = int(s[3:]) if s.startswith("kb-") else int(s)
            active_agent = create_agentic_rag_system(kb_int)
        except Exception:
            pass
    if not active_agent:
        yield '0:"Error: Agent not initialized"\n'
        return
    _log_event_json(messages)
    inputs = {"messages": convert_messages(messages)}
    try:
        async for event in active_agent.astream_events(inputs,version="v2"):
            payload = {
                "event": event.get("event"),
                "name": event.get("name"),
                "run_id": event.get("run_id"),
                "data": _to_jsonable(event.get("data")),
            }
            yield json.dumps(payload, ensure_ascii=False) + "\n"
    except Exception as e:
        err_payload = {
            "event": "error",
            "name": "stream_error",
            "run_id": None,
            "data": {"error": _as_text(e)},
        }
        yield json.dumps(err_payload, ensure_ascii=False) + "\n"

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
