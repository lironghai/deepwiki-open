# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepWiki is an AI-powered tool that automatically generates beautiful, interactive wikis for Git repositories (GitHub, GitLab, BitBucket). It analyzes code structure, creates visual diagrams using Mermaid, and provides an intelligent Q&A interface using RAG (Retrieval Augmented Generation).

**Core Technologies:**
- Backend: Python 3.11+ with FastAPI, AdalFlow library for RAG
- Frontend: Next.js 15 (React 19) with TypeScript, Tailwind CSS
- AI Models: Multi-provider support (Google Gemini, OpenAI, OpenRouter, Azure, Ollama, Bedrock)
- Embeddings: OpenAI, Google AI, Ollama, or Bedrock embeddings via AdalFlow
- Vector Store: FAISS for efficient similarity search
- MCP Server: FastMCP-based server for repository querying

## Essential Development Commands

### Backend (Python/FastAPI)
```bash
# Install dependencies (requires Poetry 2.0.1+)
python -m pip install poetry==2.0.1 && poetry install -C api

# Start API server (development mode with hot reload)
python -m api.main

# The API runs on port 8001 by default (configurable via PORT env var)
```

### Frontend (Next.js)
```bash
# Install dependencies
npm install
# or
yarn install

# Start development server (runs on custom port 29006)
npm run dev
# or
yarn dev

# Build for production
npm run build
# or
yarn build

# Lint code
npm run lint
# or
yarn lint
```

### Docker
```bash
# Using Docker Compose (recommended for full stack)
docker-compose up

# Build local image
docker build -t deepwiki-open .

# Run container with environment variables
docker run -p 8001:8001 -p 3000:3000 \
  -e GOOGLE_API_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  -v ~/.adalflow:/root/.adalflow \
  deepwiki-open
```

### MCP Server
```bash
# The MCP server is bundled with the API server
# It automatically starts when you run the API server
# Two main tools are provided:
# 1. deepwiki_list_projects - List processed repositories
# 2. deepwiki_ask - Ask questions about repositories
```

## High-Level Architecture

### Request Flow Architecture

```
User Request → Next.js Frontend → FastAPI Backend → AI Processing Pipeline
                                                    ↓
                                            1. Repository Cloning
                                            2. Code Analysis & Embedding
                                            3. FAISS Vector Store
                                            4. LLM Generation (via provider)
                                            5. Wiki Structure Creation
                                            6. Cache Storage
```

### Key Architectural Patterns

**1. Multi-Provider AI System**
- Centralized configuration in `api/config/generator.json` and `api/config/embedder.json`
- Provider-specific clients: `openai_client.py`, `google_embedder_client.py`, `openrouter_client.py`, `azureai_client.py`, `bedrock_client.py`, `dashscope_client.py`, `ollama_patch.py`
- Dynamic model selection at runtime via `api/config.py`

**2. RAG (Retrieval Augmented Generation) Pipeline**
- Entry point: `api/rag.py` with `SimpleRAG` and `SimpleDeepResearchRAG` classes
- Components:
  - `Memory`: Custom conversation history manager
  - `FAISSRetriever`: Semantic search over code embeddings
  - `Generator`: Provider-agnostic LLM interface
  - Prompts: `api/prompts.py` contains system prompts and templates

**3. Data Pipeline**
- `api/data_pipeline.py`: Repository cloning, code parsing, embedding generation
- `DatabaseManager`: Handles FAISS index persistence
- File filtering: Configurable exclusions via `api/config/repo.json`
- Token counting: Uses tiktoken for embedding token limits (MAX_EMBEDDING_TOKENS = 8192)

**4. Frontend State Management**
- Repository configuration cached in localStorage (`deepwikiRepoConfigCache`)
- Language context via `LanguageContext.tsx` for i18n support
- Processed projects tracked via custom hook `useProcessedProjects`

**5. Wiki Cache System**
- Location: `~/.adalflow/wikicache/`
- Format: `deepwiki_cache_{type}_{owner}_{repo}_{language}.json`
- Contains: Wiki structure, generated pages, provider/model metadata
- API endpoint: `/cache/wiki` (save), `/cache/wiki/{...}` (load)

### Critical File Paths

**Backend Core:**
- `api/main.py` - Entry point, configures uvicorn with 4 workers
- `api/api.py` - FastAPI routes and request handlers
- `api/rag.py` - RAG implementation with conversation memory
- `api/data_pipeline.py` - Repository processing and embeddings
- `api/config.py` - Configuration loader with env variable substitution
- `api/mcp_server.py` - MCP server implementation using FastMCP

**Configuration Files:**
- `api/config/generator.json` - LLM model configurations
- `api/config/embedder.json` - Embedding model settings
- `api/config/repo.json` - Repository filtering rules

**Frontend Core:**
- `src/app/page.tsx` - Homepage with repository input
- `src/app/[owner]/[repo]/page.tsx` - Wiki display page
- `src/components/Ask.tsx` - Q&A interface component
- `src/components/Mermaid.tsx` - Mermaid diagram renderer
- `src/contexts/LanguageContext.tsx` - Internationalization context

### Important Implementation Details

**1. Embedding Type Selection**
- Controlled by `DEEPWIKI_EMBEDDER_TYPE` environment variable
- Supported types: `openai`, `google`, `ollama`, `bedrock`
- Default: `openai`
- Different embedders require different API keys

**2. Repository Cloning**
- Supports GitHub, GitLab, BitBucket
- Private repo support via access tokens
- Clones to `~/.adalflow/repos/`
- Token injection into URL for authenticated cloning

**3. Background Task Management**
- Uses `ThreadPoolExecutor` with 4 workers for repository preparation
- Status tracking via `preparing_repos` dictionary with thread locks
- WebSocket endpoint for progress updates: `/ws/prepare-status/{repo_identifier}`

**4. Streaming Responses**
- Chat completions use Server-Sent Events (SSE)
- Generator yields chunks via `acall()` method
- Frontend streams via EventSource API

**5. Code Analysis**
- Language-specific parsers in `api/parsers/` (Go, Java, Python, etc.)
- Uses tree-sitter for AST parsing
- Extracts functions, classes, imports for better context

**6. Port Configuration**
- Frontend dev server: Port 29006 (custom, not standard 3000)
- Backend API: Port 8001 (configurable via PORT env var)
- Ensure `SERVER_BASE_URL` in frontend matches API server location

**7. Logging System**
- Python logging configured in `api/logging_config.py`
- Configurable via `LOG_LEVEL` and `LOG_FILE_PATH` environment variables
- Default log location: `api/logs/application.log`
- Log directory mounted in Docker for persistence

**8. Authorization Mode**
- Optional feature controlled by `DEEPWIKI_AUTH_MODE` and `DEEPWIKI_AUTH_CODE`
- When enabled, frontend requires authorization code for wiki generation
- Restricts frontend initiation and cache deletion

### Environment Variables

**Required for full functionality:**
- At least one of: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `AZURE_OPENAI_API_KEY`, or AWS credentials for Bedrock
- Embedder-specific: Based on `DEEPWIKI_EMBEDDER_TYPE` setting

**Optional configuration:**
- `PORT` - API server port (default: 8001)
- `SERVER_BASE_URL` - API base URL (default: http://localhost:8001)
- `DEEPWIKI_EMBEDDER_TYPE` - Embedder provider (default: openai)
- `DEEPWIKI_CONFIG_DIR` - Custom config directory path
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `LOG_FILE_PATH` - Log file location (default: api/logs/application.log)
- `DEEPWIKI_AUTH_MODE` - Enable authorization mode (default: false)
- `DEEPWIKI_AUTH_CODE` - Authorization code when auth mode enabled
- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)
- `OPENAI_BASE_URL` - Custom OpenAI API endpoint

**Provider-specific:**
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_VERSION` - For Azure OpenAI
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ROLE_ARN` - For Bedrock

### Testing & Development Notes

**Custom Development Port:**
- The Next.js dev server is configured to run on port 29006 instead of the default 3000
- This is set in package.json: `"dev": "next dev --turbopack --port 29006"`

**Hot Reload:**
- Backend: Uvicorn auto-reload enabled in development
- Backend excludes `logs/` directory from reload triggers
- Frontend: Next.js Turbopack for fast refresh

**Token Management:**
- Token counting uses tiktoken library
- Different encodings for different embedders (cl100k_base for Ollama/Google/Bedrock)
- Embedding token limit: 8192 tokens per chunk
- RAG context window: 7500 tokens safe threshold

**Common Development Patterns:**
- Configuration changes require server restart
- Cache invalidation: Delete files in `~/.adalflow/wikicache/`
- Database reset: Delete `~/.adalflow/databases/`
- Repository re-clone: Delete `~/.adalflow/repos/{repo_name}`

**MCP Server Integration:**
- Implements standard MCP protocol via FastMCP
- Provides programmatic access to DeepWiki repositories
- Enables integration with MCP-compatible tools and IDEs
- Two main capabilities:
  1. Listing processed repositories with fuzzy search
  2. Asking questions about repository content with RAG

### Internationalization

The project supports multiple languages:
- English, Chinese (Simplified/Traditional), Japanese, Spanish, Korean, Vietnamese, Portuguese, French, Russian
- Language context managed via `LanguageContext.tsx`
- Translation files in `src/messages/`
- Selected language stored in localStorage and affects both UI and generated content

### Security Considerations

- API keys managed via environment variables
- Private repository tokens injected into clone URLs
- CORS enabled for all origins (consider restricting in production)
- Log file path validation prevents path traversal
- Authorization mode available for access control
