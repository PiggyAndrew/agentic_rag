import json
import urllib.request


def get(url: str) -> tuple[int, str]:
    """执行简单的 HTTP GET 请求并返回 (status, body)"""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            return status, body
    except Exception as e:
        return 0, str(e)


def test_kb_list_endpoint():
    """验证 /api/kb 接口返回有效 JSON 数组结构"""
    status, body = get("http://127.0.0.1:8000/api/kb")
    assert status == 200, f"unexpected status: {status}, body: {body}"
    data = json.loads(body)
    assert isinstance(data, list)
    for item in data:
        assert isinstance(item, dict)
        assert "id" in item and "name" in item

