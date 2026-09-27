# OpenSource Copilot Architecture

## Overview
OpenSource Copilot is architected as a modular monorepo cleanly separating the client-side presentation layer (Next.js App Router) from the server-side business logic and data processing layer (FastAPI + PostgreSQL).

```
┌────────────────────────────────────────────────────────┐
│               Frontend (Next.js + Tailwind)            │
│  - App Router Shell                                    │
│  - Modular UI Sections (Hero, Analyzer, Issues, Chat)  │
│  - Strongly-typed Domain Contracts                     │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (CORS Enabled)
                            ▼
┌────────────────────────────────────────────────────────┐
│               Backend (Python FastAPI)                 │
│  - app/main.py (Application Lifecycle & CORS)          │
│  - app/api/v1/ (Route Controllers)                     │
│  - app/services/ (Service Layer & Replaceable LLMs)    │
│  - app/repositories/ (Database Operations)             │
│  - app/models/ (SQLAlchemy Declarative Entities)       │
│  - app/schemas/ (Pydantic Request/Response Models)     │
│  - app/core/ (Config & Database Sessions)              │
└───────────────────────────┬────────────────────────────┘
                            │ SQLAlchemy (PostgreSQL / pgvector)
                            ▼
┌────────────────────────────────────────────────────────┐
│                     PostgreSQL                         │
│  - Users, Skills, Repositories, Issues, Guides, Chat   │
│  - Vector Embeddings (Planned via pgvector)            │
└────────────────────────────────────────────────────────┘
```

## Replaceable AI Provider Design
To prevent vendor lock-in and enable zero-cost local development, the AI subsystem is decoupled behind an abstract base class `LLMProvider`:

- **Contract**: Defines uniform asynchronous methods `generate_text`, `chat_stream`, and `create_embeddings`.
- **Implementations**:
  - `OllamaProvider`: Connects to a local open-source Ollama instance (default for open-source development).
  - `OpenAICompatibleProvider`: Connects to any standard API-based provider (OpenAI, Groq, Mistral, Anthropic adapter).
- **Configuration**: Chosen dynamically via `LLM_PROVIDER` environment variable without changing downstream application code.

## Data Layer Planning
The database schema is planned around key domain entities:
1. **User & UserSkill**: Developer profiles and tagged technical proficiencies (languages, frameworks, experience level).
2. **Repository & RepositoryFile**: Cloned or indexed repository metadata, structure, dependencies, and READMEs.
3. **Issue & IssueAnalysis**: Open issues fetched from GitHub, classified by difficulty, domain, and prerequisites.
4. **ContributionGuide**: Generated step-by-step guidance tailored for a specific issue and repo.
5. **ChatSession, ChatMessage & Embedding**: Multi-turn repository-specific conversations and vector embeddings for semantic document search.

## API Route Design
- `/api/health`: Service health check (implemented in Foundation).
- `/api/v1/repositories/analyze` (also available as `/api/repositories/analyze`): Real GitHub repository analysis (Implemented in Phase 3).
- `/api/repositories`: Repository ingestion and listing.
- `/api/repositories/{id}`: Detailed repository overview and structure.
- `/api/repositories/{id}/issues`: Issue discovery and skill-based matching.
- `/api/repositories/{id}/analysis`: Deep architecture analysis and summary.
- `/api/repositories/{id}/chat`: RAG-powered repository Q&A chat.
- `/api/issues/{id}`: Individual issue details and contribution guide.
- `/api/users`: User management.
- `/api/users/{id}/skills`: Developer skills profiling for issue recommendations.

## GitHub Integration Architecture (Phase 3)

The GitHub integration subsystem provides direct, real-time ingestion of public GitHub repository data through FastAPI and httpx, feeding normalized domain models to the frontend.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│  - lib/api.ts (Typed API Client & Error Mapping)       │
│  - Repository Input & Analysis Orchestrator            │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/repositories/analyze
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Repositories Router              │
│  - app/api/v1/endpoints/repositories.py                │
│  - URL validation via parse_github_url                 │
│  - HTTP Exception mapping (400, 404, 403, 503)         │
└───────────────────────────┬────────────────────────────┘
                            │ Async Service Calls
                            ▼
┌────────────────────────────────────────────────────────┐
│                   GitHubService                        │
│  - app/services/github_service.py                      │
│  - fetch_repository (metadata, stars, forks, license)  │
│  - fetch_languages (byte counts per language)          │
│  - fetch_readme (base64 decoded content & summary)     │
│  - fetch_issues (filters out pull requests)            │
└───────────────────────────┬────────────────────────────┘
                            │ Async HTTPS (httpx with optional GITHUB_TOKEN)
                            ▼
┌────────────────────────────────────────────────────────┐
│                  GitHub REST API v3                    │
│  - api.github.com/repos/{owner}/{repo}                 │
│  - api.github.com/repos/{owner}/{repo}/languages       │
│  - api.github.com/repos/{owner}/{repo}/readme          │
│  - api.github.com/repos/{owner}/{repo}/issues          │
└────────────────────────────────────────────────────────┘
```

### Components
1. **GitHub URL Parser** (`parse_github_url`):
   - Validates HTTPS, HTTP, and shorthand (`owner/repo`) repository strings.
   - Rejects non-GitHub hosts (e.g. `gitlab.com`, `bitbucket.org`).
   - Normalizes owner and repository names, stripping trailing slashes and `.git`.

2. **Async GitHub Service** (`GitHubService`):
   - Built on `httpx.AsyncClient` with configurable timeout (`GITHUB_REQUEST_TIMEOUT`).
   - Optional GitHub Personal Access Token authentication via `GITHUB_TOKEN` setting for higher rate limits (5,000 req/hr vs 60 req/hr unauthenticated).
   - Base64 README decoding with automatic fallback if README is missing.
   - Issues query filters out pull requests (which GitHub's issue endpoint includes by default via `pull_request` key).

3. **Exception Hierarchy**:
   - `InvalidGitHubURLError` -> HTTP 400 Bad Request
   - `GitHubNotFoundError` -> HTTP 404 Not Found
   - `GitHubRateLimitError` -> HTTP 403 Forbidden
   - `GitHubServiceError` -> HTTP 503 Service Unavailable

4. **Pydantic Schemas** (`app/schemas/repository.py`):
   - `RepositoryAnalyzeRequest`: Validated payload containing repository URL.
   - `RepositoryInfo`: Normalized repository metadata, license, open issue count, default branch.
   - `ReadmeInfo`: Presence flag, filename, size, and decoded content preview.
   - `IssueItem`: Real issues with number, title, author, labels, comments, and direct GitHub HTML URL.
   - `RepositoryAnalysisResponse`: Unified payload with metadata, languages, README, issues, and `source: "github"`.

## Repository Tree and Code Ingestion Architecture (Phase 4)

Phase 4 enables OpenSource Copilot to retrieve real repository file hierarchies and source code content from GitHub without cloning git repositories locally, with strict safety limits and automated file classification.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│  - RepositoryTree component (Hierarchical tree & viewer)│
│  - lib/api.ts (getRepositoryTree, getRepositoryFile)   │
└───────────────────────────┬────────────────────────────┘
                            │ GET /api/v1/repositories/{owner}/{repo}/tree
                            │ GET /api/v1/repositories/{owner}/{repo}/files/{path}
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Repositories Router              │
│  - app/api/v1/endpoints/repositories.py                │
└───────────────────────────┬────────────────────────────┘
                            │ Service Calls
                            ▼
┌────────────────────────────────────────────────────────┐
│             RepositoryIngestionService                 │
│  - app/services/repository_ingestion_service.py        │
│  - Enforces safety limits (file counts, byte limits)   │
│  - get_repository_tree() & get_file_content()          │
│  - ingest_repository() batch ingestion                │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│    RepositoryFileFilter      │ │        GitHubService         │
│ - app/services/              │ │ - app/services/              │
│   repository_file_filter.py  │ │   github_service.py          │
│ - File category tagging      │ │ - fetch_tree (Git Trees API) │
│ - Language detection         │ │ - fetch_file_content (Base64)│
│ - Ignored dir / binary filter│ └──────────────────────────────┘
└──────────────────────────────┘
```

### 1. Git Trees Integration (`GitHubService.fetch_tree`)
- Utilizes the GitHub Git Trees API (`GET /repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1`) to retrieve the complete repository file tree in a single lightweight HTTP request.
- Normalizes GitHub tree types: `blob` → `file`, `tree` → `directory`.
- Handles truncated trees gracefully with `truncated` flag propagation.

### 2. File Classification & Language Detection (`RepositoryFileFilter`)
- Classifies each tree item into one of six categories:
  - `source`: Active application source files (`.py`, `.ts`, `.js`, `.go`, `.rs`, etc.).
  - `test`: Test suites, test runners, and spec files (`test_*.py`, `*.spec.ts`, `tests/`, etc.).
  - `documentation`: Guides, markdown docs, and licenses (`.md`, `.rst`, `docs/`, `LICENSE`).
  - `configuration`: Build and project configurations (`package.json`, `pyproject.toml`, `Makefile`, etc.).
  - `generated_or_ignored`: Artifact directories (`node_modules/`, `dist/`, `build/`, `__pycache__/`, `.venv/`).
  - `binary_or_unsupported`: Compiled binaries, minified bundles, images, archives, lock files.
- Identifies programming languages across 25+ language extensions and special filenames.

### 3. Safety Guardrails & Resource Limits
- Configurable environment thresholds in `app/core/config.py`:
  - `MAX_TREE_ITEMS` (default: 10,000): Maximum tree nodes parsed.
  - `MAX_SOURCE_FILES` (default: 100): Maximum source files ingested in batch runs.
  - `MAX_FILE_SIZE_BYTES` (default: 100 KB): Maximum size for individual text files fetched.
  - `MAX_TOTAL_CODE_BYTES` (default: 2 MB): Maximum total code payload ingested.
- Binary detection via null-byte inspection (`b"\x00"` in initial bytes) and UTF-8 validation prevents binary corruption or memory spikes.

### 4. Endpoints & Frontend UI
- `GET /api/v1/repositories/{owner}/{repo}/tree?branch={branch}`: Returns enriched tree with file categories and detected languages.
- `GET /api/v1/repositories/{owner}/{repo}/files/{path:path}?ref={ref}`: Returns on-demand decoded source code with syntax language and line count.
- `POST /api/v1/repositories/ingest`: Batch analysis and metadata ingestion with summary statistics.
- Interactive file explorer in `frontend/components/repository/repository-tree.tsx` featuring expandable directories, category badge filtering, file search, and an integrated code viewer with line numbering and clipboard copy.

## AI Repository Analysis Architecture (Phase 5)

Phase 5 introduces the first real AI capability to OpenSource Copilot: given structured data retrieved from GitHub in Phases 3 and 4, the application synthesizes a grounded architectural breakdown, technology stack with evidence citations, and beginner onboarding guide using a replaceable LLM provider interface (defaulting to local Ollama).

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│  - AIAnalysisSection component (Tabs & Evidence Cards) │
│  - lib/api.ts (analyzeRepositoryAI)                    │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/repositories/analyze-ai
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Repositories Router              │
│  - app/api/v1/endpoints/repositories.py                │
└───────────────────────────┬────────────────────────────┘
                            │ Coordinates Data
                            ▼
┌────────────────────────────────────────────────────────┐
│             RepositoryAnalysisService                  │
│  - app/services/repository_analysis_service.py         │
│  - Validates URL & fetches metadata, tree, source files│
│  - Prompts LLM & sanitizes/validates Pydantic output   │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│   RepositoryContextBuilder   │ │      LLMProviderFactory      │
│ - app/services/              │ │ - app/services/              │
│   repository_context_builder │ │   llm_factory.py             │
│ - Priority sorting (README > │ │ - Resolves configured        │
│   configs > entry points >   │ │   provider (OllamaProvider)  │
│   source > tests)            │ └──────────────┬───────────────┘
│ - Capping chars & file counts│                │
└──────────────────────────────┘                ▼
                                 ┌──────────────────────────────┐
                                 │        OllamaProvider        │
                                 │ - app/services/              │
                                 │   llm_provider.py            │
                                 │ - POST /api/generate         │
                                 │ - format: "json"             │
                                 │ - Optional at startup        │
                                 └──────────────┬───────────────┘
                                                │ Local HTTP
                                                ▼
                                 ┌──────────────────────────────┐
                                 │     Local Ollama Daemon      │
                                 │ - http://localhost:11434     │
                                 │ - Default model: llama3      │
                                 └──────────────────────────────┘
```

### 1. Replaceable LLM Provider Abstraction
- Abstract interface `LLMProvider` in `app/services/llm_provider.py` defines `generate(prompt, system_prompt, temperature, max_tokens, json_mode)`.
- `OllamaProvider` connects over HTTP to the local Ollama daemon without requiring paid commercial APIs.
- Provider resolution via `llm_factory.get_llm_provider()` allows future providers (`OpenAIProvider`, `GeminiProvider`, `AnthropicProvider`) to be added without modifying the analysis orchestration service.
- **Startup Isolation**: The application starts immediately without checking Ollama. When an AI request is made, network failures cleanly map to HTTP 503 (`LLMProviderUnavailableError`) with setup guidance (`ollama run llama3`).

### 2. Deterministic Context Builder & Guardrails
- `RepositoryContextBuilder` transforms raw repository data into an optimized, character-bounded context prompt:
  - **Tier 1**: README (`README.md`, `README.rst`)
  - **Tier 2**: Manifests & configuration files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`, `Dockerfile`)
  - **Tier 3**: Entry points (`main.py`, `app.py`, `index.ts`, `main.go`, `server.ts`)
  - **Tier 4**: Primary source code (`src/`, `app/`, `lib/`)
  - **Tier 5**: Test suites and fixtures
- **Size Budgeting**: Enforces `AI_MAX_CONTEXT_CHARS` (default: 60,000), `AI_MAX_FILES_IN_CONTEXT` (default: 15 files), and `AI_MAX_FILE_CHARS` (default: 6,000 chars per file with truncation notices).

### 3. Grounding & Anti-Hallucination Rules
- Strict system prompt in `app/prompts/repository_analysis.py` mandates evidence-based findings.
- Every detected technology must reference evidence from configuration or observed code.
- Entry points must indicate confidence level (`high`, `medium`, `low`, `unknown`).

### 4. Reliable Structured Pydantic Output
- `RepositoryAIAnalysis` validates fields: `summary`, `purpose`, `architecture`, `technology_stack`, `important_directories`, `important_files`, `entry_points`, `testing`, `beginner_explanation`, and `confidence_assessment`.
- `sanitize_json_response` strips Markdown fences and extraneous tokens before JSON parsing.

> [!NOTE]
> **Scope Confirmation**: Phase 5 does **not** implement RAG, vector embeddings, semantic search, or remote code execution.

---

## Phase 6: AI Issue Analysis & Intelligent Issue Recommendations

Phase 6 introduces grounded, issue-level AI understanding and recommendations, allowing contributors to click on any real GitHub issue and obtain an actionable, evidence-based investigation plan.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│  - IssueCard (Analyze with AI button + GitHub link)    │
│  - LiveIssueAIModal (AI estimates, candidate files,   │
│    investigation steps, evidence breakdown)            │
│  - lib/api.ts (analyzeIssueAI)                         │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/repositories/issues/analyze
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Repositories Router              │
│  - app/api/v1/endpoints/repositories.py                │
└───────────────────────────┬────────────────────────────┘
                            │ Coordinates Issue & Repo Data
                            ▼
┌────────────────────────────────────────────────────────┐
│                IssueAnalysisService                    │
│  - app/services/issue_analysis_service.py              │
│  - Fetches single issue via github_service             │
│  - Fetches repo tree & candidate file excerpts         │
│  - Prompts LLM & validates IssueAIAnalysis schema      │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│     IssueContextBuilder      │ │      LLMProviderFactory      │
│ - app/services/              │ │ - Reuses get_llm_provider()  │
│   issue_context_builder.py   │ │   from llm_factory.py        │
│ - Keyword extraction from    │ │ - OllamaProvider (default)   │
│   issue title, body, labels  │ └──────────────┬───────────────┘
│ - Ranks candidate files      │                │
│ - Injects tree & excerpts    │                ▼
│ - Capping chars budget       │ ┌──────────────────────────────┐
└──────────────────────────────┘ │     Local Ollama Daemon      │
                                 │ - Default model: llama3      │
                                 └──────────────────────────────┘
```

### 1. Grounding & Anti-Hallucination Guardrails
- **AI Estimates**: All assigned difficulty levels and required skills are explicitly tagged as `"AI Estimate"` with supporting rationales.
- **Candidate Files**: All candidate files are framed with strict caveats: `"Candidate files requiring verification — keyword match, not proof"`. Files are selected from actual paths in the repository tree.
- **Evidence Separation**: Output is divided into three distinct categories:
  - `observed_evidence`: Direct facts quoted from issue title, body, labels, or verified repository files.
  - `inferences`: Reasonable technical deductions made by the AI based on facts.
  - `unknowns`: Unresolved ambiguities or missing reproduction steps requiring contributor clarification.

### 2. Issue Context Builder
- `IssueContextBuilder` deterministically parses issue content and matches keywords (backticks, filenames, function names, path segments) against the repository tree.
- Ranks candidate files by relevance and samples the top candidate files within character budgets (`AI_MAX_CONTEXT_CHARS`).
- Injects a compact list of all valid tree paths into the prompt, preventing LLM path hallucination.

### 3. Structured Pydantic Output
- `IssueAIAnalysis` validates fields: `issue_type`, `difficulty`, `difficulty_rationale`, `required_skills`, `skills_rationale`, `candidate_files`, `affected_areas`, `investigation_steps`, `prerequisites`, `ai_explanation`, `observed_evidence`, `inferences`, `unknowns`, and `confidence`.

---

## Phase 7: Repository RAG Pipeline Foundation

Phase 7 introduces the retrieval-augmented generation (RAG) data pipeline foundation for OpenSource Copilot. It establishes deterministic, structured ingestion, chunking, keyword-based scoring/retrieval, and bounded context generation over real GitHub repositories without relying on external vector databases.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│  - lib/api.ts (ragRetrieve, ragContext)                │
│  - types/index.ts (RAGRetrievalResponse, etc.)         │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/repositories/rag/retrieve
                            │ POST /api/v1/repositories/rag/context
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Repositories Router              │
│  - app/api/v1/endpoints/repositories.py                │
└───────────────────────────┬────────────────────────────┘
                            │ Service Layer
                            ▼
┌────────────────────────────────────────────────────────┐
│                      RAGService                        │
│  - app/rag/service.py                                  │
│  - Orchestrates document loading, chunking, retrieval  │
│  - Builds grounded context prompts                     │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│        DocumentLoader        │ │      RepositoryChunker       │
│ - app/rag/document_loader.py │ │ - app/rag/chunker.py         │
│ - Filters non-text & binary  │ │ - Language-aware chunking    │
│ - Category filtering         │ │ - Python, Markdown, YAML     │
│ - Preserves file metadata    │ │ - Line-number preservation   │
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│       KeywordRetriever       │ │      RAGContextBuilder       │
│ - app/rag/retriever.py       │ │ - app/rag/context.py         │
│ - BM25-inspired term scoring │ │ - Formatted file headers     │
│ - Subword & path boosts      │ │ - Strict char/token budget   │
│ - Exact-identifier weighting │ │ - Truncation notices         │
└──────────────────────────────┘ └──────────────────────────────┘
```

### 1. Domain Models (`app/rag/models.py`)
- `RepositoryDocument`: Normalized document representation with path, content, category, language, size, and line count.
- `RepositoryChunk`: Chunk unit containing deterministic `chunk_id` (`{file_path}#L{start}-L{end}`), source path, line range, content, token estimate, language, and category.
- `RetrievedChunk`: Chunk enriched with relevance score, matched query terms, and human-readable retrieval explanation.
- `RAGContext`: Assembled prompt context string accompanied by included chunks, file paths, total character count, and truncation indicators.

### 2. Document Loader (`app/rag/document_loader.py`)
- Ingests repository files and selectively filters out binary, generated, and ignored files.
- Restricts document collection to supported categories: `source`, `documentation`, `configuration`, and `test`.
- Enforces strict safety limits on file count and total code bytes to prevent memory spikes.

### 3. Language-Aware Repository Chunker (`app/rag/chunker.py`)
- Breaks code and documents into discrete semantic blocks rather than arbitrary character slices:
  - **Python**: Splits along top-level function (`def `) and class (`class `) definitions.
  - **Markdown**: Splits along markdown headers (`# `, `## `, `### `).
  - **YAML/Config**: Splits along top-level keys or blank lines.
  - **Fallback**: Sliding line-window chunking with configurable overlap.
- Sub-splits oversized blocks to respect `rag_chunk_size` (default: 1,500 chars).
- Preserves accurate 1-indexed start and end line numbers for precise code citation.

### 4. Deterministic Keyword Retriever (`app/rag/retriever.py`)
- Implements deterministic term frequency and position-based relevance scoring:
  - Exact identifier match boosting (quoted or programmatic terms).
  - Subword and case-splitting matches (camelCase and snake_case identifier breaking).
  - File path segment matches (e.g. matching queries against directory or file names).
  - Category relevance weight adjustments (applied only when term signals exist).
- Produces deterministic, sorted rankings with transparent `retrieval_reason` and `matched_terms`.

### 5. RAG Context Builder (`app/rag/context.py`)
- Formats retrieved chunks into markdown-fenced code blocks with file path headers and line number annotations.
- Enforces strict character budgets (`rag_max_context_chars`) and inserts informative truncation notices when budgets are exceeded.
- Produces clean, grounded context ready for downstream LLM generation or chat Q&A.

### 6. Verification & Endpoints
- `POST /api/v1/repositories/rag/retrieve`: Retrieves top-k ranked chunks for any natural language or code identifier query.
- `POST /api/v1/repositories/rag/context`: Generates a formatted context bundle suitable for LLM injection.
- Zero external vector database requirement, enabling fully local, deterministic execution.

---

## Phase 8: Local Embeddings + PostgreSQL pgvector Semantic Retrieval

Phase 8 elevates the keyword-based RAG pipeline into a full semantic similarity search engine using local sentence-transformers embeddings and PostgreSQL with the pgvector extension.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│  - lib/api.ts (indexRepositoryRAG, ragVectorSearch)    │
│  - types/index.ts (RAGIndexResponse, etc.)             │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/repositories/rag/index
                            │ POST /api/v1/repositories/rag/vector-search
                            │ POST /api/v1/repositories/rag/context
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Repositories Router              │
│  - app/api/v1/endpoints/repositories.py                │
└───────────────────────────┬────────────────────────────┘
                            │ Service Layer
                            ▼
┌────────────────────────────────────────────────────────┐
│                      RAGService                        │
│  - app/rag/service.py                                  │
│  - Routes queries to VectorRetriever or fallback       │
│  - Automatic KeywordRetriever fallback if DB offline   │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│      RepositoryIndexer       │ │       VectorRetriever        │
│ - app/rag/indexer.py         │ │ - app/rag/vector_retriever.py│
│ - SHA-256 content hashing    │ │ - Encodes query with prefix  │
│ - Chunk caching & reuse      │ │ - Cosine similarity: 1 - <=> │
│ - Batch embedding (size: 32) │ │ - Maps to RetrievedChunk     │
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│  SentenceTransformerProvider │ │     PostgreSQL + pgvector    │
│ - app/embeddings/            │ │ - repository_chunks table    │
│ - BAAI/bge-small-en-v1.5     │ │ - Vector(384) column         │
│ - 384 dimensions, CPU        │ │ - docker-compose.yml pg16    │
│ - Lazy load on 1st inference │ │ - Safe extension init        │
└──────────────────────────────┘ └──────────────────────────────┘
```

### 1. Embedding Provider Abstraction (`app/embeddings/`)
- `EmbeddingProvider`: Interface defining `embed_text(text, is_query)` and `embed_documents(texts)`.
- `SentenceTransformerEmbeddingProvider`:
  - Default model: `BAAI/bge-small-en-v1.5` producing 384-dimensional unit vectors.
  - Runs 100% locally on CPU without requiring GPU or external API keys.
  - Lazy loading: weights only download and load on the first vector embedding call, ensuring FastAPI starts instantaneously.
  - BGE Query Prefixing: Applies `"Represent this sentence for searching relevant passages: "` when `is_query=True`.
  - Normalized embeddings: Euclidean norm = 1.0, enabling exact cosine similarity via dot product.

### 2. Database Model & pgvector (`app/models/entities.py`)
- `RepositoryChunk` SQLAlchemy model:
  - `id`, `repository_id`, `repository_identifier` (`owner/repo`)
  - `file_path`, `language`, `category`, `chunk_index`, `start_line`, `end_line`, `content`
  - `content_hash`: SHA-256 hex digest of chunk text
  - `chunk_metadata`: JSON dictionary
  - `embedding`: `Vector(settings.EMBEDDING_DIMENSION)` (default: 384)
- `docker-compose.yml`: Local PostgreSQL container with pgvector (`pgvector/pgvector:pg16`), port 5432, and named volume `pgvector_data`.

### 3. Repository Indexer & Content Caching (`app/rag/indexer.py`)
- Incremental indexing workflow:
  1. Loads documents and chunks them using structure-aware chunker.
  2. Calculates deterministic SHA-256 hash for every chunk.
  3. Reuses existing vectors when `content_hash` matches existing DB records.
  4. Only batches and embeds new or modified chunks (`EMBEDDING_BATCH_SIZE=32`).
  5. Stores updated chunks and vectors in PostgreSQL.
  6. Deletes stale chunks when files are updated or removed.
  7. Returns detailed statistics: documents processed, chunks created/embedded/reused/updated.

### 4. Semantic Vector Retriever & Fallback (`app/rag/vector_retriever.py`, `app/rag/service.py`)
- `VectorRetriever`:
  - Encodes search query into normalized 384-dim vector.
  - Queries PostgreSQL pgvector using cosine distance (`<=>` operator).
  - Translates distance to cosine similarity: $\text{similarity} = 1.0 - \text{distance}$ (1.0 = identical match).
  - Returns `RetrievedChunk` models directly compatible with `RAGContextBuilder`.
- **Automatic Fallback Guardrail**:
  - If `RAG_RETRIEVAL_MODE=vector`, but PostgreSQL/pgvector is unreachable, the embedding model fails, or the repository has 0 indexed chunks:
  - Automatically and transparently falls back to `KeywordRetriever`.
  - Sets `retrieval_mode="keyword_fallback"` with explicit warning logs.

---

## Developer Skill Profile & Personalized Issue Recommendations (Phase 10)

Phase 10 introduces developer skill profiling and personalized issue recommendations, answering:
1. *"Which issues in this repository match my skills?"*
2. *"Why is this issue a good match for my current skills?"*

```text
┌────────────────────────────────────────────────────────┐
│             Developer Skill Profile                    │
│  - languages, frameworks, tools, domains, interests    │
│  - experience level: beginner | intermediate | advanced│
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Deterministic Normalizer                   │
│  - app/services/skill_normalizer.py                    │
│  - Canonical alias map ("js" -> "JavaScript")          │
│  - Preserves unknown skills without dropping           │
│  - Deduplicates case-insensitively                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Profile Service (In-Memory)                │
│  - GET /api/v1/profile/skills                          │
│  - POST /api/v1/profile/skills                         │
│  - No persistent accounts or auth required in Phase 10 │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           Skill Matching Service & Recommendations     │
│  - app/services/skill_matching_service.py              │
│  - Reuses cached IssueAIAnalysis (from Phase 6)        │
│  - Evaluates required skills, candidate files, stack   │
│  - Computes transparent Match Score (0.0 - 1.0)        │
│  - Generates explicit Match Reasons & Skill Gaps       │
│  - Identifies concrete Learning Opportunities          │
│  - Keeps AI Difficulty Estimate strictly separate      │
│  - Sorts deterministically by score desc, issue # asc  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            POST /api/v1/repositories/issues/recommend  │
│  - Evaluates repository open issues against profile    │
│  - Frontend RecommendedIssues & Profile UI components  │
└────────────────────────────────────────────────────────┘
```

### 1. Developer Skill Profile (`app/schemas/profile.py`)
- Fields:
  - `programming_languages`: List[str]
  - `frameworks`: List[str]
  - `tools`: List[str]
  - `domains`: List[str]
  - `experience_level`: "beginner" | "intermediate" | "advanced"
  - `interests`: List[str]

### 2. Conservative Skill Normalization (`app/services/skill_normalizer.py`)
- Direct canonical alias map for languages, frameworks, databases, and tools.
- Preserves casing and formatting for unknown skills.
- Deduplicates lists case-insensitively while preserving insertion order.

### 3. Transparent Skill Match vs. AI Difficulty Estimate
- **Skill Match Score**: Range 0.0 to 1.0 (0% to 100%). Represents the proportion of analyzed requirements that overlap with the developer profile. It is NOT an objective measure of developer capability.
- **AI Difficulty Estimate**: Intrinsic technical complexity estimated by AI (beginner, intermediate, advanced, unknown). Kept strictly separate from the skill match score. An issue may be "Advanced" while a senior engineer has a 100% skill match.
- **Match Reasons**: Transparent evidence-based explanations (e.g. required skill overlap, candidate file extensions matching programming languages, framework alignments).
- **Skill Gaps**: Required skills not present in the developer's profile.
- **Learning Opportunities**: Constructive guidance highlighting new skills or technologies that working on this issue offers an opportunity to learn.

### 4. Recommendation Ordering
- Recommendations are sorted by numeric Skill Match score descending.
- Ties are broken deterministically by issue number ascending.
- Strictly avoids subjective claims like "best", "winner", or "easiest".

---

## Grounded AI Contribution Guide (Phase 11)

Phase 11 provides maintainer-ready, verified contribution blueprints grounded in repository source code:

```text
┌────────────────────────────────────────────────────────┐
│             POST /issues/contribution-guide            │
│  - repo, issue, branch, developer profile context      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                Context Retrieval (RAG)                 │
│  - pgvector semantic search + keyword retriever        │
│  - Bounded retrieved chunks with SHA-256 chunk IDs     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               Grounded Prompt Synthesis                │
│  - UNTRUSTED REPOSITORY CONTEXT isolation tags         │
│  - Injection defense guidelines                        │
│  - Strict citation instruction (only cite valid paths) │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              Post-Generation Verification              │
│  - Verifies cited files exist in retrieved chunks      │
│  - Filters out unverified / hallucinated line ranges   │
│  - Enforces Pydantic structured output validation      │
└────────────────────────────────────────────────────────┘
```

---

## Authentication & User Accounts (Phase 12)

Phase 12 implements persistent user authentication and session management:

```text
┌────────────────────────────────────────────────────────┐
│                     Client App                         │
│  - AuthProvider (React Context & useAuth hook)         │
│  - JWT stored in localStorage / Authorization header   │
└───────────────────────────┬────────────────────────────┘
                            │ Bearer <JWT>
                            ▼
┌────────────────────────────────────────────────────────┐
│                 FastAPI Auth Middleware                │
│  - Depends(get_current_user_optional)                  │
│  - PyJWT verification (HS256)                          │
│  - bcrypt password hashing                             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             PostgreSQL Auth Persistence                │
│  - users table (id, email, hashed_password)            │
│  - developer_profiles table (skills, interests)        │
│  - Backward-compatible unauthenticated fallback        │
└────────────────────────────────────────────────────────┘
```

---

## Security Hardening & Defenses (Phase 13)

Phase 13 establishes zero-trust validation across all ingest points:
- **Path Traversal Protection**: `validate_repository_path()` prevents directory traversal (`../`, `..\`, null bytes, absolute paths).
- **Prompt Injection Defense**: Untrusted content wrapped in strict XML/markdown boundaries (`=== UNTRUSTED REPOSITORY CONTEXT ===`).
- **Input Boundedness**: Strict maximum lengths on all user inputs, schemas, and query parameters.
- **Sanitized Errors**: Internal stack traces and database credentials suppressed in production HTTP 500 responses.
- **Automated Security Verification**: 57 dedicated security tests across 26 threat vectors.

---

## Docker & Containerization Topology (Phase 14)

Phase 14 orchestrates a multi-service production topology:

```text
┌────────────────────────────────────────────────────────┐
│                     Host Machine                       │
│  Ports: 3000 (Frontend), 8000 (Backend), 11434 (Ollama)│
└───────────────────────────┬────────────────────────────┘
                            │ Docker Bridge (opencopilot_net)
                            ▼
┌────────────────────────────────────────────────────────┐
│                     Docker Network                     │
│  ├── postgres:16-alpine (pgvector enabled)             │
│  ├── ollama:latest (llama3.2:3b local LLM)             │
│  ├── backend:python-3.11-slim (non-root appuser)       │
│  └── frontend:node-20-alpine (multi-stage runner)      │
└────────────────────────────────────────────────────────┘
```

---

## Theme & Design System Architecture (Phase 15)

Phase 15 introduces a comprehensive, accessible design system supporting both Light and Dark modes:

```text
┌────────────────────────────────────────────────────────┐
│                  NextThemes Provider                   │
│  - attribute="class", defaultTheme="system"            │
│  - enableSystem=true, localStorage persistence         │
│  - suppressHydrationWarning on root <html>             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               CSS Variable Token System                │
│  :root (Light Mode Tokens)                             │
│    --background: 0 0% 100%                             │
│    --foreground: 222 47% 11%                           │
│    --card: 0 0% 100% / --border: 214 32% 91%           │
│  .dark (Dark Mode Tokens)                              │
│    --background: 222 47% 7%                            │
│    --foreground: 210 40% 98%                           │
│    --card: 222 47% 9% / --border: 217 33% 18%          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Component Primitives                 │
│  - Semantic tokens: bg-background, text-foreground     │
│  - Dual-contrast badges: text-amber-600 dark:text-amber-400
│  - Smooth transitions and prefers-reduced-motion check │
│  - ThemeToggle in Navigation Bar (desktop & mobile)    │
└────────────────────────────────────────────────────────┘
```

