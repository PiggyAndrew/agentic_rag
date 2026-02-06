import base64
import json
import os
import re
import urllib.request
from typing import Any, List, Union

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from backend.modules.providers.domain.models import ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository


class AliyunDashScopeVisionAgent:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model_name: str | None = None, timeout: int = 60):
        repo = LLMConfigRepository()
        p = repo.get_default_by_category(ModelCategory.vll.value)
        self._base_url = (base_url or (p.base_url if p else None) or (os.getenv("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1")).strip()
        self._api_key = (api_key or (p.api_key if p else None) or (os.getenv("DASHSCOPE_API_KEY") or "")).strip()
        self._model_name = (model_name or (p.model_name if p else None) or (os.getenv("VLL_MODEL") or "")).strip()
        self._timeout = timeout
        self._llm = ChatOpenAI(
            temperature=0,
            max_retries=3,
            base_url=self._base_url,
            model=self._model_name,
            api_key=self._api_key,
        )

    def _read_image_bytes(self, path_or_url: Any) -> tuple[bytes, str]:
        p = (str(path_or_url) if path_or_url is not None else "").strip()
        if not p:
            raise ValueError("image path is empty")
        if re.match(r"^https?://", p, flags=re.I):
            req = urllib.request.Request(
                p,
                headers={
                    "User-Agent": "agentic-rag/1.0",
                    "Accept": "image/*,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = resp.read()
                ct = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            mime = ct if ct.startswith("image/") else self._guess_mime(p)
            return data, mime
        with open(path_or_url, "rb") as f:
            data = f.read()
        return data, self._guess_mime(p)

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

    def analyze_image(self, images: list[dict[str, Any]]) -> Any:
        prompt = (
            "请用中文简要描述所有图片的主要内容（1-2 句话）。"
            "如果是表格/图表/流程图/架构图，请说明它表达的主题与关键元素。"
            "不要编造图片中看不到的信息。"
            "只输出严格的 JSON，不要包含多余文字。"
            "输出为 JSON 数组，数组长度必须等于输入图片数量，且必须逐一对应每张图片。"
            "每个元素必须包含：\"index\"（对应输入图片的 index属性）与 \"description\"（描述文本）。"
            "示例（有n张图）："
            "["
                "{\"index\":0, \"description\": \"XXXXXX\"},"
            "]"
        )
        content: list[dict[str, Any]] = []
        try:
            for it in images:
                image_path = (it.get("path") or it.get("url") or "").strip()
                if not image_path:
                    continue
                data, mime = self._read_image_bytes(image_path)
                b64 = base64.b64encode(data).decode("utf-8")
                content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        except Exception as e:
            return {"error": str(e)}
        content.append({"type": "text", "text": f"{prompt}\n"})
        msg = HumanMessage(content=content)
        try:
            res_msg = self._llm.invoke([msg])
        except Exception as e:
            return {"error": str(e)}
        res_text = getattr(res_msg, "content", res_msg)
        try:
            return json.loads(res_text)
        except Exception:
            return []
