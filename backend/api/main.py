from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

    # 静态资源挂载：暴露 data/kb 目录用于图片访问
    # 访问示例：/assets/{kbId}/assets/images/{fileId}/{imageName}
    kb_assets_dir = os.path.join("data", "kb")
    os.makedirs(kb_assets_dir, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=kb_assets_dir), name="kb_assets")
    return app


app = create_app()
