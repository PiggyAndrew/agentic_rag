from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv


def get_deepseek_chat_llm(*, max_retries: int = 2) -> Optional[object]:
    load_dotenv()
    api_key = "sk-7582a5657fc042519669979db6cabd71"
    if not api_key:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        return None
    return ChatOpenAI(
        temperature=0,
        max_retries=int(max_retries),
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key=api_key,
    )

