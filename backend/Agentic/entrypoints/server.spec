# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 配置文件
# 用于打包 Python 后端为单一可执行文件

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 基本配置
block_cipher = None

a = Analysis(
    ['backend/entrypoints/server.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含数据库迁移文件
        ('backend/database/migrations', 'backend/database/migrations'),
        # 包含共享提示词
        ('backend/shared/prompts', 'backend/shared/prompts'),
    ],
    hiddenimports=[
        # FastAPI 相关
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        
        # Pydantic 相关
        'pydantic',
        'pydantic_core',
        'pydantic_settings',
        
        # LangChain 相关
        'langchain',
        'langchain_core',
        'langchain_openai',
        'langchain_community',
        'langchain_deepseek',
        'langchain_ollama',
        'langgraph',
        
        # LlamaIndex 相关
        'llama_index',
        'llama_index.core',
        'llama_index.readers',
        'llama_index.embeddings',
        
        # 其他依赖
        'fastapi',
        'sqlalchemy',
        'chromadb',
        'sentence_transformers',
        'pymupdf4llm',
        'pymupdf',
        'pypdf',
        'openpyxl',
        'python_docx',
        'python_multipart',
        'dashscope',
        'openai',
        'ollama',
        'httpx',
        'aiohttp',
        'numpy',
        'pandas',
        
        # 后端模块
        'backend.api',
        'backend.database',
        'backend.domain',
        'backend.entrypoints',
        'backend.infrastructure',
        'backend.modules',
        'backend.services',
        'backend.shared',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='agent_api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台以便调试
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标路径
)
