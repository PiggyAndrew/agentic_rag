from __future__ import annotations

from typing import Any, Dict, Optional


async def test_chat_completions(
    *,
    base_url: str,
    api_key: str = "",
    model: str,
    timeout_s: float = 10.0,
) -> Dict[str, Any]:
    import httpx

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": [{"role": "user", "content": "Hello, are you working?"}], "max_tokens": 5}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, json=payload, headers=headers)
        content_type = (resp.headers.get("content-type") or "").lower()
        details: Optional[Any] = None
        if "application/json" in content_type:
            try:
                details = resp.json()
            except Exception:
                details = resp.text
        else:
            details = resp.text

    return {"status_code": int(resp.status_code), "details": details}

