"""
Domain models for the RAG pipeline.

Provides structured representations for repository documents, chunks,
retrieval results, and pipeline statistics.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RepositoryDocument(BaseModel):
    """Represents a single file loaded from a repository for RAG processing."""

    repository: str = Field(..., description="'owner/repo' format")
    owner: str = Field(..., description="Repository owner")
    repo_name: str = Field(..., description="Repository name")
    branch: str = Field(..., description="Branch or commit ref")
    file_path: str = Field(..., description="Full path within the repository")
    file_name: str = Field(..., description="Filename without directory")
    category: str = Field(
        ...,
        description="File classification: source, test, documentation, configuration",
    )
    language: Optional[str] = Field(None, description="Detected programming language")
    sha: Optional[str] = Field(None, description="Git blob SHA")
    content: str = Field(..., description="Full file text content")
    size_bytes: int = Field(0, description="Content size in bytes")


class RepositoryChunk(BaseModel):
    """A chunk produced by splitting a RepositoryDocument."""

    chunk_id: str = Field(
        ...,
        description="Deterministic ID: '{repository}:{file_path}:{chunk_index}'",
    )
    repository: str = Field(..., description="'owner/repo' format")
    file_path: str = Field(..., description="Source file path")
    language: Optional[str] = Field(None, description="Programming language")
    category: str = Field(..., description="File category")
    chunk_index: int = Field(..., description="Zero-based chunk index within file")
    start_line: int = Field(..., description="1-based start line in source file")
    end_line: int = Field(..., description="1-based end line in source file")
    content: str = Field(..., description="Chunk text content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata for future embeddings/vectors",
    )


class RetrievedChunk(BaseModel):
    """A chunk returned by the retriever with scoring information."""

    chunk: RepositoryChunk
    score: float = Field(..., description="Relevance score (higher is better)")
    matched_terms: List[str] = Field(
        default_factory=list,
        description="Query terms that matched in this chunk",
    )
    retrieval_reason: str = Field(
        ...,
        description="Human-readable explanation of why this chunk was selected",
    )


class RAGStatistics(BaseModel):
    """Pipeline statistics for a RAG operation."""

    documents_loaded: int = 0
    documents_skipped: int = 0
    chunks_created: int = 0
    chunks_searched: int = 0
    results_returned: int = 0
    truncated_files: int = 0
    total_content_chars: int = 0
