import sys
import os
from cx_Freeze import setup, Executable

# ------------------------------------------------------------------------------
# 路径配置
# ------------------------------------------------------------------------------
# 获取 setup.py 所在目录 (e.g., d:\GitHub\agentic_rag\setup)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (e.g., d:\GitHub\agentic_rag)
project_root = os.path.dirname(current_dir)

# 将项目根目录加入 sys.path，解决 "ModuleNotFoundError: No module named 'backend'"
# 这样 cx_Freeze 在分析 imports 时能正确找到 backend 包
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ------------------------------------------------------------------------------
# 构建选项
# ------------------------------------------------------------------------------
build_exe_options = {
    # 强制包含 backend 包及其子包
    # 这会将 backend 代码编译进 library.zip，而不会以源码形式暴露在文件夹中
    "packages": [
        "backend", 
        "fastapi",
        "uvicorn",
        "dotenv",
        "pydantic",
        "numpy",
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langgraph",
        "langsmith",
        "langchain_community",
        "chromadb",  # Explicitly include chromadb
        "opentelemetry",  # Explicitly include opentelemetry
        "opentelemetry.context.contextvars_context", # Explicitly include the missing module
    ],
    # 排除不需要的大型库以减小体积
    "excludes": [
        "transformers",
        "scipy",
        "matplotlib",
        "torch",
        "tensorflow",
        "sklearn",
        "tkinter",
    ],
    # 包含必要的非 Python 数据文件
    # 格式: (源路径, 目标路径)
    "include_files": [
        # 1. 数据库迁移脚本 (runner.py 需要读取文件系统上的 .sql 文件)
        # 目标路径保持 backend/database/migrations/sqlite 结构
        (
            os.path.join(project_root, "backend", "database", "migrations", "sqlite"), 
            "backend/database/migrations/sqlite"
        ),
    ],
}

# 如果 .env 存在，也将其打包
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    build_exe_options["include_files"].append((env_path, ".env"))

# ------------------------------------------------------------------------------
# Setup 配置
# ------------------------------------------------------------------------------
setup(
    name="agent_api",
    version="1.0",
    description="Agentic RAG API",
    executables=[
        Executable(
            # 使用绝对路径指向入口文件
            script=os.path.join(project_root, "backend", "entrypoints", "server.py"),
            target_name="agent_api.exe",
            # base="Win32GUI" # 如果想完全隐藏黑框，可以取消注释（但建议开发阶段保留 Console 查看日志）
        )
    ],
    options={"build_exe": build_exe_options}
)
