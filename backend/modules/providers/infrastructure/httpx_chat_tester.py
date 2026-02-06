from __future__ import annotations

from typing import Any

from backend.modules.providers.domain.ports import ChatCompletionsTesterPort


class HttpxChatCompletionsTester(ChatCompletionsTesterPort):
    async def test_chat_completions(self, *, base_url: str, api_key: str, model: str, timeout_s: float) -> dict[str, Any]:
        import httpx

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"model": model, "messages": [{"role": "user", "content": "Hello, are you working?"}], "max_tokens": 5}
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json=payload, headers=headers)
            content_type = (resp.headers.get("content-type") or "").lower()
            details: Any = None
            if "application/json" in content_type:
                try:
                    details = resp.json()
                except Exception:
                    details = resp.text
            else:
                details = resp.text

        return {"status_code": int(resp.status_code), "details": details}

