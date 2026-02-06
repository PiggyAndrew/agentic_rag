import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
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
    async def lifespan(app: FastAPI):
        from backend.database.sqlite import build_sqlite_manager, init_sqlite_database
        from backend.modules.providers.infrastructure.seed import seed_providers
        from backend.modules.config.infrastructure.persistence.models import ConfigBase
        from backend.modules.config.infrastructure.repository import SqlAlchemyConfigRepository
        from backend.modules.chat.infrastructure.persistence.models import ChatBase
        from backend.modules.kb.infrastructure.persistence.models import Base as KnowledgeBase
        from backend.modules.providers.infrastructure.persistence.models import ProvidersBase
        from backend.modules.chat.infrastructure.chat_service import ChatService
        from backend.modules.chat.application.usecase import ChatUseCase
        from backend.entrypoints.composition.kb import build_kb_usecase, default_kb_base_dir
        from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
        from backend.modules.config.application.config_service import build_config_service
        from backend.modules.config.infrastructure.db_repository import SqliteConfigRepositoryAdapter
        from backend.modules.config.infrastructure.env_source import EnvConfigSource
        from backend.modules.providers.application.provider_service import ProviderService
        from backend.modules.providers.infrastructure.httpx_chat_tester import HttpxChatCompletionsTester
        from backend.modules.agents.infrastructure.event_logger import log_stream_event_json

        manager = build_sqlite_manager()
        app.state.sqlite_manager = manager
        init_sqlite_database(
            manager=manager,
            metadatas=[
                KnowledgeBase.metadata,
                ConfigBase.metadata,
                ProvidersBase.metadata,
                ChatBase.metadata,
            ]
        )
        config_repo = SqlAlchemyConfigRepository(manager=manager)
        app.state.config_repo = config_repo
        app.state.config_service = build_config_service(
            sources=[EnvConfigSource()],
            repository=SqliteConfigRepositoryAdapter(repo=config_repo),
        )
        seed_providers(manager=manager)
        chat_repo = ChatService(manager=manager)
        app.state.chat_usecase = ChatUseCase(repo=chat_repo)
        app.state.kb_usecase = build_kb_usecase(manager=manager, base_dir=default_kb_base_dir())
        app.state.llm_config_repo = LLMConfigRepository(manager=manager)
        app.state.provider_service = ProviderService(repo=app.state.llm_config_repo, tester=HttpxChatCompletionsTester())
        app.state.stream_event_logger = log_stream_event_json
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

    def _detail_to_message(detail) -> str:
        if detail is None:
            return ""
        if isinstance(detail, str):
            return detail
        try:
            return json.dumps(detail, ensure_ascii=False)
        except Exception:
            return str(detail)

    @app.exception_handler(ValueError)
    async def handle_value_error(_: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                ok=False, error=ApiError(code=400, message=str(exc))
            ).model_dump(),
        )

    @app.exception_handler(FileNotFoundError)
    async def handle_not_found(_: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                ok=False, error=ApiError(code=404, message=str(exc))
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException):
        status = int(getattr(exc, "status_code", 500) or 500)
        return JSONResponse(
            status_code=status,
            content=ApiResponse(
                ok=False, error=ApiError(code=status, message=_detail_to_message(getattr(exc, "detail", "")))
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                ok=False, error=ApiError(code=422, message=_detail_to_message(exc.errors()))
            ).model_dump(),
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
            ).model_dump(),
        )

    # 路由注册
    from backend.api.routers.chat import router as chat_router
    from backend.api.routers.chat_history import router as chat_history_router
    from backend.api.routers.kb import router as kb_router
    from backend.api.routers.docx import router as docx_router
    from backend.api.routers.config import router as config_router
    from backend.api.routers.llm_config import router as llm_config_router

    app.include_router(chat_router)
    app.include_router(chat_history_router, prefix="/api/chat")
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
