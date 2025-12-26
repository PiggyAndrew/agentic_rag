import json
import urllib.request


def post_json(url: str, payload: dict) -> tuple[int, str]:
    """发送 JSON POST 请求并返回 (status, body)"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            return status, body
    except Exception as e:
        return 0, str(e)


def test_chat_stream_basic():
    """验证 /api/chat 流式接口返回逐行 JSON 且包含 event 字段"""
    status, body = post_json("http://127.0.0.1:8000/api/chat", {
        "messages": [{"role": "user", "content": "你好"}],
    })
    assert status == 200, f"unexpected status: {status}, body: {body}"
    lines = [l for l in body.splitlines() if l.strip()]
    assert len(lines) >= 1
    first = json.loads(lines[0])
    assert isinstance(first, dict) and "event" in first

