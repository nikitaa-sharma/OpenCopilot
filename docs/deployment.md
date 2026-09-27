# Deployment & Operational Guide

This document provides complete instructions for deploying, orchestrating, and operating **OpenSource Copilot** locally via Docker Compose, in hybrid developer setups, and across low-cost or free-tier cloud platforms.

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
             │     pgvector     │  │   or Remote API  │
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

### Step 2: Build and Start Services
```bash
docker compose up -d --build
```

This will:
1. Start PostgreSQL with pgvector and run health checks until ready.
2. Start the Ollama engine container.
3. Build and launch the FastAPI backend (connecting to `postgres` and `ollama`).
4. Build and launch the Next.js frontend web UI.

### Step 3: Pull the Recommended LLM Model
Because LLM model weights are multi-gigabyte files, Ollama does not block initial container startup. Download the recommended model into the persistent volume once:
```bash
docker compose exec ollama ollama pull llama3.2:3b
```

> **Tip**: For machines with higher VRAM (8GB+), you can optionally pull larger models like `llama3.1:8b` or `mistral:7b`, then update `LLM_MODEL` in `.env`.

### Step 4: Verify Deployment
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

### 1. Run Only Infrastructure Services in Docker
```bash
docker compose up -d postgres ollama
```

### 2. Run Backend Locally
`> [!IMPORTANT]
> **Production Cloud Architecture on Vercel**:
> Vercel hosts both the **Next.js Frontend** and the **FastAPI Backend** as unified services in a single Vercel project using `vercel.json` edge rewrites.
> 
> Because serverless functions are ephemeral, production uses:
> 1. **Hosted PostgreSQL with pgvector** (e.g., Neon or Supabase free tiers).
> 2. **Hosted LLM API** (e.g., Groq free tier or OpenAI API) instead of local Ollama.
> 3. **Remote Embeddings** (OpenAI `text-embedding-3-small` with 384 dimensions) to avoid downloading 800MB PyTorch weights on serverless cold starts.

```
                         ┌──────────────────────────────────────────────┐
                         │               Vercel Project                 │
                         │                                              │
                         │   ┌────────────────┐    ┌────────────────┐   │
  Client Browser ───────▶│   │ Next.js        │    │ FastAPI        │   │
  (Single Domain)        │   │ Frontend (Web) │    │ Backend (API)  │   │
                         │   │ Root: frontend/│    │ Root: backend/ │   │
                         │   └────────────────┘    └────────┬───────┘   │
                         └──────────────────────────────────┼───────────┘
                                                            │
                                  ┌─────────────────────────┴─────────────────────────┐
                                  │                                                   │
                                  ▼                                                   ▼
                       ┌──────────────────────┐                           ┌──────────────────────┐
                       │ Cloud PostgreSQL +   │                           │ Hosted LLM & Embed   │
                       │ pgvector (Neon/      │                           │ (Groq / OpenAI API)  │
                       │ Supabase)            │                           └──────────────────────┘
                       └──────────────────────┘
```

---

## 4. Deploying OpenSource Copilot on Vercel (12-Step Guide)

Follow this step-by-step procedure to deploy the entire monorepo to Vercel.

### Step 1: Prerequisites
Before deploying, make sure you have:
- A [Vercel Account](https://vercel.com/signup)
- A GitHub account with the OpenCopilot repository pushed to your personal or organization profile
- A free cloud PostgreSQL database with `pgvector` enabled (see Step 2)
- An API key for an LLM provider:
  - [Groq Console](https://console.groq.com) (free tier recommended: `llama-3.3-70b-versatile`)
  - OR [OpenAI Platform](https://platform.openai.com) (`gpt-4o-mini` and `text-embedding-3-small`)

### Step 2: Provision Cloud PostgreSQL with pgvector
Create a free cloud PostgreSQL database:
- **Neon ([neon.tech](https://neon.tech))**: Sign up, create a project named `opencopilot`. Enable pgvector under Extensions or run in the Neon SQL Editor:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- **OR Supabase ([supabase.com](https://supabase.com))**: Create a new project, navigate to Database -> Extensions, and enable `vector`.

### Step 3: Format the Connection String
Obtain your connection URI from your database dashboard. Ensure it uses the `postgresql+asyncpg://` scheme required by SQLAlchemy's async engine:
```
postgresql+asyncpg://<username>:<password>@<host>:<port>/<database>?ssl=require
```
*(Replace `postgres://` or `postgresql://` with `postgresql+asyncpg://`)*.

### Step 4: Verify Repository Configuration
The project is pre-configured for Vercel Monorepo deployment with:
- `vercel.json` in the root directory defining `frontend` (Next.js) and `backend` (FastAPI) services.
- `backend/main.py` entrypoint exporting the FastAPI `app`.
- `frontend/lib/api.ts` configured with relative `/api` fallback for seamless same-origin routing.

### Step 5: Import Project in Vercel
1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Select your Git provider and import the **OpenCopilot** repository.
4. Keep the **Root Directory** as `./` (the repository root).

### Step 6: Verify Service Settings
Vercel automatically detects the configuration from `vercel.json`:
- `frontend` service: Framework preset **Next.js**, root directory `frontend/`.
- `backend` service: Python runtime with entrypoint `main:app`, root directory `backend/`.

### Step 7: Configure Environment Variables in Vercel
In the Vercel Project Settings under **Environment Variables**, add the following for **Production** and **Preview** environments:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enables production mode |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-xyz.neon.tech/opencopilot?ssl=require` | Hosted PostgreSQL URI |
| `AUTH_SECRET_KEY` | *(Run `openssl rand -hex 32`)* | Strong random 32+ char secret for JWT |
| `GITHUB_TOKEN` | `ghp_...` *(optional)* | Increases GitHub rate limit (60 -> 5,000 req/hr) |
| `LLM_PROVIDER` | `groq` *(or `openai`)* | Production AI provider |
| `LLM_MODEL` | `llama-3.3-70b-versatile` *(or `gpt-4o-mini`)* | Target AI model |
| `LLM_API_KEY` | `gsk_...` *(or `sk-...`)* | Your provider API key |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Hosted API endpoint |
| `EMBEDDING_PROVIDER` | `openai` | Remote embedding provider |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 384-dimension embedding model |
| `EMBEDDING_DIMENSION`| `384` | Vector dimension matching database schema |
| `EMBEDDING_API_KEY` | `sk-...` | OpenAI API key for embeddings |
| `CORS_ORIGINS` | `["https://your-project.vercel.app"]` | Allowed CORS origins (also supports comma-separated list) |
| `SKIP_DB_INIT` | `false` | Run database schema initialization on startup |

### Step 8: Deploy
1. Click **Deploy**.
2. Vercel will install dependencies for both the frontend (via npm) and the backend (via pip using `backend/requirements.txt`).
3. Wait for both builds to complete and the deployment status to show **Ready**.

### Step 9: Verify Core Endpoints
Once deployed, test your live Vercel domain (`https://<project-name>.vercel.app`):
1. **API Health**: `https://<project-name>.vercel.app/api/health` -> `{"status":"ok"}`
2. **Interactive Docs**: `https://<project-name>.vercel.app/docs` -> FastAPI Swagger UI
3. **Frontend Application**: `https://<project-name>.vercel.app/` -> Landing page

### Step 10: Database Schema Initialization
On the initial cold start with `SKIP_DB_INIT=false`, FastAPI automatically executes:
- `CREATE EXTENSION IF NOT EXISTS vector;`
- Table generation for `repositories`, `repository_chunks`, `users`, and `chat_sessions`.
- Backward-compatible schema migrations.

### Step 11: End-to-End Feature Verification
Verify all user-facing features on your live Vercel URL:
1. **User Authentication**: Register a new user at `/login` -> Verify JWT session creation.
2. **Repository Analysis**: Enter a public repository (e.g. `pallets/flask`) -> Verify tree, language breakdown, and statistics.
3. **AI Repository Analysis**: Request AI analysis -> Verify hosted LLM response.
4. **Issue Recommendations**: Browse issues with difficulty matching -> Verify developer skill profiling.
5. **Interactive AI Chat & RAG**: Ask questions about the codebase -> Verify context retrieval and streaming chat.
6. **Contribution Guide**: Generate step-by-step contribution guides for beginner issues.

### Step 12: Production Operations & Troubleshooting
- **Cold Starts**: Serverless functions initialize on demand. Database connection pooling is handled efficiently by `asyncpg`.
- **Function Execution Limits**: AI endpoints can take a few seconds; Vercel Hobby plan allows up to 60s maxDuration.
- **Log Inspection**: In the Vercel Dashboard, select your project -> **Logs** to view real-time runtime logs from both the frontend and backend.
---

## 5. Environment Variables Reference

| Variable | Default | Required | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Yes | PostgreSQL connection string with `asyncpg` driver |
| `POSTGRES_USER` | `postgres` | No | PostgreSQL user for Docker Compose |
| `POSTGRES_PASSWORD` | `postgres` | No | PostgreSQL password for Docker Compose |
| `POSTGRES_DB` | `opencopilot` | No | PostgreSQL database name |
| `POSTGRES_PORT` | `5432` | No | Host port for PostgreSQL |
| `LLM_PROVIDER` | `ollama` | Yes | LLM provider (`ollama`, `openai`, `groq`) |
| `LLM_BASE_URL` | `http://localhost:11434` | Yes | Base URL for LLM provider API |
| `LLM_MODEL` | `llama3.2:3b` | Yes | Target LLM model name |
| `LLM_API_KEY` | `""` | No | API key for external providers (e.g. OpenAI, Groq) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | No | Ollama endpoint URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | No | Ollama model identifier |
| `GITHUB_TOKEN` | `""` | No | Personal Access Token for GitHub API (raises rate limits) |
| `AUTH_SECRET_KEY` | *dev key* | **Yes (Prod)** | Secret key for JWT signing (minimum 32 characters) |
| `AUTH_ALGORITHM` | `HS256` | No | JWT algorithm |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | No | JWT session lifetime |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Yes | JSON list or comma-separated allowed origins |
| `ENVIRONMENT` | `development` | No | Environment mode (`development`, `production`, `testing`) |
| `EMBEDDING_PROVIDER` | `sentence_transformers` | No | Embedding provider (`sentence_transformers` or `openai`) |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | No | Embedding model name (`text-embedding-3-small` for OpenAI) |
| `EMBEDDING_DIMENSION` | `384` | No | Vector dimension (must match PostgreSQL schema) |
| `EMBEDDING_API_KEY` | `""` | No | API key for remote OpenAI embeddings |
| `SKIP_DB_INIT` | `false` | No | Skip DB auto-init on cold starts if tables exist |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api` | No | Backend API base (defaults to relative `/api` on Vercel) |

---

## 6. Operational Troubleshooting & FAQ

### Port 5432 or 8000 is already in use
If another PostgreSQL instance or web server is running locally:
```bash
# In .env, change host port bindings without altering container configurations:
POSTGRES_PORT=5433
BACKEND_PORT=8001
FRONTEND_PORT=3001
```

### Ollama responds with "model not found"
If you see an error indicating `llama3.2:3b` was not found:
```bash
docker compose exec ollama ollama pull llama3.2:3b
```

### Database migration / tables initialization
The backend automatically creates the `vector` extension and all required tables on startup via SQLAlchemy `init_db()`. If tables need to be manually inspected:
```bash
docker compose exec postgres psql -U postgres -d opencopilot -c "\dt"
```

### CORS error in browser console
Ensure that `CORS_ORIGINS` in the backend environment matches the exact origin of the frontend (including protocol and port). For example:
```ini
CORS_ORIGINS=["https://my-app.vercel.app","http://localhost:3000"]
```
