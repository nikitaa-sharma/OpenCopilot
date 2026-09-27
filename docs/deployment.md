# Local Development & Operations Guide

This document provides complete instructions for orchestrating, operating, and developing **OpenSource Copilot** locally via Docker Compose or hybrid developer workflows.

> **Note**: OpenSource Copilot is currently configured and documented for **Local Development Only**.

---

## 1. System Architecture & Container Topology

OpenSource Copilot is composed of four decoupled, scalable tiers:

```
                    ┌─────────────────────────┐
                    │      Client Browser     │
                    │   (User's Web Browser)  │
                    └────────────┬────────────┘
                                 │
                 HTTP :3000      │      HTTP :8000
                 (UI Pages)      │      (REST API)
                                 ▼
                    ┌─────────────────────────┐
                    │        Frontend         │
                    │      Next.js 14 / UI    │
                    │      (Port 3000)        │
                    └────────────┬────────────┘
                                 │
                                 │ Internal Container Bridge Network
                                 │ (`opencopilot_net`)
                                 ▼
                    ┌─────────────────────────┐
                    │         Backend         │
                    │     FastAPI / Python    │
                    │       (Port 8000)       │
                    └───────┬─────────┬───────┘
                            │         │
      postgresql+asyncpg:// │         │ http://ollama:11434
      postgres:5432         │         │
                            ▼         ▼
             ┌──────────────────┐  ┌──────────────────┐
             │     Database     │  │    LLM Engine    │
             │ PostgreSQL 16 +  │  │   Ollama Local   │
             │     pgvector     │  │   (llama3.2:3b)  │
             │   (Port 5432)    │  │   (Port 11434)   │
             └──────────────────┘  └──────────────────┘
```

### Network Separation
- **Host / Browser Traffic**: Requests to `http://localhost:3000` (Frontend) and `http://localhost:8000` (Backend API) bind to host ports.
- **Internal Service Traffic**: Containers communicate over the `opencopilot_net` bridge network using Docker DNS service names (`postgres:5432`, `ollama:11434`, `backend:8000`).
- **Persistent Data**: Database tables and vector embeddings are persisted in the `pgvector_data` volume. Downloaded LLM weights are persisted in the `ollama_data` volume.

---

## 2. Local Setup with Docker Compose

### Prerequisites
- [Docker Engine](https://docs.docker.com/engine/install/) (v24.0 or newer)
- [Docker Compose](https://docs.docker.com/compose/) (v2.20 or newer)
- At least 8 GB RAM recommended for running local LLMs

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/your-org/opencopilot.git
cd opencopilot

# Copy configuration template
cp .env.example .env
```

Review `.env`. The defaults are pre-configured to work immediately out of the box. If you have a GitHub Personal Access Token (for higher GitHub API rate limits), add it to `GITHUB_TOKEN`.
If host port 5432 is occupied by an existing local PostgreSQL service on Windows, set `POSTGRES_PORT=5433` in `.env`.

### Step 2: Build and Start Services
```bash
docker compose up -d --build
```

This will:
1. Start PostgreSQL with pgvector and run health checks until ready.
2. Start the Ollama local AI runtime container.
3. Build and launch the FastAPI backend (connecting to `postgres` and `ollama`).
4. Build and launch the Next.js frontend web UI.

### Step 3: Pull the Recommended Local LLM Model
Because LLM model weights are multi-gigabyte files, Ollama does not block initial container startup. Download the recommended model into the persistent volume once:
```bash
docker compose exec ollama ollama pull llama3.2:3b
```

> **Tip**: For machines with higher VRAM (8GB+), you can optionally pull larger models like `llama3.1:8b` or `mistral:7b`, then update `LLM_MODEL` in `.env`.

### Step 4: Verify Local Deployment
Check the status of running containers:
```bash
docker compose ps
```

Verify backend health:
```bash
curl http://localhost:8000/api/health
# Response: {"status":"ok"}
```

Open your browser to:
- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Step 5: Viewing Logs and Teardown
```bash
# Stream logs from all services
docker compose logs -f

# Stream logs from backend only
docker compose logs -f backend

# Stop services (preserves database and models)
docker compose down

# Stop services and remove all persistent volumes (fresh reset)
docker compose down -v
```

---

## 3. Hybrid Development Setup

For fast local development where you want live hot-reloading for code changes without waiting for Docker image builds:

### 1. Run Infrastructure Services in Docker
```bash
docker compose up -d postgres ollama
```
*(If host port 5432 has a conflict with native PostgreSQL, set `POSTGRES_PORT=5433` in your root `.env`)*.

### 2. Run Backend Locally
```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit DATABASE_URL in backend/.env if using port 5433:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/opencopilot

python -m uvicorn app.main:app --reload --port 8000
```

### 3. Run Frontend Locally
```bash
cd frontend
npm install
npm run dev
```

### 4. Pull the Local LLM Model
```bash
docker compose exec ollama ollama pull llama3.2:3b
# Or if running native Ollama:
ollama pull llama3.2:3b
```

---

## 4. Environment Variables Reference

| Variable | Default | Required | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/opencopilot` | Yes | PostgreSQL connection string with `asyncpg` driver |
| `POSTGRES_USER` | `postgres` | No | PostgreSQL user for Docker Compose |
| `POSTGRES_PASSWORD` | `postgres` | No | PostgreSQL password for Docker Compose |
| `POSTGRES_DB` | `opencopilot` | No | PostgreSQL database name |
| `POSTGRES_PORT` | `5432` | No | Host port for PostgreSQL (`5433` if 5432 is occupied) |
| `LLM_PROVIDER` | `ollama` | Yes | AI provider (`ollama`) |
| `LLM_BASE_URL` | `http://localhost:11434` | Yes | Base URL for LLM provider API |
| `LLM_MODEL` | `llama3.2:3b` | Yes | Target LLM model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Yes | Local Ollama endpoint URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Yes | Local Ollama model identifier |
| `GITHUB_TOKEN` | `""` | No | Personal Access Token for GitHub API (raises rate limits) |
| `AUTH_SECRET_KEY` | *dev key* | No | Secret key for JWT signing (minimum 32 characters) |
| `AUTH_ALGORITHM` | `HS256` | No | JWT algorithm |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | No | JWT session lifetime |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | Yes | JSON list or comma-separated allowed origins |
| `ENVIRONMENT` | `development` | No | Environment mode (`development`, `production`, `testing`) |
| `EMBEDDING_PROVIDER` | `sentence_transformers` | Yes | Local embedding provider (`sentence_transformers`) |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Yes | Sentence transformer model name |
| `EMBEDDING_DIMENSION` | `384` | Yes | Vector dimension (must match PostgreSQL schema) |
| `EMBEDDING_DEVICE` | `cpu` | No | Embedding compute device (`cpu` or `cuda`) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api` | Yes | Backend API base URL accessible from frontend |

---

## 5. Operational Troubleshooting & FAQ

### Port 5432 or 8000 is already in use
If another PostgreSQL instance (e.g. Windows native service) or web server is running locally:
```bash
# In .env, change host port bindings:
POSTGRES_PORT=5433
BACKEND_PORT=8001
FRONTEND_PORT=3001
```
And update `DATABASE_URL` in `backend/.env` to point to port `5433`.

### Ollama responds with "model not found"
If you see an error indicating `llama3.2:3b` was not found:
```bash
# Docker Compose:
docker compose exec ollama ollama pull llama3.2:3b

# Local native Ollama:
ollama pull llama3.2:3b
```

### Database migration / tables initialization
The backend automatically creates the `vector` extension and all required tables on startup via SQLAlchemy `init_db()`. If tables need to be manually inspected:
```bash
docker compose exec postgres psql -U postgres -d opencopilot -c "\dt"
```

### CORS error in browser console
Ensure that `CORS_ORIGINS` in the backend environment includes the frontend URL:
```ini
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```
