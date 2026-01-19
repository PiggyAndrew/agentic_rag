import os
import json
import base64
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage
from typing import Any, List, Union

class OllamaVisionAgent:
    def __init__(self, base_url: str | None = None, model_name: str | None = None, timeout: int = 60):
        settings = get_settings()
        self._base_url = base_url or settings.get_ollama_base_url("ollama.baseUrl")
        self._model_name = model_name or settings.get_ollama_vision_model("ollama.visionModel")
        self._timeout = timeout
        self._llm = ChatOllama(base_url=self._base_url, model=self._model_name)

    def _guess_mime(self, path: str) -> str:
        p = (path or "").lower()
        if p.endswith(".png"):
            return "image/png"
        if p.endswith(".jpg") or p.endswith(".jpeg"):
            return "image/jpeg"
        if p.endswith(".webp"):
            return "image/webp"
        return "image/png"

    def invoke(self, messages: List[Union[HumanMessage, Any, dict]]) -> dict:
        try:
            res_msg = self._llm.invoke(messages)
        except Exception as e:
            return {"error": str(e), "model": self._model_name, "base_url": self._base_url}
        res_text = getattr(res_msg, "content", "") or ""
        return {
            "model": self._model_name,
            "content": res_text,
            "raw": json.loads(json.dumps(getattr(res_msg, "__dict__", {}), default=str)),
        }

    def analyze_image(self, image_path: str, prompt: str) -> dict:
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except Exception as e:
            return {"error": str(e), "image_path": image_path}
        try:
            mime = self._guess_mime(image_path)
            content = [
                {"type": "text", "text": prompt+"图片名称：Model Division in Floor Level"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]
            msg = HumanMessage(content=content)
            res_msg = self._llm.invoke([msg])
        except Exception as e:
            return {"error": str(e), "image_path": image_path, "model": self._model_name}
        res_text = getattr(res_msg, "content", "") or ""
        return {
            "model": self._model_name,
            "prompt": prompt,
            "image_path": image_path,
            "response": res_text,
            "raw": json.loads(json.dumps(getattr(res_msg, "__dict__", {}), default=str)),
        }

def create_vision_agent() -> OllamaVisionAgent:
    return OllamaVisionAgent()
