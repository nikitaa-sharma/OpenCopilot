from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """
    Core application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=[
            str(ROOT_DIR / ".env"),
            str(BACKEND_DIR / ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "OpenSource Copilot API"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Authentication & Security (Phase 12)
    AUTH_SECRET_KEY: str = "dev-insecure-secret-key-change-in-production-min-32-chars-long"
    AUTH_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins: List[str] = []
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                import json
                try:
                    origins = json.loads(v_stripped)
                except Exception:
                    origins = [i.strip().strip("'\"") for i in v_stripped.strip("[]").split(",") if i.strip()]
            else:
                origins = [i.strip() for i in v_stripped.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = list(v)

        seen = set()
        deduped: List[str] = []
        for o in origins:
            clean_origin = o.rstrip("/")
            if clean_origin and clean_origin not in seen:
                seen.add(clean_origin)
                deduped.append(clean_origin)
        return deduped

    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/opencopilot"

    # GitHub API Configuration
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_REQUEST_TIMEOUT: int = 30

    # Ingestion & Safety Limits (Phase 4)
    MAX_TREE_ITEMS: int = 10000          # Max items processed from recursive git tree
    MAX_SOURCE_FILES: int = 100          # Max source/doc files ingested in batch operation
    MAX_FILE_SIZE_BYTES: int = 100 * 1024  # Max size per individual file (100 KB)
    MAX_TOTAL_CODE_BYTES: int = 2 * 1024 * 1024  # Max total code ingested (2 MB)

    # AI / LLM Configuration (Modular & Replaceable)
    LLM_PROVIDER: str = "ollama"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3.2:3b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 4096
    LLM_REQUEST_TIMEOUT: float = 120.0

    # AI Context Building & Safety Limits
    AI_MAX_CONTEXT_CHARS: int = 60000
    AI_MAX_FILES_IN_CONTEXT: int = 15
    AI_MAX_FILE_CHARS: int = 6000

    # RAG Pipeline Configuration (Phase 7 & 8)
    RAG_CHUNK_SIZE: int = 1200          # Target chunk size in characters
    RAG_CHUNK_OVERLAP: int = 150        # Overlap between chunks in characters (line-based fallback)
    RAG_MAX_CHUNKS_PER_FILE: int = 100  # Maximum chunks produced per document
    RAG_MAX_TOTAL_CHUNKS: int = 5000    # Maximum total chunks across entire repository
    RAG_TOP_K: int = 5                  # Default number of retrieval results
    RAG_MAX_CONTEXT_CHARS: int = 12000  # Maximum context characters for LLM prompt
    RAG_RETRIEVAL_MODE: str = "vector"  # "vector" or "keyword"

    # Embeddings Configuration (Phase 8 & Phase 16)
    # Options: "sentence_transformers" (local CPU) or "openai" (remote API)
    EMBEDDING_PROVIDER: str = "sentence_transformers"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""


settings = Settings()


