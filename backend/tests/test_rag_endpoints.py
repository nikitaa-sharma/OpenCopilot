"""
Tests for the RAG API endpoints:
  POST /api/v1/repositories/rag/retrieve
  POST /api/v1/repositories/rag/context
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.rag.models import RAGStatistics, RepositoryChunk, RetrievedChunk
from app.rag.service import RAGRetrievalResult, RAGContextResult

client = TestClient(app)


def _make_retrieved_chunk(
    file_path: str = "src/app.py",
    content: str = "def create_app():\n    return Flask(__name__)",
    score: float = 5.5,
) -> RetrievedChunk:
    chunk = RepositoryChunk(
        chunk_id=f"pallets/flask:{file_path}:0",
        repository="pallets/flask",
        file_path=file_path,
        language="Python",
        category="source",
        chunk_index=0,
        start_line=1,
        end_line=5,
        content=content,
        metadata={},
    )
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        matched_terms=["flask", "application"],
        retrieval_reason="Matched flask and application in content.",
    )


def _make_stats(docs_loaded=5, chunks_created=20, results_returned=2) -> RAGStatistics:
    return RAGStatistics(
        documents_loaded=docs_loaded,
        documents_skipped=1,
        chunks_created=chunks_created,
        chunks_searched=chunks_created,
        results_returned=results_returned,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /rag/retrieve tests
# ──────────────────────────────────────────────────────────────────────────────

def test_rag_retrieve_valid_repository():
    """Valid request returns retrieval results with statistics."""
    mock_result = RAGRetrievalResult(
        repository="pallets/flask",
        query="Flask application class",
        results=[_make_retrieved_chunk()],
        statistics=_make_stats(results_returned=1),
    )
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
        new=AsyncMock(return_value=mock_result),
    ):
        response = client.post(
            "/api/v1/repositories/rag/retrieve",
            json={
                "repository_url": "https://github.com/pallets/flask",
                "query": "Flask application class",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "pallets/flask"
    assert data["query"] == "Flask application class"
    assert len(data["results"]) == 1
    chunk = data["results"][0]
    assert chunk["file_path"] == "src/app.py"
    assert chunk["score"] == 5.5
    assert "retrieval_reason" in chunk


def test_rag_retrieve_invalid_url():
    """Invalid GitHub URL returns 400."""
    from app.services.github_service import InvalidGitHubURLError
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
        new=AsyncMock(side_effect=InvalidGitHubURLError("Invalid URL")),
    ):
        response = client.post(
            "/api/v1/repositories/rag/retrieve",
            json={"repository_url": "not-a-url", "query": "Flask"},
        )
    assert response.status_code == 400


def test_rag_retrieve_not_found():
    """Nonexistent repository returns 404."""
    from app.services.github_service import GitHubNotFoundError
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
        new=AsyncMock(side_effect=GitHubNotFoundError("Not found")),
    ):
        response = client.post(
            "/api/v1/repositories/rag/retrieve",
            json={"repository_url": "https://github.com/nonexistent/repo", "query": "test"},
        )
    assert response.status_code == 404


def test_rag_retrieve_rate_limit():
    """Rate limit exceeded returns 403."""
    from app.services.github_service import GitHubRateLimitError
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
        new=AsyncMock(side_effect=GitHubRateLimitError("Rate limited")),
    ):
        response = client.post(
            "/api/v1/repositories/rag/retrieve",
            json={"repository_url": "https://github.com/pallets/flask", "query": "test"},
        )
    assert response.status_code == 403


def test_rag_retrieve_empty_query():
    """Empty query returns valid response with empty results."""
    mock_result = RAGRetrievalResult(
        repository="pallets/flask",
        query="",
        results=[],
        statistics=_make_stats(results_returned=0),
    )
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.retrieve_for_query",
        new=AsyncMock(return_value=mock_result),
    ):
        response = client.post(
            "/api/v1/repositories/rag/retrieve",
            json={"repository_url": "https://github.com/pallets/flask", "query": ""},
        )
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_rag_retrieve_top_k_validation():
    """top_k must be between 1 and 20."""
    response = client.post(
        "/api/v1/repositories/rag/retrieve",
        json={
            "repository_url": "https://github.com/pallets/flask",
            "query": "Flask",
            "top_k": 0,  # Invalid: must be >= 1
        },
    )
    assert response.status_code == 422  # Validation error


# ──────────────────────────────────────────────────────────────────────────────
# POST /rag/context tests
# ──────────────────────────────────────────────────────────────────────────────

def test_rag_context_valid_repository():
    """Valid request returns context string and retrieved chunks."""
    context_str = (
        "Repository Context\n"
        "============================================================\n\n"
        "File: src/app.py\nLanguage: Python\nLines: 1-5\n\n"
        "def create_app():\n    return Flask(__name__)\n\n---\n\n"
    )
    mock_result = RAGContextResult(
        repository="pallets/flask",
        query="Flask application",
        context=context_str,
        retrieved_chunks=[_make_retrieved_chunk()],
        statistics=_make_stats(results_returned=1),
    )
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.context_for_query",
        new=AsyncMock(return_value=mock_result),
    ):
        response = client.post(
            "/api/v1/repositories/rag/context",
            json={
                "repository_url": "https://github.com/pallets/flask",
                "query": "Flask application",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "pallets/flask"
    assert "context" in data
    assert "src/app.py" in data["context"]
    assert len(data["retrieved_chunks"]) == 1


def test_rag_context_includes_statistics():
    """Response includes retrieval statistics."""
    mock_result = RAGContextResult(
        repository="pallets/flask",
        query="Flask",
        context="Repository Context\n" + "=" * 60 + "\n",
        retrieved_chunks=[],
        statistics=_make_stats(docs_loaded=10, chunks_created=50, results_returned=0),
    )
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.context_for_query",
        new=AsyncMock(return_value=mock_result),
    ):
        response = client.post(
            "/api/v1/repositories/rag/context",
            json={"repository_url": "https://github.com/pallets/flask", "query": "Flask"},
        )

    assert response.status_code == 200
    stats = response.json()["statistics"]
    assert stats["documents_loaded"] == 10
    assert stats["chunks_created"] == 50


def test_rag_context_invalid_url():
    """Invalid URL returns 400."""
    from app.services.github_service import InvalidGitHubURLError
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.context_for_query",
        new=AsyncMock(side_effect=InvalidGitHubURLError("Invalid")),
    ):
        response = client.post(
            "/api/v1/repositories/rag/context",
            json={"repository_url": "not-valid", "query": "Flask"},
        )
    assert response.status_code == 400


def test_rag_context_service_unavailable():
    """GitHub service error returns 503."""
    from app.services.github_service import GitHubServiceError
    with patch(
        "app.api.v1.endpoints.repositories.repository_rag_service.context_for_query",
        new=AsyncMock(side_effect=GitHubServiceError("GitHub unavailable")),
    ):
        response = client.post(
            "/api/v1/repositories/rag/context",
            json={"repository_url": "https://github.com/pallets/flask", "query": "Flask"},
        )
    assert response.status_code == 503
