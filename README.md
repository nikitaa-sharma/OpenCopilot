# OpenSource Copilot – AI Contribution Assistant

OpenSource Copilot is a web application designed to help developers understand, navigate, and contribute to open-source GitHub repositories.

---

## Project Purpose
Finding where and how to start contributing to an open-source project can be daunting. Codebases are often large, documentation can be dense, and finding issues matched to one's skills is challenging. OpenSource Copilot bridges this gap by:
- Analyzing GitHub repositories on-demand.
- Summarizing technical architectures, frameworks, and core concepts.
- Classifying open GitHub issues and matching them to developer skill sets.
- Synthesizing tailored, step-by-step contribution guides for specific issues.
- Providing an interactive RAG-powered chat assistant capable of answering questions directly referencing repository code and documentation.

---

## Current Status & Roadmap

| Feature / Area | Status | Description |
| :--- | :--- | :--- |
| **Monorepo Foundation** | ✅ **Implemented** | Clean modular separation between Next.js frontend and FastAPI backend. |
| **Health Check API** | ✅ **Implemented** | `GET /api/health` returning service status. |
| **Database Foundation** | ✅ **Implemented** | PostgreSQL configuration, connection layer, and entity models planned. |
| **Replaceable AI Interface** | ✅ **Implemented** | Abstract `LLMProvider` interface ready for local (Ollama) or hosted APIs. |
| **Frontend UI Shell** | ✅ **Implemented** | App Router, responsive hero, repository input, and modular feature placeholders. |
| **TypeScript & Domain Types** | ✅ **Implemented** | Shared domain contracts across frontend and backend schemas. |
| **GitHub REST API Integration** | ✅ **Implemented (Phase 3)** | Live repository metadata, languages, README, and open issues via GitHub REST API. Async `httpx` service, URL parser, PR filtering, error handling, optional token auth. |
| **Repository Tree & Code Ingestion** | ✅ **Implemented (Phase 4)** | Recursive Git tree retrieval, file classification, language detection, on-demand file content with base64 decoding, safety limits, batch ingestion endpoint. Read-only — no code execution. |
| **AI Architecture Analysis & LLM Provider** | ✅ **Implemented (Phase 5)** | Replaceable LLM abstraction with local Ollama provider. Deterministic repository context builder (prioritizing README, configs, entry points, source files), Pydantic structured validation, interactive architecture dashboard. Zero paid API keys required. |
| **AI Issue Analysis & Recommendations**| ✅ **Implemented (Phase 6)** | Grounded AI analysis for real GitHub issues. Deterministic issue context extraction, candidate files with verification guardrails, AI estimates for difficulty and required skills, step-by-step investigation guides, and explicit Observed vs Inferred vs Unknown evidence breakdown. |
| **Repository RAG Pipeline Foundation** | ✅ **Implemented (Phase 7)** | Deterministic code document loader, language-aware semantic chunker (Python, Markdown, YAML), exact & subword keyword retriever with path boosting, bounded context builder, and dedicated retrieval/context endpoints (`/rag/retrieve`, `/rag/context`). |
| **Vector Embeddings & Semantic Search** | ✅ **Implemented (Phase 8)** | Local sentence-transformers embeddings (BAAI/bge-small-en-v1.5, 384-dim, CPU), PostgreSQL + pgvector persistence, incremental SHA-256 chunk hashing & caching, semantic cosine similarity retrieval, automatic keyword fallback guardrail, and dedicated API endpoints (`/rag/index`, `/rag/vector-search`). |
| **Repository-Aware AI Chat** | ✅ **Implemented (Phase 9)** | Grounded RAG-powered chat (`POST /chat`). Retrieves context via pgvector semantic search with automatic keyword fallback, builds bounded prompt, queries Ollama LLM, strictly validates cited sources against actual retrieved chunks (never trusts hallucinated paths), and returns structured answer with verified evidence. Frontend chat UI with source cards, retrieval mode badges, loading states, and in-memory message history. |
| **Developer Skill Profile & Recommendations** | ✅ **Implemented (Phase 10)** | Developer skill profile (languages, frameworks, tools, domains, experience level, interests). Conservative deterministic normalization. Grounded skill matching against issue requirements, candidate files, and repo stack. Separate AI difficulty estimate vs. skill match score. Explicit match reasons, skill gaps, and learning opportunities. Endpoints (`/profile/skills`, `/repositories/issues/recommend`). Interactive frontend profile editor & recommended issues dashboard. |
| **AI Contribution Guide** | ✅ **Implemented (Phase 11)** | Grounded, step-by-step contribution guides for GitHub issues. Strict citation verification against retrieved chunks, code areas to inspect, testing/doc plans, pre-flight PR checklist. |
| **Authentication & User Accounts** | ✅ **Implemented (Phase 12)** | JWT bearer token authentication, bcrypt password hashing, persistent PostgreSQL user and profile storage, with graceful backward-compatible unauthenticated fallback. |
| **Security & Reliability Hardening** | ✅ **Implemented (Phase 13)** | Path traversal defense (`validate_repository_path`), prompt injection defense tags, bounded schemas, global sanitized error handling, 57 security tests covering 26 attack vectors (317 total tests). |
| **Docker, CI/CD & Deployment** | ✅ **Implemented (Phase 14)** | Multi-stage production Dockerfiles, 4-tier Docker Compose orchestration (`postgres` + `pgvector`, `ollama`, `backend`, `frontend`), automated GitHub Actions CI/CD pipeline, and complete cloud deployment guides. |
| **Final UI/UX & Dark/Light Mode** | ✅ **Implemented (Phase 15)** | Seamless dark/light theme switching with `next-themes`, CSS token system, WCAG-compliant contrast, responsive navigation, portfolio-ready documentation, and complete verification suite. |


---

## Technology Stack

- **Frontend**:
  - **Framework**: Next.js (App Router)
  - **Language**: TypeScript (Strict Mode)
  - **Styling**: Tailwind CSS
  - **UI Architecture**: Modular accessible component primitives (inspired by shadcn/ui pattern)
  - **Icons**: Lucide React
- **Backend**:
  - **Framework**: Python 3.10+ FastAPI
  - **Data Validation & Serialization**: Pydantic v2
  - **ORM & Database Toolkit**: SQLAlchemy 2.0
  - **Database Driver**: asyncpg / psycopg2 for PostgreSQL (pgvector planned)
  - **Settings Management**: pydantic-settings & python-dotenv
  - **Server**: Uvicorn
  - **Testing**: Pytest & HTTPX
- **Version Control**: Git & GitHub

---

## System Architecture

```text
                               ┌─────────────────────────────┐
                               │   Next.js 14 Web Frontend   │
                               │  (TypeScript, Tailwind CSS, │
                               │   next-themes, Lucide UI)   │
                               └──────────────┬──────────────┘
                                              │ HTTP / JSON
                                              ▼
                               ┌─────────────────────────────┐
                               │     FastAPI API Gateway     │
                               │ (Dependency Injection, CORS,│
                               │  Sanitized Error Handlers)  │
                               └───┬──────────┬──────────┬───┘
                                   │          │          │
         ┌─────────────────────────┘          │          └─────────────────────────┐
         ▼                                    ▼                                    ▼
┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
│  GitHub Service  │               │ RAG & Embeddings │               │   LLM Service    │
│  (httpx Client,  │               │ (pgvector + CPU  │               │ (Ollama Provider,│
│   Rate Limiter,  │               │  bge-small-en,   │               │  Bounded Context │
│  Tree Ingestion) │               │ Keyword Fallback)│               │ Prompt Injection)│
└────────┬─────────┘               └────────┬─────────┘               └────────┬─────────┘
         │ HTTPS                            │ SQL / Vector                     │ HTTP
         ▼                                  ▼                                  ▼
┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
│  GitHub REST API │               │    PostgreSQL    │               │  Local Ollama /  │
│  (api.github.com)│               │  + pgvector EXT  │               │ llama3.2:3b Model│
└──────────────────┘               └──────────────────┘               └──────────────────┘
```

---

## RAG Retrieval Pipeline Flow

```text
[Repository Source Code / Docs]
               │
               ▼
[Semantic Language Chunker] (Python AST, Markdown, YAML)
               │
               ▼
[SHA-256 Incremental Hashing] (Avoid re-indexing unchanged chunks)
               │
               ├─────────────────────────────────────────┐
               ▼                                         ▼
[Vector Embeddings (bge-small-en-v1.5)]         [Keyword Inverted Index]
               │                                         │
               ▼                                         ▼
[pgvector Cosine Similarity Search]             [Exact & Subword Match]
               │                                         │
               └────────────────────┬────────────────────┘
                                    │
                                    ▼
                        [Automatic Fallback Engine]
                    (pgvector -> Keyword if unindexed)
                                    │
                                    ▼
                        [Bounded Context Builder]
                     (Character budget & truncation)
                                    │
                                    ▼
                     [Grounded Prompt Construction]
                    (Untrusted context isolation tag)
                                    │
                                    ▼
                        [Ollama LLM Generation]
                                    │
                                    ▼
                     [Source Verification Guardrail]
                (Filter out non-retrieved / phantom citations)
                                    │
                                    ▼
              [Verified Structured Answer with Evidence Cards]
```

---

## Monorepo Project Structure

```
opensource-copilot/
├── frontend/                     # Next.js TypeScript application
│   ├── app/                      # App router (layout, landing page, styles)
│   ├── components/               # Modular UI and layout components
│   │   ├── layout/               # Navbar, Footer, ThemeToggle
│   │   ├── sections/             # Hero, Analyzer, Overview, Issues, Chat
│   │   └── ui/                   # Reusable button, input, card, badge
│   ├── lib/                      # Utilities (cn class merger, API client)
│   ├── types/                    # Domain TypeScript interfaces (incl. GitHub API types)
│   ├── public/                   # Static assets
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                      # FastAPI Python application
│   ├── app/
│   │   ├── api/                  # Route handlers & endpoints
│   │   │   └── v1/
│   │   │       ├── endpoints/    # Health, Repositories, Profile, Auth
│   │   │       └── router.py     # Main API router
│   │   ├── chat/                 # Repository chat domain
│   │   │   ├── models.py         # ChatQuestion, ChatSource, ChatAnswer
│   │   │   ├── context.py        # RAG context retrieval for chat
│   │   │   └── service.py        # RepositoryChatService orchestration
│   │   ├── core/                 # App configuration and database setup
│   │   ├── embeddings/           # SentenceTransformer embedding provider
│   │   ├── models/               # SQLAlchemy declarative entity definitions
│   │   ├── prompts/              # Grounded system prompts (injection defended)
│   │   ├── rag/                  # RAG pipeline: chunker, retriever, indexer
│   │   ├── schemas/              # Pydantic data schemas
│   │   ├── services/             # Business logic, GitHub service, file filter
│   │   ├── repositories/         # Database access repository pattern
│   │   └── main.py               # FastAPI application entrypoint
│   ├── tests/                    # Backend automated tests (317 tests)
│   └── requirements.txt
│
├── docs/                         # Technical documentation & architecture
│   └── architecture.md
├── .gitignore                    # Monorepo ignore rules
├── .env.example                  # Environment template
└── README.md
```

---

## Quick Start with Docker Compose (Recommended)

Run the entire application stack (PostgreSQL + pgvector, Ollama, FastAPI Backend, Next.js Frontend) with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/opencopilot.git
cd opencopilot

# 2. Copy the environment template
cp .env.example .env

# 3. Start all services in the background
docker compose up -d --build

# 4. Pull the recommended local LLM model (one-time setup)
docker compose exec ollama ollama pull llama3.2:3b
```

Once started:
- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

For full deployment instructions, hybrid workflows, and production setup, see the [Deployment & Operations Guide](docs/deployment.md).

---

## Deploy to Vercel (Monorepo Deployment)

OpenSource Copilot is pre-configured for unified deployment on **Vercel** as a monorepo. Both the Next.js frontend and the FastAPI backend are deployed together in a single Vercel project with edge path rewrites (`/api/*` -> FastAPI backend, `/*` -> Next.js frontend).

### Quick Deployment Steps
1. Push your repository to GitHub.
2. Provision a cloud PostgreSQL database with `pgvector` enabled (e.g., [Neon](https://neon.tech) or [Supabase](https://supabase.com)).
3. Import the repository in [Vercel](https://vercel.com) (keep Root Directory as `./`).
4. Configure environment variables in Vercel Dashboard:
   - `ENVIRONMENT=production`
   - `DATABASE_URL=postgresql+asyncpg://...`
   - `AUTH_SECRET_KEY=<generate-with-openssl-rand-hex-32>`
   - `LLM_PROVIDER=groq` (or `openai`)
   - `LLM_API_KEY=<your-api-key>`
   - `LLM_MODEL=llama-3.3-70b-versatile` (or `gpt-4o-mini`)
   - `EMBEDDING_PROVIDER=openai`
   - `EMBEDDING_API_KEY=<your-openai-api-key>`
5. Click **Deploy**. Both services build and deploy under a single unified URL.

Detailed 12-step instructions and troubleshooting are available in [docs/deployment.md](docs/deployment.md#4-deploying-opensource-copilot-on-vercel-12-step-guide).

---

## Manual Local Development Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- PostgreSQL with pgvector (or use `docker compose up -d postgres`)

---

### Backend Setup

1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local environment file:
   ```bash
   cp .env.example .env
   ```

5. Run automated tests:
   ```bash
   pytest
   ```

6. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

7. Verify the service is running:
   - Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
   - Interactive Swagger API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Frontend Setup

1. Open another terminal and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create your local environment file:
   ```bash
   cp .env.example .env.local
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

5. Open your browser at [http://localhost:3000](http://localhost:3000).

### Local Ollama Setup (Phase 5 - AI Analysis)

> **Note**: Ollama is **100% optional** for application startup. If Ollama is offline or not installed, the application and repository explorer continue to function normally.

1. **Install Ollama**: Download and install from [ollama.com](https://ollama.com/).
2. **Start Ollama Service**:
   ```bash
   ollama serve
   ```
3. **Pull the Default Model**:
   ```bash
   ollama pull llama3.2:3b
   ```
   *(Or run `ollama run llama3.2:3b` to pull and test the model interactively).*
4. **Analyze with AI**: With FastAPI and Next.js running, submit any public GitHub repository URL. The system will build a prioritized context budget and generate grounded architectural insights.

---

## Environment Variables

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/opencopilot` |
| `GITHUB_TOKEN` | GitHub Personal Access Token (optional, for higher rate limits) | `ghp_...` or empty |
| `GITHUB_API_BASE_URL` | Base URL for GitHub REST API | `https://api.github.com` |
| `GITHUB_REQUEST_TIMEOUT` | Timeout in seconds for GitHub API requests | `15` |
| `MAX_TREE_ITEMS` | Max items processed from recursive Git tree | `10000` |
| `MAX_SOURCE_FILES` | Max source/doc files ingested in batch operation | `100` |
| `MAX_FILE_SIZE_BYTES` | Max size per individual file for content retrieval | `102400` (100 KB) |
| `MAX_TOTAL_CODE_BYTES` | Max total code ingested per repository | `2097152` (2 MB) |
| `LLM_PROVIDER` | Replaceable AI provider (`ollama`, `openai`, `anthropic`, `local`) | `ollama` |
| `OLLAMA_BASE_URL` | Base URL for local Ollama HTTP API | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name identifier in Ollama | `llama3.2:3b` |
| `LLM_TEMPERATURE` | Sampling temperature for AI generation | `0.2` |
| `LLM_MAX_OUTPUT_TOKENS` | Max output tokens generated by LLM | `4096` |
| `LLM_REQUEST_TIMEOUT` | Timeout in seconds for LLM generation | `120.0` |
| `AI_MAX_CONTEXT_CHARS` | Maximum character budget for AI context | `60000` |
| `AI_MAX_FILES_IN_CONTEXT` | Maximum files included in AI context | `15` |
| `AI_MAX_FILE_CHARS` | Maximum character limit per individual file before truncation | `6000` |
| `CORS_ORIGINS` | Allowed frontend origins for CORS | `["http://localhost:3000"]` |
| `NEXT_PUBLIC_API_BASE_URL` | API endpoint URL accessible from frontend | `http://localhost:8000/api` |


---

## Developer Skill Profile & Personalized Recommendations (Phase 10)

Phase 10 provides transparent, personalized issue recommendations based on a lightweight developer skill profile:

- **Developer Skill Profile**: Captures `programming_languages`, `frameworks`, `tools`, `domains`, `experience_level`, and `interests`.
- **Deterministic Skill Normalization**: Normalizes aliases (e.g., `"js"` → `"JavaScript"`, `"postgres"` → `"PostgreSQL"`) conservatively and preserves unknown skills without discarding them.
- **Skill Match vs. AI Difficulty Estimate**:
  - **Skill Match Score** (0% to 100%): Measures the proportion of analyzed requirements that overlap with the developer's declared skills. It does *not* claim to measure developer competency.
  - **AI Difficulty Estimate** (Beginner, Intermediate, Advanced, Unknown): Intrinsic technical complexity estimated by AI independently of the user's skill set.
- **Transparent Match Reasons & Skill Gaps**: Explains *why* each issue matched (required skill overlap, candidate file languages, repo technology alignment), clearly indicates missing skills (*skill gaps*), and highlights constructive *learning opportunities*.
- **Deterministic Recommendation Sorting**: Ordered by match score descending, with issue number ascending as a deterministic tie-breaker. Strictly avoids subjective labeling such as "best", "winner", or "easiest".
- **Current Profile Limitations**: Profile state is managed in-memory per session with local storage synchronization. No authentication or persistent user database accounts are introduced in Phase 10.

---

## Grounded AI Contribution Guide (Phase 11)

Phase 11 introduces repository-specific, AI-powered contribution guides for targeted GitHub issues:

- **Strict Source Grounding**: Recommendations are strictly grounded in repository code retrieved via pgvector / keyword RAG. Hallucinated file paths or line ranges that do not exist in retrieved chunks are automatically filtered out.
- **Structured Implementation Blueprint**:
  - **Issue Understanding**: Plain-language summary, problem root cause / symptoms, and expected resolution behavior.
  - **Prerequisites & Environment**: Runtime requirements, developer tools, and required domain knowledge.
  - **Relevant Repository Files**: Validated source files to inspect with maintainer-annotated roles (`source`, `test`, `config`, `doc`) and reasons.
  - **Sequential Implementation Plan**: Numbered step-by-step instructions referencing specific files.
  - **Code Areas to Inspect**: Targeted classes, methods, or modules with maintainer checklist items.
  - **Testing Plan**: Specific test suites (`unit`, `integration`, `regression`, `manual`) and test file commands.
  - **Documentation Plan**: Docstrings, tutorial, and configuration documentation updates needed.
  - **Pull Request Pre-Flight Checklist**: Interactive checklist covering test execution, linting, and issue linkage.
  - **Contributor Learning Opportunities**: Concrete skills, patterns, and protocols learned from solving the issue.
  - **Uncertainties & Caveats**: Explicitly notes unindexed files or areas requiring maintainer feedback.
- **API Endpoint**: `POST /api/v1/repositories/issues/contribution-guide`

---

## Authentication & User Accounts (Phase 12)

Phase 12 implements persistent user accounts and session authentication:

- **JWT Bearer Token Authentication**: Secure token issuance using PyJWT and HS256 algorithm with configurable expiration.
- **bcrypt Password Security**: Passwords are securely hashed with bcrypt using automatically generated unique salts. Plaintext passwords are never stored, logged, or returned in API responses.
- **PostgreSQL User Accounts & Profile Persistence**:
  - `users` table: User ID, email, password hash, display name, timestamps.
  - `developer_profiles` table: Persists declared developer skills, frameworks, tools, and interests across sessions and devices.
- **Graceful Backward Compatibility**:
  - Fully backward compatible: All core repository analysis, chat, issue recommendations, and contribution guide features remain accessible without authentication.
  - Optional auth dependency: If an access token is provided, developer profile changes persist to PostgreSQL; otherwise, the in-memory fallback is used.
- **Frontend Auth Integration**:
  - `AuthProvider` context and `useAuth()` hook for state and token hydration.
  - Dedicated `/login` and `/register` pages with form validation and loading feedback.
  - Auth-aware Navbar displaying user credentials and Logout action or Login/Sign Up links.
  - Developer Skill Profile displaying live account synchronization status.
- **API Endpoints**:
  - `POST /api/v1/auth/register`: Create a new user account (201 Created).
  - `POST /api/v1/auth/login`: Authenticate credentials and receive a JWT token (200 OK).
  - `GET /api/v1/auth/me`: Inspect current authenticated user information (200 OK).
  - `POST /api/v1/auth/logout`: Revoke client session (200 OK).

---

## Security, Hardening & Reliability (Phase 13)

Phase 13 hardens OpenSource Copilot across backend services, API endpoints, and LLM integrations:

- **Path Traversal Protection**:
  - `validate_repository_path()` utility enforces strict path normalization across file operations and GitHub fetching.
  - Blocks null byte injection (`\x00`), traversal segments (`../`, `..\`, `..%2f`, `..%5c`, double-encoded `%252f`), absolute filesystem paths (`/etc/passwd`, `C:\Windows`), and paths exceeding 500 characters.
  - Integrated into `github_service.fetch_file_content` and `repository_file_filter.should_ignore_path`.

- **Prompt Injection Defense**:
  - All AI system prompts (`repository_chat`, `contribution_guide`, `issue_analysis`, `repository_analysis`) contain explicit injection defense directives.
  - Repository code and issue bodies are strictly isolated within `=== UNTRUSTED REPOSITORY CONTEXT ===` demarcation tags.
  - The model is instructed to treat all repository and issue contents strictly as reference data and never follow instructions, system overrides, or roleplay requests contained within them.

- **Input Validation & Payload Size Bounds**:
  - Bounded input schemas: Questions (max 2,000 chars), queries (max 1,000 chars), repository URLs (max 500 chars), and branch names (max 100 chars).
  - Parameter bounds: `top_k` restricted to `1 <= top_k <= 20`, issue numbers required to be positive (`>= 1`).
  - Developer skill profiles enforce limits on array size (max 50 entries) and string length (max 100 chars per entry).

- **Global Error Handling & Sanitization**:
  - Application-level exception handler captures unexpected exceptions, logs full stack traces internally for diagnostics, and returns generic `500 Internal Server Error` payloads.
  - Prevents database connection strings, passwords, file paths, or internal tracebacks from leaking to API clients.

- **Comprehensive Security Test Suite**:
  - 57 dedicated security hardening tests in `backend/tests/test_security_hardening.py` covering all 26 security scenarios:
    - JWT authentication validation (invalid, expired, malformed, missing, inactive user).
    - Cross-user data isolation (User A vs. User B).
    - Path traversal and absolute path rejection.
    - URL validation and malicious host blocking.
    - Oversized input handling and boundary conditions.
    - Prompt injection defense verification.
    - Hallucinated source and line range filtering.
    - Malformed LLM JSON recovery.
    - External service resilience (Ollama timeout/offline, GitHub 403/404/timeouts).
    - Database failure response sanitization.
  - **Total Backend Test Coverage**: 317 tests passing with 0 failures.

---

## Docker, CI/CD & Deployment Preparation (Phase 14)

Phase 14 provides complete, reproducible containerization, multi-service orchestration, automated GitHub Actions CI/CD, and production deployment guides:

- **Multi-Stage Production Dockerfiles**:
  - `backend/Dockerfile`: Minimal `python:3.11-slim` image, non-root `appuser` (UID 10001), built-in health check via FastAPI `/api/health`, dependencies installed with `--no-cache-dir`.
  - `frontend/Dockerfile`: Next.js production build using `node:20-alpine` across three isolated stages (`deps` -> `builder` -> `runner`), non-root `nextjs` user (UID 1001), and parameterized `NEXT_PUBLIC_API_BASE_URL`.

- **Multi-Service Docker Compose Topology (`docker-compose.yml`)**:
  - **`postgres`**: PostgreSQL 16 with `pgvector` extension and persistent `pgvector_data` volume.
  - **`ollama`**: Local LLM engine container with persistent `ollama_data` volume.
  - **`backend`**: FastAPI API server with dependency health checks on `postgres` and `ollama`.
  - **`frontend`**: Next.js client UI connected to backend.
  - **Isolated Bridge Network**: `opencopilot_net` decouples internal container communication from host port exposure.

- **Continuous Integration Pipeline (`.github/workflows/ci.yml`)**:
  - **Backend Job**: Automatically spins up a PostgreSQL + pgvector service container, sets up Python 3.11 with pip caching, and runs the complete 317-test Pytest suite on every push and pull request.
  - **Frontend Job**: Sets up Node.js 20 with npm caching, verifies strict TypeScript typing (`tsc --noEmit`), runs ESLint, and compiles a Next.js production build.
  - **Docker Validation Job**: Validates `docker compose config` syntax and verifies buildability of backend and frontend images.
  - **Secret Hygiene Audit**: Verifies that no development `.env` files with credentials or keys are committed to Git.

- **Production & Cloud Deployment Guide**:
  - Detailed in [`docs/deployment.md`](docs/deployment.md).
  - Includes local Docker Compose setup, hybrid local-Docker workflows, step-by-step free/low-cost cloud deployment (Vercel + Render + Supabase/Neon + Groq), and transparent hardware analyses regarding LLM memory constraints on cloud free tiers.

---

## Final UI/UX, Dark/Light Mode & Portfolio Polish (Phase 15)

Phase 15 elevates OpenSource Copilot to a production-grade, portfolio-ready developer application:

- **Complete Dark / Light Mode System**:
  - Powered by `next-themes` with automatic system preference detection (`prefers-color-scheme`) and persistent `localStorage` synchronization.
  - Zero hydration flicker via `suppressHydrationWarning` and dynamic client-side mount guards.
  - Interactive Sun/Moon toggle button accessible in both desktop and mobile navigation headers.

- **Unified Semantic Token Architecture**:
  - Full HSL-based CSS variable system supporting light mode (clean crisp white/slate canvas) and dark mode (sleek deep blue/slate palette).
  - High-contrast, WCAG AA-compliant dual theme utility classes across all components (e.g., `text-emerald-600 dark:text-emerald-400`, `text-amber-600 dark:text-amber-400`).
  - Seamless border, card, and backdrop blur adjustments for elevated visual hierarchy.

- **Polished User Experience**:
  - Removal of legacy phase placeholders and developer debug buttons.
  - Streamlined empty and loading states with actionable suggestions and sample repository quick-picks.
  - Responsive design optimized across mobile (375px), tablet (768px), and desktop (1280px+) viewport breakpoints.

---

## Limitations & System Boundaries

To maintain technical integrity and set clear expectations for evaluation and deployment, the following boundaries and constraints apply:

1. **Repository Scope & Access**:
   - Analyzes **public GitHub repositories** by default. Private repositories require an authenticated GitHub Personal Access Token (`GITHUB_TOKEN`) with `repo` scope.
   - Large monorepos (>10,000 files) or single files exceeding 100 KB are bounded or truncated according to `MAX_TREE_ITEMS` and `MAX_FILE_SIZE_BYTES` configuration to preserve memory and performance.

2. **GitHub API Rate Limits**:
   - Unauthenticated GitHub API calls are subject to GitHub's rate limit of 60 requests per hour per IP.
   - Supplying a personal access token via `GITHUB_TOKEN` increases this limit to 5,000 requests per hour.

3. **Read-Only Operation & Code Execution**:
   - OpenSource Copilot is strictly a **read-only architectural analysis and recommendation engine**.
   - It **never** executes untrusted repository code, installs npm/pip packages from target repositories, or writes unauthorized commits/pull requests to user repositories.

4. **Local LLM Hardware Requirements**:
   - The default local AI provider runs `llama3.2:3b` via Ollama. This requires approximately 4 GB to 8 GB of available system RAM.
   - If local Ollama is offline or unavailable, the application gracefully degrades to deterministic analysis mode, keyword-based RAG retrieval, and cached architecture cards without crashing.

5. **RAG Context Boundedness**:
   - Retrieval is bounded by character budgets (`AI_MAX_CONTEXT_CHARS`, default 60,000 chars) and file limits (`AI_MAX_FILES_IN_CONTEXT`, default 15) to prevent context window overflow and maintain low latency.
   - Hallucinated source citations or non-retrieved line ranges generated by LLMs are strictly intercepted and filtered out before returning responses to the user.

---

## Contributing & License

OpenSource Copilot is built for open-source developers worldwide. Contributions are welcome!
Licensed under the [MIT License](LICENSE).


