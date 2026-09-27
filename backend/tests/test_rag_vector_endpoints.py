"""
Tests for Phase 8 Vector RAG API Endpoints:
  POST /api/v1/repositories/rag/index
  POST /api/v1/repositories/rag/vector-search
  POST /api/v1/repositories/rag/context (updated with retrieval_mode)
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.embeddings.base import EmbeddingModelLoadError
from app.main import app
from app.rag.indexer import RAGIndexResult
from app.rag.models import RAGStatistics, RepositoryChunk, RetrievedChunk
from app.rag.service import RAGContextResult, RAGRetrievalResult
from app.services.github_service import (
    GitHubNotFoundError,
    GitHubRateLimitError,
    InvalidGitHubURLError,
)

client = TestClient(app)


def _make_sample_retrieved_chunk(score: float = 0.88) -> RetrievedChunk:
    chunk = RepositoryChunk(
        chunk_id="pallets/flask:src/flask/app.py:0",
        repository="pallets/flask",
        file_path="src/flask/app.py",
        language="Python",
        category="source",
        chunk_index=0,
        start_line=1,
        end_line=50,
        content="class Flask:\n    def __init__(self):\n        pass",
        metadata={},
    )
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        matched_terms=[],
        retrieval_reason=f"Vector semantic similarity: {score:.4f}",
    )


class TestRAGIndexEndpoint:
    """Tests for POST /api/v1/repositories/rag/index."""

    def test_rag_index_success(self):
        sample_result = RAGIndexResult(
            repository="pallets/flask",
            documents_processed=25,
            chunks_created=110,
            chunks_embedded=90,
            chunks_reused=20,
            chunks_updated=0,
            chunks_skipped=0,
            embedding_dimension=384,
            elapsed_time_seconds=1.23,
        )

        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.index_repository",
            AsyncMock(return_value=sample_result),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/index",
                json={"repository_url": "https://github.com/pallets/flask"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"] == "pallets/flask"
        assert data["documents_processed"] == 25
        assert data["chunks_created"] == 110
        assert data["chunks_embedded"] == 90
        assert data["chunks_reused"] == 20
        assert data["embedding_dimension"] == 384
        assert data["elapsed_time_seconds"] == 1.23

    def test_rag_index_invalid_url_returns_400(self):
        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.index_repository",
            AsyncMock(side_effect=InvalidGitHubURLError("Invalid URL format.")),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/index",
                json={"repository_url": "invalid-url"},
            )
        assert resp.status_code == 400

    def test_rag_index_repo_not_found_returns_404(self):
        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.index_repository",
            AsyncMock(side_effect=GitHubNotFoundError("Repo not found")),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/index",
                json={"repository_url": "https://github.com/pallets/nonexistent"},
            )
        assert resp.status_code == 404

    def test_rag_index_embedding_failure_returns_503(self):
        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.index_repository",
            AsyncMock(side_effect=EmbeddingModelLoadError("Model weights missing")),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/index",
                json={"repository_url": "https://github.com/pallets/flask"},
            )
        assert resp.status_code == 503
        assert "Embedding provider error" in resp.json()["detail"]


class TestRAGVectorSearchEndpoint:
    """Tests for POST /api/v1/repositories/rag/vector-search."""

    def test_vector_search_success(self):
        retrieved_chunk = _make_sample_retrieved_chunk(0.92)
        stats = RAGStatistics(chunks_searched=150, results_returned=1)

        retrieval_result = RAGRetrievalResult(
            repository="pallets/flask",
            query="Flask application class",
            results=[retrieved_chunk],
            statistics=stats,
            retrieval_mode="vector",
        )

        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
            AsyncMock(return_value=retrieval_result),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/vector-search",
                json={
                    "repository_url": "https://github.com/pallets/flask",
                    "query": "Flask application class",
                    "top_k": 5,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"] == "pallets/flask"
        assert data["query"] == "Flask application class"
        assert data["retrieval_mode"] == "vector"
        assert len(data["results"]) == 1
        assert data["results"][0]["file_path"] == "src/flask/app.py"
        assert data["results"][0]["similarity_score"] == 0.92
        assert data["statistics"]["results_returned"] == 1

    def test_vector_search_invalid_url_returns_400(self):
        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
            AsyncMock(side_effect=InvalidGitHubURLError("Bad URL")),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/vector-search",
                json={
                    "repository_url": "bad-url",
                    "query": "hello",
                },
            )
        assert resp.status_code == 400


class TestRAGContextEndpointPhase8:
    """Tests for POST /api/v1/repositories/rag/context with retrieval_mode."""

    def test_context_endpoint_includes_retrieval_mode(self):
        retrieved_chunk = _make_sample_retrieved_chunk(0.85)
        stats = RAGStatistics(documents_loaded=1, chunks_created=5, chunks_searched=5, results_returned=1)

        context_result = RAGContextResult(
            repository="pallets/flask",
            query="where is app initialized?",
            context="### src/flask/app.py\n```python\nclass Flask: pass\n```",
            retrieved_chunks=[retrieved_chunk],
            statistics=stats,
            retrieval_mode="keyword_fallback",
        )

        with patch(
            "app.api.v1.endpoints.repositories.repository_rag_service.context_for_query",
            AsyncMock(return_value=context_result),
        ):
            resp = client.post(
                "/api/v1/repositories/rag/context",
                json={
                    "repository_url": "https://github.com/pallets/flask",
                    "query": "where is app initialized?",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["retrieval_mode"] == "keyword_fallback"
        assert data["repository"] == "pallets/flask"
        assert len(data["retrieved_chunks"]) == 1
