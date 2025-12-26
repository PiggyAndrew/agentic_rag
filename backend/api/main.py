from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os


def create_app() -> FastAPI:
    """创建 FastAPI 应用并挂载路由与中间件"""
    os.environ.setdefault("OTEL_PYTHON_DISABLED", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    load_dotenv()
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由注册
    from backend.api.routers.chat import router as chat_router
    from backend.api.routers.kb import router as kb_router
    app.include_router(chat_router)
    app.include_router(kb_router)
    return app


app = create_app()
