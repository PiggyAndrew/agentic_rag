import base64
import json
import logging
import os
import re
import urllib.request
from typing import Any, List, Union

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from backend.modules.providers.domain.models import ModelCategory
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository

logger = logging.getLogger(__name__)


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
            timeout=self._timeout,
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

        # Handle internal /assets/ paths (virtual paths from frontend/markdown)
        # /assets/{kb_id}/assets/images/{file_id}/{filename} -> data/kb/{kb_id}/assets/images/{file_id}/{filename}
        if p.startswith("/assets/"):
            # project_root/data/kb is the target
            # remove leading /assets/ and join with KB_ROOT_DIR
            from backend.modules.config.infrastructure.boot_config import get_boot_config
            base_dir = get_boot_config().KB_ROOT_DIR
            relative_path = p[len("/assets/") :]
            # Ensure relative path doesn't start with / or \ for os.path.join
            relative_path = relative_path.lstrip("/\\")
            p = os.path.join(base_dir, relative_path)

        with open(p, "rb") as f:
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

    def analyze_image(self, image: dict[str, Any]) -> Any:
        prompt = (
            "请用中文简要描述这张图片的主要内容+文字提取+表格提取,越详细越好。"
            "如果图片包含图表/流程图/架构图，请说明它表达的主题与关键元素。"
            "如果含有表格请提取表格信息，如果视图里有文字请提取文本信息。"
            "不要编造图片中看不到的信息。"
            "只输出严格的 JSON 对象，不要包含多余文字。"
            "输出格式必须为："
            "{\"description\": \"XXXXXX\"}"
        )
        content: list[dict[str, Any]] = []
        try:
            image_path = (image.get("path") or image.get("url") or "").strip()
            if not image_path:
                return {}
            data, mime = self._read_image_bytes(image_path)
            b64 = base64.b64encode(data).decode("utf-8")
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        except Exception as e:
            logger.exception(f"Error preparing image content for vision: {e}")
            raise

        content.append({"type": "text", "text": f"{prompt}\n"})
        msg = HumanMessage(content=content)
        try:
            res_msg = self._llm.invoke([msg])
        except Exception as e:
            logger.exception(f"Error invoking vision LLM: {e}")
            raise
        res_text = getattr(res_msg, "content", res_msg)
        if not res_text:
            return []

        # Clean up possible markdown code blocks
        clean_text = str(res_text).strip()
        if clean_text.startswith("```"):
            # Remove ```json ... ``` or just ``` ... ```
            lines = clean_text.splitlines()
            if len(lines) >= 2:
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

        try:
            return json.loads(clean_text)
        except Exception as e:
            # Try to extract JSON object if the model returned extra text
            try:
                start = clean_text.find('{')
                end = clean_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_obj = clean_text[start : end + 1]
                    return json.loads(json_obj)
            except Exception:
                pass

            logger.exception(f"Failed to parse vision response as JSON: {clean_text}")
            return {"description": clean_text}
