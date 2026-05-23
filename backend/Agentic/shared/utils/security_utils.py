from __future__ import annotations

from typing import Optional


def mask_api_key(api_key: Optional[str]) -> str:
    """
    脱敏 API Key，只显示前 4 位和后 4 位
    
    Args:
        api_key: 原始 API Key
        
    Returns:
        脱敏后的 API Key，格式为 sk-****-****-****
    """
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


def is_valid_api_key(api_key: Optional[str]) -> bool:
    """
    验证 API Key 格式是否有效
    
    Args:
        api_key: API Key 字符串
        
    Returns:
        True 如果格式有效，False 否则
    """
    if not api_key:
        return False
    if len(api_key) < 8:
        return False
    return True
