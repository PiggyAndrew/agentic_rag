# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agentic RAG is a local-first Retrieval-Augmented Generation application combining a Python FastAPI backend with a Vue 3 frontend. It supports multiple AI providers (OpenAI, DeepSeek, Ollama, DashScope), knowledge base management with vector embeddings (ChromaDB), and document processing (PDF, Excel). All data is stored locally for privacy.

## Development Commands

### Backend (Python)

```bash
# Run the development server (default: http://localhost:8000)
python -m backend.entrypoints.server

# Run tests
python -m pytest tests/unittests/
python -m pytest tests/non_unittests/

# Run specific test
python -m pytest tests/unittests/test_kb_sqlite_service.py
```

### Frontend (Vue 3)

```bash
cd frontend/agui-vue

# Install dependencies
npm install

# Development server (http://localhost:5173)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Full Build (Windows Desktop)

```cmd
setup\auto_setup.bat
```

This builds the Vue frontend, Python backend (cx_Freeze), and WPF wrapper, then creates an Inno Setup installer.

## Architecture

### Backend Structure

- `backend/api/` - FastAPI routes and models
  - `main.py` - App factory with CORS, exception handlers, router registration
  - `routers/chat.py` - Chat streaming endpoint with citation tracking
  - `routers/chat_history.py` - Chat session management
  - `routers/kb.py` - Knowledge base CRUD operations
  - `routers/config.py` - System configuration endpoints
  - `routers/llm_config.py` - LLM provider management
  - `routers/docx.py` - Document processing

- `backend/agents/` - LangGraph-based agents
  - `rag_agent.py` - RAG agent with tool integration
  - `sql_agent.py` - SQL query agent
  - `vision_ollama_qwen3_vl.py` - Vision/image processing agent
  - `graph.py` - Base agent graph structure with `AgentState(MessagesState)`

- `backend/kb/` - Knowledge base management
  - `knowledge_service.py` - Service layer for KB operations (create, ingest, search)
  - `knowledge_base.py` - PersistentKnowledgeBaseController for disk operations
  - `knowledge_repository.py` - SqlAlchemyKnowledgeRepository for metadata
  - `knowledge_models.py` - SQLAlchemy ORM models
  - `embeddings.py` - Embedding provider abstraction (Ollama, DashScope)
  - `vector_store.py` - ChromaDB integration
  - `ingestion.py` - PDF/Excel document parsing and chunking
  - `splitters/` - Text chunking strategies (normal, headings-based, table, adaptive)
  - `rerank.py` - Reranking of search results

- `backend/database/` - Database layer
  - `sqlite.py` - SqliteSessionManager, init_sqlite_database()
  - `chat_models.py` - ChatMessage ORM with citation support
  - `chat_service.py` - ChatMessage CRUD operations
  - `migrations/runner.py` - SQL migration system (versioned scripts in `migrations/sqlite/`)

- `backend/config/` - Configuration management
  - `settings.py` - Settings singleton with `get_settings()`, runtime config from env (dev) or db (prod)
  - `init_providers.py` - Seeds default LLM/embedding/reranker providers
  - `config_models.py` - SystemConfig ORM for persistent settings

- `backend/services/` - Business logic
- `backend/tools/` - LangChain tools (e.g., `read_file_chunks` for RAG retrieval)
- `backend/prompts/` - System prompts for agents
- `backend/protocols/` - Protocol definitions including `streaming.py`

### Frontend Structure (Vue 3 + TypeScript)

- `frontend/agui-vue/src/api/` - API client functions
- `frontend/agui-vue/src/components/` - Vue components
  - `KnowledgeBaseChat.vue` - Main chat interface with streaming
  - `KnowledgeBaseManager.vue` - KB CRUD operations
  - `FileParseSettingsDialog.vue` - File parsing configuration
- `frontend/agui-vue/src/pages/` - Page components
- `frontend/agui-vue/src/stores/` - Pinia stores (kb.ts, chat.ts)
- `frontend/agui-vue/src/router/index.ts` - Vue Router configuration
- `frontend/agui-wpf/` - WPF desktop wrapper (C# .NET 8)

## Key Architectural Patterns

### Configuration Management
- **Development**: Configuration loaded from environment variables (`.env`)
- **Production**: Configuration loaded from `system_configs` table in SQLite
- Use `get_settings().get_config("llm.baseUrl")` for unified access

### Knowledge Base IDs
- KB IDs use format `kb-{integer}` (e.g., `kb-1`)
- File IDs use format `f-{integer}` (e.g., `f-42`)
- Use `parse_kb_id()` and `parse_file_id()` from `kb/knowledge_service.py` to convert

### Agent Workflow
- Agents built with LangGraph `StateGraph(AgentState)`
- State extends `MessagesState` with additional fields (e.g., `tools`)
- Streaming responses use SSE with JSON event format
- Tool outputs tracked via `on_tool_end` events for citations

### Database Migrations
- SQL scripts in `backend/database/migrations/sqlite/`
- Filenames as version numbers (e.g., `0003_add_chat_message_citations.sql`)
- Applied automatically on startup via `apply_sql_migrations()`
- Tracked in `schema_migrations` table

### Chat History
- Sessions stored in SQLite (`chat_sessions`, `chat_messages` tables)
- Citations attached to assistant messages via JSON column
- Streaming wrapper accumulates chunks and saves complete messages

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | `development` |
| `LLM_BASE_URL` | LLM provider base URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM API key | Required |
| `LLM_MODEL` | Default model name | `gpt-4o` |
| `DEEPSEEK_API_KEY` | DeepSeek API key | - |
| `EMBEDDING_BACKEND` | Embedding provider (ollama/dashscope) | `ollama` (dev), `dashscope` (prod) |
| `EMBEDDING_BASE_URL` | Embedding service URL | `http://localhost:11434` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Testing

Tests are split into:
- `tests/unittests/` - Isolated unit tests (repository, service layer)
- `tests/non_unittests/` - Integration tests requiring external services (API routes, agent execution, document processing)

Run with `pytest` directly - the codebase does not use standard unittest conventions.

## Data Storage

- **SQLite**: `data/kb/knowledge.sqlite3` for metadata, sessions, config
- **ChromaDB**: `data/kb/kb-{id}/chroma` for vector embeddings
- **File uploads**: `data/kb/kb-{id}/uploads/` for source documents
- **Static assets**: `/assets/{kbId}/assets/images/{fileId}/{imageName}` served from `data/kb/`

## API Endpoints

- `POST /api/chat` - Streaming chat with optional KB ID and session
- `GET/POST /api/chat/sessions` - Chat session management
- `GET/POST /api/kb` - Knowledge base CRUD
- `POST /api/kb/{kbId}/files` - Upload files
- `POST /api/kb/{kbId}/ingest` - Ingest uploaded file
- `GET/POST /api/config` - System configuration
- `GET/POST /api/llm_config` - LLM provider configuration
- `GET /assets/*` - Static file serving
