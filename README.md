# AI Twin — Contextual Document Understanding

An AI-powered assistant that lets users upload PDF documents and ask natural-language questions grounded in those documents. Built with FastAPI, LangGraph, Qdrant, and Next.js.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Next.js 14 Frontend                   │
│  Auth pages  │  Document upload  │  Streaming chat UI        │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend                         │
│                                                              │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  Auth API   │   │ Documents API│   │    Chat API (SSE) │  │
│  └──────┬──────┘   └──────┬───────┘   └────────┬─────────┘  │
│         │                 │                     │            │
│  ┌──────▼──────┐   ┌──────▼───────┐   ┌────────▼─────────┐  │
│  │ Auth Service│   │ Doc Ingest   │   │  LangGraph Graph  │  │
│  │  JWT + BCrypt│  │ PDF→Chunks   │   │  retrieve_node    │  │
│  └─────────────┘   │ Embed→Qdrant │   │  generate_node    │  │
│                    └──────┬───────┘   │  summarize_node   │  │
│                           │           └────────┬─────────┘  │
└───────────────────────────┼────────────────────┼────────────┘
                            │                    │
              ┌─────────────▼──┐      ┌──────────▼────────┐
              │   Qdrant       │      │  OpenAI / LiteLLM │
              │  global_docs   │      │  GPT-4o-mini       │
              │  private_docs  │      └───────────────────┘
              └────────────────┘
                            │
              ┌─────────────▼──┐
              │   PostgreSQL   │
              │  Users         │
              │  Documents     │
              │  Conversations │
              │  Messages      │
              └────────────────┘
```

**Document retrieval** fetches chunks from both the global collection (shared across all users) and the requesting user's private collection. Results are merged by cosine similarity score.

**LangGraph** maintains per-conversation state via `MemorySaver` checkpoints. A summarization node fires when the message history exceeds 15 messages or ~3000 tokens.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- An OpenAI-compatible API key (or LiteLLM proxy)

### 1. Clone and configure

```bash
git clone <repo-url>
cd wizly-assignment
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```
LITELLM_API_KEY=sk-...           # your OpenAI / LiteLLM key
JWT_SECRET_KEY=<random-64-chars>
SECRET_KEY=<random-64-chars>
```

### 2. Start all services

```bash
docker compose up --build
```

Services started:
| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Qdrant | http://localhost:6333 |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | FastAPI secret key |
| `DATABASE_URL` | Yes | — | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | Yes | — | JWT signing secret |
| `JWT_ACCESS_TOKEN_LIFETIME` | No | `15` | Access token lifetime (minutes) |
| `JWT_REFRESH_TOKEN_LIFETIME` | No | `10080` | Refresh token lifetime (minutes, 7 days) |
| `LITELLM_API_KEY` | Yes | — | OpenAI / LiteLLM API key |
| `LITELLM_BASE_URL` | No | `` | Custom LiteLLM proxy URL |
| `EMBEDDING_MODEL` | No | `BAAI/bge-base-en-v1.5` | HuggingFace embedding model |
| `EMBEDDING_DIMENSIONS` | No | `768` | Vector size (must match the embedding model) |
| `QDRANT_URL` | Yes | — | Qdrant HTTP URL (e.g. `http://localhost:6333`, or `http://qdrant:6333` in Compose) |
| `QDRANT_API_KEY` | No | — | Qdrant API key (if enabled on the server) |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000,http://localhost:3001` | CORS allowed origins (comma-separated) |
| `LANGCHAIN_TRACING_V2` | No | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | `wizly-ai-twin` | LangSmith project name |
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend URL visible to the browser |

---

## API Reference

All endpoints return JSON. Protected endpoints require `Authorization: Bearer <access_token>`.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Register a new user |
| `POST` | `/auth/login` | No | Login, returns `access_token` + `refresh_token` |
| `POST` | `/auth/refresh` | No | Exchange refresh token for new access token |
| `POST` | `/auth/logout` | Yes | Blacklist the current access token |

**Rate limits:** `/auth/register` — 10 req/min, `/auth/login` — 20 req/min.

### Documents

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/documents/upload` | Yes | Upload a PDF (`multipart/form-data`: `file`, `visibility`) |
| `GET` | `/documents/` | Yes | List documents for the current user |
| `DELETE` | `/documents/{doc_id}` | Yes | Delete a document (removes from DB, Qdrant, object storage) |

`visibility` values: `global` (queryable by AI Twin) or `private` (owner-only).

### Chat

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/conversations/` | Yes | Create a new conversation |
| `GET` | `/conversations/` | Yes | List all conversations for the current user |
| `GET` | `/conversations/{id}/messages` | Yes | Get full message history |
| `GET` | `/conversations/{id}/stream?query=...` | Yes | SSE chat stream |

**SSE event format:**
```
data: {"type": "token", "content": "The "}
data: {"type": "token", "content": "answer"}
data: {"type": "sources", "sources": [{"doc_id": "...", "filename": "...", "page": 1}]}
data: {"type": "done"}
```

### Health & Debug

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | No | Health check |
| `GET` | `/debug/checkpoint/{session_id}` | No | Inspect LangGraph checkpoint |
| `GET` | `/debug/qdrant` | No | Inspect Qdrant collection counts and sample metadata |

---

## Development

### Backend (without Docker)

Run Qdrant locally (for example `docker compose up qdrant -d`, or `docker run -p 6333:6333 qdrant/qdrant`), set `QDRANT_URL=http://localhost:6333` in `.env`, then:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

### Run tests

```bash
# Backend — from /backend
pytest --cov=app --cov-report=term-missing

# Lint + type check
ruff check .
mypy app/
```

### Rebuild after code changes

```bash
docker compose up -d --build backend
docker compose up -d --build frontend
```

---

## Security Notes

- JWT tokens expire server-side; logout blacklists the JTI in PostgreSQL.
- Private documents are stored in a separate Qdrant collection, filtered by `user_id` — they are never exposed to other users or to the LLM.
- The AI Twin chat endpoint exclusively queries the `global_docs` collection plus the authenticated user's own `private_docs`. No cross-user leakage is possible.
- File uploads validate MIME type and extension server-side; max size is 20 MB.
- Auth endpoints are rate-limited (10–20 req/min per IP).
- CORS is configured via `ALLOWED_ORIGINS` env var — lock it to your production domain.
- Stack traces are never returned to clients; all unhandled errors return a generic 500 message.
