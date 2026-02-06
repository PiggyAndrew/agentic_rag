import os
import sys
from fastapi import FastAPI
import uvicorn
from backend.api.main import create_app as create_api_app
from backend.modules.config.infrastructure.logging import configure_logging
from backend.modules.config.infrastructure.boot_config import AppEnv, get_boot_config


def _uvicorn_logging_config(level: str, access_level: str) -> dict:
    """构造 uvicorn 日志配置，降低控制台噪声

    - level：uvicorn 主日志级别（info/warning/error）
    - access_level：访问日志级别（info/warning）
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": "%(asctime)s %(levelname)s %(name)s: %(client_addr)s - \"%(request_line)s\" %(status_code)s",
            },
        },
        "handlers": {
            "default": {"class": "logging.StreamHandler", "formatter": "default", "stream": "ext://sys.stderr"},
            "access": {"class": "logging.StreamHandler", "formatter": "access", "stream": "ext://sys.stdout"},
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": level.upper(), "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": level.upper(), "propagate": False},
            "uvicorn.access": {"handlers": ["access"], "level": access_level.upper(), "propagate": False},
            "watchfiles": {"handlers": ["default"], "level": "WARNING", "propagate": False},
            "watchfiles.main": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        },
    }


def create_app() -> FastAPI:
    """创建 FastAPI 应用并初始化日志"""
    configure_logging()
    return create_api_app()


app = create_app()


def main():
    """启动 uvicorn 服务入口"""
    s = get_boot_config()
    is_dev = s.APP_ENV == AppEnv.development
    
    # 如果是打包后的环境，强制禁用 reload，避免无限重启
    if getattr(sys, 'frozen', False):
        is_dev = False
        
    port = int(os.getenv("PORT", "8000"))
    uv_level = "info" if is_dev else "warning"
    access_level = "info" if is_dev else "warning"
    log_config = _uvicorn_logging_config(uv_level, access_level)

    if is_dev:
        # 开发模式：使用字符串以支持 reload
        app_target = "backend.entrypoints.server:app"
    else:
        # 生产/打包模式：直接使用 app 实例，避免 import 路径问题
        app_target = app

    uvicorn.run(
        app_target,
        host="0.0.0.0",
        port=port,
        reload=is_dev,
        reload_dirs=["backend"] if is_dev else None,
        reload_delay=0.5 if is_dev else None,
        log_level=uv_level,
        access_log=is_dev,
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
