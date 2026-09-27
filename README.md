# OpenSource Copilot – AI Contribution Assistant

OpenSource Copilot is an intelligent, local developer assistant designed to help developers understand, navigate, and contribute to open-source GitHub repositories.

---

## 1. Overview

Getting started with an open-source project is often overwhelming. OpenSource Copilot provides a unified local interface where developers enter any public GitHub repository URL, and the system autonomously analyzes it to:
- Explore project structure, languages, activity, and core concepts.
- Ingest repository code and documentation into a vector database with pgvector.
- Inspect and classify open GitHub issues according to technical difficulty.
- Match issues against the developer's personal skill profile with transparent scoring and skill gap analysis.
- Provide interactive, RAG-grounded codebase chat that cites verified source files.
- Synthesize actionable, step-by-step contribution guides for targeted issues with pre-flight pull request checklists.

OpenSource Copilot runs **completely locally** using Docker, PostgreSQL with pgvector, Ollama (`llama3.2:3b`), and Sentence Transformers (`BAAI/bge-small-en-v1.5`).

---

## 2. Problem Statement

New open-source contributors and developers entering unfamiliar codebases frequently face severe friction:
1. **Steep Architectural Learning Curve**: Large repositories contain thousands of files with complex dependency trees and implicit patterns that documentation rarely explains.
2. **Dense or Incomplete Documentation**: Documentation is often outdated, incomplete, or assumes deep prior knowledge of internal conventions.
3. **Issue Discovery Dilemma**: Finding suitable issues is difficult. Labels like `"good first issue"` vary wildly in complexity across projects and often mismatch a developer's specific skillset.
4. **Execution Uncertainty**: Even after identifying an issue, beginners struggle to identify which files to modify, how to run relevant test suites, and how to verify their solution before submitting a pull request.

---

## 3. Objectives

OpenSource Copilot addresses these friction points through five core objectives:
- **Repository Understanding**: Extract repository metadata, analyze directory trees, classify file types, and produce structured architectural overviews.
- **AI Issue Analysis**: Inspect open GitHub issues, extract technical requirements, identify candidate files to edit, and estimate complexity independently of contributor skill.
- **Personalized Issue Recommendation**: Map developer declared skills (languages, frameworks, tools) against issue requirements to score relevance, illuminate missing technologies (skill gaps), and highlight learning opportunities.
- **RAG-Based Repository Q&A**: Provide grounded conversational Q&A over repository source code and documentation using semantic vector search with keyword fallbacks.
- **Step-by-Step Contribution Guidance**: Synthesize concrete implementation blueprints for specific issues, detailing relevant files, inspection checklists, test suites, and pre-flight PR checks.
- **Zero-Cloud Dependency**: Operate locally with no mandatory paid API keys or cloud subscriptions.

---

## 4. Key Features

The application delivers the following fully implemented capabilities:

- **GitHub Repository Analysis**: Live metadata extraction (stars, forks, open issues, license, default branch, topics) via the GitHub REST API.
- **Repository Metadata & File-Tree Analysis**: Recursive Git tree inspection with automatic file classification (source, documentation, configuration, tests) and file-type recognition.
- **Source-Code Ingestion**: Safe, bounded batch ingestion of repository code and documentation with strict size ceilings (100 files, 100 KB/file, 2 MB total).
- **AI Architecture Analysis**: Grounded technical breakdown identifying primary frameworks, design patterns, core components, and application entrypoints.
- **AI Issue Analysis**: Grounded evaluation of open GitHub issues with deterministic context extraction and verified candidate files.
- **Difficulty Classification**: Intrinsic technical difficulty estimation (Beginner, Intermediate, Advanced) based on scope of changes, architectural impact, and prerequisites.
- **Developer Skill Profile**: Customizable developer profile tracking languages, frameworks, developer tools, domains, experience level, and interests with deterministic alias normalization.
- **Personalized Issue Recommendations**: Transparent, deterministic matching between developer skills and issue requirements, showing match percentage, matching reasons, and constructive skill gaps.
- **RAG-Based Repository Chat**: Grounded conversational assistant answering codebase queries with verified file citations and code references.
- **pgvector Vector Search with Keyword Fallback**: 384-dimensional cosine similarity retrieval via PostgreSQL pgvector, with automatic fallback to exact and subword keyword retrieval if unindexed.
- **AI Contribution Guide**: Structured step-by-step blueprints for resolving issues, covering environment prerequisites, code areas to inspect, testing strategy, and PR checklists.
- **User Authentication & Profile Persistence**: Secure JWT bearer tokens and bcrypt password hashing with PostgreSQL profile persistence and backward-compatible unauthenticated access.
- **Security Validation & Injection Protection**: Strict path-traversal protection, GitHub URL validation, bounded request schemas, sanitized error reporting, and prompt-injection defense with untrusted context isolation tags.

---

## 5. System Workflow

The following flowchart illustrates the complete operational workflow from repository input to personalized guidance and chat:

```mermaid
flowchart TD
    User(["Developer"]) --> EnterRepo["Enter GitHub Repository URL\n(e.g., pallets/flask)"]
    EnterRepo --> GitHubAPI["GitHub REST API\n(api.github.com)"]
    
    GitHubAPI --> RepoData["Repository Metadata, README,\nOpen Issues & Git File Tree"]
    RepoData --> IngestFilter["Source Ingestion & Safety Filter\n(Limit: 100 files, 100 KB/file)"]
    
    IngestFilter --> Chunker["Language-Aware Chunker\n(AST & Line Boundaries)"]
    Chunker --> Hasher["SHA-256 Incremental Hasher\n(Skip Unchanged Chunks)"]
    Hasher --> Embedder["Sentence Transformers\n(BAAI/bge-small-en-v1.5)"]
    
    Embedder --> PGVector[("PostgreSQL 16 + pgvector\n(384-dim Embeddings)")]
    
    DevProfile["Developer Skill Profile\n(Languages, Tools, Level)"] --> SkillMatcher["Deterministic Skill Matcher"]
    RepoData -.->|"Issue Requirements"| SkillMatcher
    SkillMatcher --> RecIssues["Personalized Recommended Issues\n(Match Score %, Skill Gaps)"]
    
    UserQuery["User Query / Selected Issue"] --> RAGRetrieval["Hybrid RAG Retrieval\n(pgvector Cosine Search + Keyword Fallback)"]
    PGVector --> RAGRetrieval
    
    RAGRetrieval --> ContextBuilder["Bounded Context Builder\n(=== UNTRUSTED CONTEXT ===)"]
    ContextBuilder --> OllamaLLM["Local Ollama LLM\n(llama3.2:3b)"]
    
    OllamaLLM --> Guardrail["Citation Verification Guardrail\n(Strip Non-Retrieved Sources)"]
    
    Guardrail --> FeaturesOut{"Output Generation"}
    FeaturesOut --> ArchAnalysis["Architectural Overview Dashboard"]
    FeaturesOut --> GroundedChat["Grounded Codebase Chat with Citations"]
    FeaturesOut --> ContribGuide["Step-by-Step Contribution Guide"]
    
    RecIssues --> FrontendView["Next.js Responsive Web UI"]
    ArchAnalysis --> FrontendView
    GroundedChat --> FrontendView
    ContribGuide --> FrontendView
    FrontendView --> User
```

---

## 6. Architecture

OpenSource Copilot follows a modular, decoupled architecture where the Next.js frontend communicates with the FastAPI backend, backed by PostgreSQL + pgvector and a local Ollama instance:

```mermaid
flowchart TD
    subgraph FrontendLayer["Presentation Layer (Port 3000)"]
        NextJS["Next.js 14 App Router\n(React, TypeScript, Tailwind CSS, next-themes)"]
    end

    subgraph BackendLayer["API & Application Layer (Port 8000)"]
        FastAPI["FastAPI REST API Gateway\n(Dependency Injection, CORS, Error Sanitization)"]
        
        subgraph ServicesLayer["Domain Services Layer"]
            GitHubService["GitHub Service\n(httpx, Tree Traversal, Rate Limiter)"]
            LLMService["AI / LLM Service\n(Ollama Provider, Prompt Builder)"]
            IssueService["Issue Analysis Service\n(Difficulty Estimator, Context Builder)"]
            SkillService["Skill Matching Service\n(Normalizer, Score Calculator)"]
            GuideService["Contribution Guide Service\n(Blueprint Synthesizer, Verification)"]
            RAGService["RAG Pipeline Service\n(Chunker, Retriever, Indexer)"]
        end
    end

    subgraph StorageLayer["Data & Inference Layer"]
        Postgres[("PostgreSQL 16 + pgvector\n(Port 5432/5433 | Users, Profiles, Vectors)")]
        OllamaEngine["Local Ollama Engine\n(Port 11434 | llama3.2:3b)"]
    end

    NextJS -->|"HTTP / JSON (/api/*)"| FastAPI
    FastAPI --> ServicesLayer
    
    GitHubService -->|"HTTPS Requests"| RemoteGitHub["GitHub REST API"]
    RAGService --> Postgres
    SkillService --> Postgres
    GuideService --> RAGService
    LLMService --> OllamaEngine
```

---

## 7. RAG Pipeline

The Retrieval-Augmented Generation (RAG) pipeline indexes codebase documents into vector embeddings and extracts relevant context with strict grounding:

```mermaid
flowchart LR
    RepoFiles["Repository Source Code & Docs\n(Python, Markdown, YAML)"] --> FileFilter["File Filter & Safety Scanner\n(Skip Binary, Vendor & Minified Files)"]
    FileFilter --> Chunker["Structure-Aware Chunker\n(AST & Function/Class Boundaries)"]
    Chunker --> SentenceTrans["Sentence Transformers\n(Local CPU Ingestion)"]
    SentenceTrans --> Embeddings["384-Dimensional Vectors\n(BAAI/bge-small-en-v1.5)"]
    Embeddings --> PGVectorStore[("PostgreSQL + pgvector\n(Cosine Distance Index)")]
    
    Query["User Question / Issue Query"] --> QueryVec["Query Embedding"]
    QueryVec --> SimSearch{"pgvector Similarity Retrieval"}
    PGVectorStore --> SimSearch
    
    SimSearch -->|"Success (Cosine <= 0.8)"| RetrievedChunks["Ranked Code Chunks"]
    SimSearch -->|"Fallback if unindexed"| KeywordFallback["Exact & Subword Keyword Matcher\n(Path & Filename Boosting)"]
    KeywordFallback --> RetrievedChunks
    
    RetrievedChunks --> ContextAssembly["Bounded Context Assembly\n(Demarcated Prompt Injection Shield)"]
    ContextAssembly --> OllamaInference["Local Ollama Inference\n(llama3.2:3b)"]
    OllamaInference --> CitationGuard["Citation Verification Filter\n(Discard Hallucinated Citations)"]
    CitationGuard --> GroundedAnswer["Verified Grounded Answer"]
```

> **Fallback Guardrail**: If a repository has not yet been indexed into pgvector or the database is starting up, the retriever seamlessly and automatically falls back to an exact and subword keyword retrieval engine with path and filename boosting.

---

## 8. Technology Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS
- **Theme**: `next-themes` (Dark and Light modes)
- **Icons**: Lucide React
- **UI Components**: Modular component primitives (inspired by shadcn/ui)

### Backend
- **Framework**: Python 3.10+ FastAPI
- **Data Validation & Serialization**: Pydantic v2
- **ORM & Database Toolkit**: SQLAlchemy 2.0
- **Database Driver**: `asyncpg` (Asynchronous PostgreSQL client) & `psycopg2-binary`
- **Settings Management**: `pydantic-settings` & `python-dotenv`
- **Server**: Uvicorn

### Local AI & Vector Database
- **Vector Database**: PostgreSQL 16 with `pgvector` extension
- **Embedding Provider**: Sentence Transformers (`BAAI/bge-small-en-v1.5`, 384 dimensions, CPU execution)
- **Local LLM Engine**: Ollama
- **Local Model**: `llama3.2:3b`

### Infrastructure & Tooling
- **External API**: GitHub REST API (v3) via asynchronous `httpx`
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest & Pytest-Asyncio (329 tests)
- **CI/CD**: GitHub Actions

---

## 9. Project Structure

```
opensource-copilot/
├── frontend/                     # Next.js 14 Web Application
│   ├── app/                      # App router (layout, login, register, page)
│   ├── components/               # Modular UI, analyzer, chat, issues, profile
│   ├── context/                  # AuthContext and state providers
│   ├── lib/                      # API client and utility helpers
│   ├── types/                    # Domain TypeScript type definitions
│   └── package.json
│
├── backend/                      # FastAPI Python Application
│   ├── app/
│   │   ├── api/v1/               # API endpoints (health, auth, repos, profile)
│   │   ├── auth/                 # JWT authentication, security, bcrypt hashing
│   │   ├── chat/                 # RAG repository chat orchestration
│   │   ├── contribution/         # Step-by-step contribution guide generator
│   │   ├── core/                 # Settings configuration, database connection
│   │   ├── embeddings/           # Sentence Transformers local embedding engine
│   │   ├── models/               # SQLAlchemy declarative database entities
│   │   ├── prompts/              # Grounded LLM system prompts (injection defended)
│   │   ├── rag/                  # Semantic chunker, retriever, pgvector indexer
│   │   ├── repositories/         # Database access repository layer
│   │   ├── schemas/              # Pydantic schemas and serialization models
│   │   ├── services/             # Business logic (GitHub, issues, skills, LLM)
│   │   └── main.py               # FastAPI application entrypoint
│   ├── tests/                    # 329 comprehensive automated tests
│   └── requirements.txt          # Python dependencies
│
├── docs/                         # Technical architecture & deployment guides
│   ├── architecture.md
│   └── deployment.md
├── docker-compose.yml            # Multi-service local Docker orchestration
├── .gitignore                    # Git ignore definitions
├── .env.example                  # Environment configuration template
└── README.md                     # Project documentation
```

---

## 10. Local Setup

Follow these step-by-step Windows PowerShell instructions to run OpenSource Copilot locally.

### Prerequisites
- [Git](https://git-scm.com/)
- [Node.js 18+](https://nodejs.org/) and npm
- [Python 3.10+](https://www.python.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/)

---

### Step 1: Clone Repository
```powershell
git clone https://github.com/your-org/opencopilot.git
cd opencopilot
```

---

### Step 2: Start PostgreSQL with pgvector via Docker
Start the database service in the background:
```powershell
# Copy root environment template
Copy-Item .env.example .env

# Start PostgreSQL + pgvector
docker compose up -d postgres
```

> **Windows Port Note**: If native Windows PostgreSQL is already using port `5432`, set `POSTGRES_PORT=5433` in your root `.env`. Docker will bind to host port `5433` without port conflicts.

---

### Step 3: Start Ollama and Pull the Local Model
1. Open a new terminal and start the Ollama service:
   ```powershell
   ollama serve
   ```
2. Pull the default 3B parameter model (one-time download):
   ```powershell
   ollama pull llama3.2:3b
   ```
3. Verify the model is available:
   ```powershell
   ollama list
   ```

---

### Step 4: Configure and Start the Backend (FastAPI)
1. Open a terminal and navigate to `backend/`:
   ```powershell
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install backend dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Create your local environment file:
   ```powershell
   Copy-Item .env.example .env
   ```
   *(Ensure `DATABASE_URL` in `backend/.env` points to port `5433` if you configured port 5433 in Step 2: `postgresql+asyncpg://postgres:postgres@localhost:5433/opencopilot`)*.
5. Launch the FastAPI server:
   ```powershell
   python -m uvicorn app.main:app --reload --port 8000
   ```
6. Verify backend health in your browser or terminal:
   ```powershell
   curl http://localhost:8000/api/health
   # Returns: {"status":"ok","service":"OpenSource Copilot API"}
   ```
   Interactive Swagger documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 5: Configure and Start the Frontend (Next.js)
1. Open a new terminal and navigate to `frontend/`:
   ```powershell
   cd frontend
   ```
2. Install npm dependencies:
   ```powershell
   npm install
   ```
3. Create your local environment file:
   ```powershell
   Copy-Item .env.example .env.local
   ```
4. Start the Next.js development server:
   ```powershell
   npm run dev
   ```

---

### Step 6: Open the Application
Open your browser at:
```
http://localhost:3000
```
Enter any public GitHub repository (e.g., `pallets/flask` or `tiangolo/fastapi`) and start analyzing!

---

## 11. Environment Variables

The table below documents all environment variables used in local development. Never commit real credentials, passwords, or personal access tokens to version control.

| Variable | Description | Default / Example Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URI (`asyncpg` driver) | `postgresql+asyncpg://postgres:postgres@localhost:5433/opencopilot` |
| `POSTGRES_PORT` | Host port mapped to PostgreSQL container | `5433` (or `5432`) |
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `postgres` |
| `POSTGRES_DB` | PostgreSQL database name | `opencopilot` |
| `GITHUB_TOKEN` | Optional GitHub Personal Access Token (PAT) to increase rate limit (60 -> 5,000 req/hr) | `""` or `ghp_...` |
| `GITHUB_API_BASE_URL` | GitHub REST API endpoint | `https://api.github.com` |
| `GITHUB_REQUEST_TIMEOUT` | Timeout in seconds for GitHub requests | `15` |
| `LLM_PROVIDER` | Local AI engine | `ollama` |
| `LLM_MODEL` | Ollama model identifier | `llama3.2:3b` |
| `OLLAMA_BASE_URL` | Ollama HTTP API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name identifier | `llama3.2:3b` |
| `LLM_TEMPERATURE` | Sampling temperature for AI generation | `0.2` |
| `LLM_MAX_OUTPUT_TOKENS` | Maximum output tokens generated | `4096` |
| `LLM_REQUEST_TIMEOUT` | Generation timeout in seconds | `120.0` |
| `EMBEDDING_PROVIDER` | Local embeddings engine | `sentence_transformers` |
| `EMBEDDING_MODEL` | Sentence Transformers model name | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_DIMENSION` | Vector dimensions (must match DB schema) | `384` |
| `EMBEDDING_DEVICE` | Execution device for embeddings | `cpu` |
| `AUTH_SECRET_KEY` | Secret key for signing JWT tokens | `dev-insecure-secret-key-change-in-production-min-32-chars-long` |
| `AUTH_ALGORITHM` | Algorithm used for JWT signing | `HS256` |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | Token session validity in minutes | `10080` (7 days) |
| `CORS_ORIGINS` | Allowed origins for CORS | `["http://localhost:3000","http://127.0.0.1:3000"]` |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend client backend endpoint | `http://localhost:8000/api` |

---

## 12. API Overview

The backend exposes structured REST endpoints under the `/api` prefix:

| Group | Method & Path | Description |
| :--- | :--- | :--- |
| **Health** | `GET /api/health` | Service status check and version confirmation |
| **Auth** | `POST /api/v1/auth/register` | Register a new user account (201 Created) |
| | `POST /api/v1/auth/login` | Authenticate user and issue JWT bearer token |
| | `GET /api/v1/auth/me` | Retrieve profile of currently authenticated user |
| | `POST /api/v1/auth/logout` | Revoke user session |
| **Repositories** | `POST /api/v1/repositories/analyze` | Fetch repository metadata, stats, languages, and README |
| | `POST /api/v1/repositories/tree` | Retrieve recursive Git tree and file classification |
| | `POST /api/v1/repositories/file` | Retrieve raw or decoded content of a specific file |
| | `POST /api/v1/repositories/ingest` | Ingest repository code documents into local database |
| | `POST /api/v1/repositories/ai-analysis` | Generate grounded architectural analysis via Ollama |
| **Profile** | `GET /api/v1/profile/skills` | Retrieve developer skill profile |
| | `PUT /api/v1/profile/skills` | Update developer skill profile (stored in PostgreSQL) |
| **RAG** | `POST /api/v1/rag/index` | Chunk and embed repository documents into pgvector |
| | `POST /api/v1/rag/retrieve` | Retrieve top-k chunks matching a query |
| | `POST /api/v1/rag/context` | Build bounded character-budget context window |
| | `POST /api/v1/rag/vector-search` | Query 384-dimensional cosine similarity index |
| **Chat** | `POST /api/v1/chat` | Grounded conversational Q&A with verified file citations |
| **Issues** | `POST /api/v1/repositories/issues/analyze` | Inspect issue body, candidate files, and difficulty |
| | `POST /api/v1/repositories/issues/recommend` | Score and rank issues matching developer skill profile |
| **Guide** | `POST /api/v1/repositories/issues/contribution-guide` | Synthesize step-by-step contribution blueprint |

---

## 13. Security

OpenSource Copilot is designed with layered defense-in-depth principles:

- **Path Traversal Protection**: The `validate_repository_path()` utility blocks null bytes (`\x00`), path traversal sequences (`../`, `..\`, `..%2f`, double-encoded `%252f`), absolute filesystem paths (`/etc/passwd`, `C:\Windows`), and paths exceeding 500 characters.
- **GitHub URL Validation**: Strict URL parsers validate domains and repository path patterns (`owner/repo`), rejecting invalid hostnames, IP addresses, and malicious query strings.
- **Prompt Injection Defense**: All system prompts contain strict isolation rules. Untrusted repository files and issue bodies are demarcated inside `=== UNTRUSTED REPOSITORY CONTEXT ===` tags, directing the LLM to treat them strictly as data, never instructions.
- **Bounded Inputs & Rate Ceilings**: Input schemas enforce character limits (questions: max 2,000 chars; search queries: max 1,000 chars; repo URLs: max 500 chars). Retrieval bounds (`1 <= top_k <= 20`) prevent memory exhaustion.
- **Source Verification Guardrail**: LLM responses are checked against actually retrieved chunks. Hallucinated file citations or non-retrieved line ranges are stripped before responses reach the user.
- **Sanitized Server Errors**: Uncaught exceptions are intercepted by a global exception handler. Full diagnostic traces are logged internally, while clients receive sanitized HTTP 500 error envelopes that never expose internal paths, passwords, or database schemas.

---

## 14. Testing & Verification

The project is backed by comprehensive automated test suites across both backend and frontend.

### Verified Test Results

```bash
# Backend Pytest Suite
python -m pytest -q
# Result: 329 passed, 4 warnings in 5.65s (0 failures)
```

```bash
# Frontend Static Analysis & Type Checking
npm run typecheck
# Result: tsc --noEmit -> Exit code 0 (0 type errors)

# Frontend ESLint
npm run lint
# Result: ✔ No ESLint warnings or errors (Exit code 0)

# Frontend Production Build
npm run build
# Result: Compiled successfully, all 6 static routes generated (Exit code 0)
```

- **Backend Test Coverage**: 329 tests covering authentication, RAG chunking, pgvector retrieval, keyword fallback, GitHub API parsing, security hardening (26 attack vectors), and skill matching.
- **Frontend Verification**: TypeScript in strict mode with zero type errors, clean ESLint validation, and successful Next.js production compilation.

---

## 15. Limitations

To maintain realistic expectations, the following limitations currently apply:

- **Local Ollama Dependency**: AI analysis, chat, and contribution guide generation require Ollama running locally with the `llama3.2:3b` model downloaded. If Ollama is offline, the application gracefully degrades to deterministic analysis mode and keyword search.
- **GitHub API Rate Limits**: Unauthenticated requests to GitHub are capped at 60 requests per hour per IP. Adding a `GITHUB_TOKEN` in `.env` increases this threshold to 5,000 requests per hour.
- **Local Infrastructure Requirements**: Requires Docker to run PostgreSQL with the `pgvector` extension and sufficient system RAM (8 GB recommended) for running local LLM inference.
- **Read-Only Operation**: OpenSource Copilot strictly analyzes code and recommends solutions. It **does not** create pull requests, commit code to remote repositories, or execute untrusted code locally.

---

## 16. Future Enhancements

Planned future improvements include:
- **Cloud Deployment Profiles**: Optional cloud infrastructure templates for teams desiring hosted deployments.
- **Multi-Language AST Chunking**: Deep AST chunkers for Go, Rust, and TypeScript in addition to Python, Markdown, and YAML.
- **Enhanced Issue Ranking**: Semantic vector search directly over issue descriptions for nuanced topic-based discovery.
- **GitHub PR Workflow Integration**: Optional capability to draft pull request descriptions and export contribution checklists directly to GitHub.
- **Additional LLM Providers**: Expand the provider interface with configurable hosted providers while retaining Ollama as the local default.

---

## 17. License

OpenSource Copilot is open-source software licensed under the [MIT License](LICENSE).

---

## 18. Complete System Flow

The diagram below provides a complete, high-level view of the end-to-end data flow through all layers of OpenSource Copilot:

```mermaid
flowchart TD
    subgraph UserInteraction["User Interaction"]
        Dev["Developer"]
    end

    subgraph ClientLayer["Frontend Client (Port 3000)"]
        UI["Next.js 14 Web Interface"]
    end

    subgraph APILayer["FastAPI Gateway (Port 8000)"]
        API["FastAPI Application"]
    end

    subgraph ExternalServices["External APIs"]
        GitHub["GitHub REST API"]
    end

    subgraph IngestionPipeline["Code Ingestion & Indexing"]
        Ingestion["Source Ingestion Service"]
        Chunker["AST Semantic Chunker"]
        Embedder["Sentence Transformers\n(384-dim CPU)"]
    end

    subgraph Storage["Persistence Layer"]
        DB[("PostgreSQL 16 + pgvector\n(Port 5433)")]
    end

    subgraph LocalInference["Local AI Inference"]
        Ollama["Local Ollama Engine\n(llama3.2:3b)"]
    end

    subgraph AIFeatures["Output & Reasoning Engine"]
        ArchOut["Architecture Breakdown"]
        ChatOut["RAG Grounded Chat"]
        IssueOut["Skill-Matched Issues"]
        GuideOut["Contribution Guide"]
    end

    Dev -->|"Enters Repo URL / Query"| UI
    UI -->|"HTTP Request"| API
    
    API -->|"Fetch Tree, Files, Issues"| GitHub
    GitHub -->|"Raw Repo Data"| API
    
    API -->|"Process Code"| Ingestion
    Ingestion --> Chunker
    Chunker --> Embedder
    Embedder -->|"Store Vectors"| DB
    
    API -->|"Retrieve Context"| DB
    DB -->|"Top-k Chunks"| API
    
    API -->|"Bounded Prompt"| Ollama
    Ollama -->|"Inference Result"| API
    
    API --> ArchOut
    API --> ChatOut
    API --> IssueOut
    API --> GuideOut
    
    ArchOut --> UI
    ChatOut --> UI
    IssueOut --> UI
    GuideOut --> UI
    UI -->|"Displays Insights & Guides"| Dev
```
