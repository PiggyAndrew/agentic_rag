# Agentic RAG

Agentic RAG is a comprehensive Retrieval-Augmented Generation (RAG) application that combines a powerful Python backend with a modern Vue.js frontend. It features intelligent agents, a knowledge base system, and document processing capabilities, all wrapped in a user-friendly interface.

It can be run as a local web application or packaged as a standalone Windows desktop application.

## ✨ Key Features

- **🤖 Intelligent Agents**: Utilizes LangChain and LangGraph for complex reasoning and retrieval tasks.
- **📚 Knowledge Base**: Upload and manage documents (PDF, Word, etc.) to provide context for AI.
- **🔌 Multi-Model Support**: Seamless integration with OpenAI, DeepSeek, Ollama, DashScope, and more.
- **📄 Document Processing**: Advanced capabilities including PDF parsing and Word document rewriting.
- **🖥️ Hybrid Interface**: Available as both a web application and a Windows desktop app (WPF).
- **💬 Chat Interface**: Real-time chat with streaming support and artifact generation.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, SQLite, SQLAlchemy, LangChain, ChromaDB
- **Frontend**: Vue 3, TypeScript, Vite, Tailwind CSS, Shadcn UI
- **Desktop**: WPF (Windows Presentation Foundation) wrapper

## 🚀 Getting Started

### Prerequisites

- **Python** 3.11+
- **Node.js** (for frontend)
- **Git**

### 1. Backend Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/agentic_rag.git
    cd agentic_rag
    ```

2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    # or if using pyproject.toml directly
    pip install .
    ```

3.  Configure Environment Variables:
    Copy `.env.example` to `.env` and fill in your API keys.
    ```bash
    cp .env.example .env
    ```

4.  Run the server:
    ```bash
    python -m backend.entrypoints.server
    ```
    The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend/agui-vue
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

3.  Start the development server:
    ```bash
    npm run dev
    ```
    The UI will be available at `http://localhost:5173`.

## 📦 Building for Windows

To build the standalone Windows application (installer):

1.  Ensure you have **Python**, **Node.js**, **.NET SDK**, and **Inno Setup 6** installed.
2.  Run the automated setup script:
    ```cmd
    setup\auto_setup.bat
    ```
3.  This script will:
    - Build the Vue frontend.
    - Compile the Python backend into an executable.
    - Build the WPF desktop wrapper.
    - Generate an installer in the `Output` directory.

## ⚙️ Configuration (.env)

| Variable | Description | Example |
| :--- | :--- | :--- |
| `APP_ENV` | Environment (development/production) | `development` |
| `LLM_BASE_URL` | Base URL for LLM provider | `https://api.openai.com/v1` |
| `LLM_API_KEY` | API Key for LLM provider | `sk-...` |
| `LLM_MODEL` | Default LLM model name | `gpt-4o` |
| `EMBEDDING_BACKEND` | Embedding provider | `ollama` or `dashscope` |
| `EMBEDDING_BASE_URL`| Base URL for embeddings | `http://localhost:11434` |
| `LOG_LEVEL` | Logging level | `INFO` |

## 📄 License

[MIT](LICENSE)
