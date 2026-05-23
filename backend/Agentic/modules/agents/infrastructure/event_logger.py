from __future__ import annotations

import json
import os
import time


def to_jsonable(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return to_jsonable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return to_jsonable(obj.dict())
        except Exception:
            pass
    if hasattr(obj, "content"):
        try:
            return to_jsonable(getattr(obj, "content"))
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {k: to_jsonable(v) for k, v in obj.__dict__.items() if not str(k).startswith("_")}
        except Exception:
            pass
    return str(obj)


def log_stream_event_json(event, *, path: str = os.path.join("data", "logs", "stream_events.json")) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "ts": int(time.time() * 1000),
            "event": event.get("event"),
            "name": event.get("name"),
            "run_id": event.get("run_id"),
            "data": to_jsonable(event.get("data")),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
