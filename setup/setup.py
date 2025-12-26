from cx_Freeze import setup, Executable
import sys

# 构建选项
build_exe_options = {
    "packages": [
        "fastapi",
        "uvicorn",
        "dotenv",
        "pydantic",
        "numpy",
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langgraph",
        "app",
        "backend",
        "backend.kb",
        "backend.kb.splitters",
        "backend.agents",
        "backend.api",
        "backend.api.routers",
        "backend.tools",
        "backend.config",
        "backend.protocols",
        "langsmith",
    ],
    "excludes": [
        "transformers",
        "scipy",
        "matplotlib",
        "torch",
        "tensorflow",
        "sklearn",
    ],
    "include_files": [
        ".env",
    ],
}

setup(
    name="agent_api",
    version="1.0",
    description="Agentic RAG API",
    executables=[Executable("backend/api/main.py", target_name="agent_api.exe")],
    options={"build_exe": build_exe_options}
)
