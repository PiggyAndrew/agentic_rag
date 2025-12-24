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
        "kb",
        "app",
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
    executables=[Executable("app/api.py", target_name="agent_api.exe")],
    options={"build_exe": build_exe_options}
)
