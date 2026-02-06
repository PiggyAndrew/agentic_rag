import json
import os

from langchain.messages import AIMessage, HumanMessage, SystemMessage


def convert_messages(messages):
    lc_messages = []
    for msg in messages:
        role = None
        content = None
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")
        else:
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", None)

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
    return str(value)


def _to_jsonable(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
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
    if hasattr(obj, "content"):
        try:
            return _to_jsonable(getattr(obj, "content"))
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {k: _to_jsonable(v) for k, v in obj.__dict__.items() if not str(k).startswith("_")}
        except Exception:
            pass
    return str(obj)


async def stream_generator(messages, kb_id=None, *, llm_config=None, kb=None, providers=None, event_logger=None):
    os.environ.setdefault("OTEL_PYTHON_DISABLED", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

    from backend.modules.agents.application.rag_agent import create_agentic_rag_system
    kb_int = None
    if kb_id:
        try:
            s = str(kb_id)
            kb_int = int(s[3:]) if s.startswith("kb-") else int(s)
        except Exception:
            kb_int = None

    if kb is None:
        yield '0:"Error: KB usecase not provided"\n'
        return

    target_kb = kb_int if kb_int is not None else 1
    try:
        active_agent = create_agentic_rag_system(
            target_kb,
            kb=kb,
            providers=providers,
            llm_config=llm_config,
        )
    except Exception:
        active_agent = None

    if not active_agent:
        yield '0:"Error: Agent not initialized"\n'
        return

    inputs = {"messages": convert_messages(messages)}
    try:
        async for event in active_agent.astream_events(inputs):
            if callable(event_logger):
                try:
                    event_logger(event)
                except Exception:
                    pass
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
