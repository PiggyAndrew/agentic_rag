from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

# 获取全局 logger
logger = logging.getLogger("app.error")

class ApiError(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None

class ApiResponse(BaseModel):
    ok: bool
    data: Optional[Any] = None
    error: Optional[ApiError] = None

def handle_exception(exc: Exception, context: Optional[str] = None) -> ApiResponse:
    """
    统一处理异常的工具函数。
    1. 记录详细的错误日志（包含堆栈信息）
    2. 返回统一格式的 ApiResponse 供前端显示
    """
    # 记录错误到日志
    log_msg = f"Exception occurred"
    if context:
        log_msg += f" in context: {context}"
    
    # 使用 logger.exception 会自动记录当前堆栈
    logger.exception(f"{log_msg}: {type(exc).__name__}: {exc}")

    # 构造返回给前端的错误信息
    # 这里可以根据异常类型进行细分处理
    error_code = 500
    error_message = f"服务错误: {type(exc).__name__}: {exc}"
    
    # 如果是 HTTPException 或其他带有状态码的异常，可以提取状态码
    if hasattr(exc, "status_code"):
        error_code = getattr(exc, "status_code")
    
    # 对于开发环境，可以考虑在 detail 中返回堆栈信息（可选）
    # detail = traceback.format_exc()
    
    return ApiResponse(
        ok=False,
        error=ApiError(
            code=error_code,
            message=error_message
        )
    )

def log_and_raise(exc: Exception, context: Optional[str] = None):
    """记录日志并重新抛出异常，适用于不想在当前层处理异常但需要记录的情况"""
    log_msg = f"Error"
    if context:
        log_msg += f" in {context}"
    logger.exception(f"{log_msg}: {exc}")
    raise exc
