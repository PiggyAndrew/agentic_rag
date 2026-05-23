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
from pathlib import Path
from backend.api.models import ApiResponse, ApiError
from backend.shared.utils.error_handler import handle_exception

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def create_app() -> FastAPI:
    """创建 FastAPI 应用并挂载路由与中间件"""
    os.environ.setdefault("OTEL_PYTHON_DISABLED", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    load_dotenv(dotenv_path=ENV_FILE)

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

    @app.exception_handler(ValueError)
    async def handle_value_error(req: Request, exc: ValueError):
        resp = handle_exception(exc, context=f"Value error at {req.url.path}")
        return JSONResponse(
            status_code=400,
            content=resp.model_dump(),
        )

    @app.exception_handler(FileNotFoundError)
    async def handle_not_found(req: Request, exc: FileNotFoundError):
        resp = handle_exception(exc, context=f"Not found at {req.url.path}")
        return JSONResponse(
            status_code=404,
            content=resp.model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(req: Request, exc: HTTPException):
        resp = handle_exception(exc, context=f"HTTP exception at {req.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=resp.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(req: Request, exc: RequestValidationError):
        resp = handle_exception(exc, context=f"Validation error at {req.url.path}")
        # 对于校验错误，返回 422
        if resp.error:
            resp.error.code = 422
        return JSONResponse(
            status_code=422,
            content=resp.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(req: Request, exc: Exception):
        resp = handle_exception(exc, context=f"API path={req.url.path}")
        return JSONResponse(
            status_code=resp.error.code if resp.error else 500,
            content=resp.model_dump(),
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
    from backend.entrypoints.composition.kb import default_kb_base_dir
    kb_assets_dir = default_kb_base_dir()
    os.makedirs(kb_assets_dir, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=kb_assets_dir), name="kb_assets")
    return app


app = create_app()
