import os
from fastapi import FastAPI
import uvicorn
from backend.api.main import create_app as create_api_app
from backend.config.settings import configure_logging


def create_app() -> FastAPI:
    """创建 FastAPI 应用并初始化日志"""
    configure_logging()
    return create_api_app()


app = create_app()


def main():
    """启动 uvicorn 服务入口"""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "backend.entrypoints.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
