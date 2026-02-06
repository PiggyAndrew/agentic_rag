from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.api.main import create_app


class ApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(), raise_server_exceptions=False)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_validation_error_is_api_response(self) -> None:
        resp = self.client.post("/api/llm/test", json={"apiKey": "x", "modelName": "m"})
        self.assertEqual(resp.status_code, 422)
        body = resp.json()
        self.assertEqual(body.get("ok"), False)
        self.assertEqual(body.get("error", {}).get("code"), 422)

    def test_http_exception_is_api_response(self) -> None:
        resp = self.client.put("/api/chat/sessions/s1", json={"title": ""})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body.get("ok"), False)
        self.assertEqual(body.get("error", {}).get("code"), 400)


if __name__ == "__main__":
    unittest.main()
