from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os
import logging
from backend.api.models import ApiResponse, ApiError


def create_app() -> FastAPI:
    """创建 FastAPI 应用并挂载路由与中间件"""
    os.environ.setdefault("OTEL_PYTHON_DISABLED", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    load_dotenv()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        from backend.database.sqlite import init_sqlite_database
        from backend.config.init_providers import seed_providers

        init_sqlite_database()
        seed_providers()
        yield

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    logger = logging.getLogger("api")

    @app.exception_handler(ValueError)
    async def handle_value_error(_: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                ok=False, error=ApiError(code=400, message=str(exc))
            ).dict(),
        )

    @app.exception_handler(FileNotFoundError)
    async def handle_not_found(_: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                ok=False, error=ApiError(code=404, message=str(exc))
            ).dict(),
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(req: Request, exc: Exception):
        logger.exception("API error: path=%s", req.url.path)
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                ok=False,
                error=ApiError(
                    code=500, message=f"服务错误: {type(exc).__name__}: {exc}"
                ),
            ).dict(),
        )

    # 路由注册
    from backend.api.routers.chat import router as chat_router
    from backend.api.routers.kb import router as kb_router
    from backend.api.routers.docx import router as docx_router
    from backend.api.routers.config import router as config_router
    from backend.api.routers.llm_config import router as llm_config_router

    app.include_router(chat_router)
    app.include_router(kb_router)
    app.include_router(docx_router)
    app.include_router(config_router)
    app.include_router(llm_config_router)

    # 静态资源挂载：暴露 data/kb 目录用于图片访问
    # 访问示例：/assets/{kbId}/assets/images/{fileId}/{imageName}
    kb_assets_dir = os.path.join("data", "kb")
    os.makedirs(kb_assets_dir, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=kb_assets_dir), name="kb_assets")
    return app


app = create_app()
