"""
Unit tests for the RAG retrieval mode switching and keyword fallback system (Phase 8).
Verifies that when vector search fails or repository is unindexed, it falls back to keyword retrieval.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.rag.models import RepositoryChunk, RepositoryDocument, RetrievedChunk
from app.rag.service import RepositoryRAGService


def _make_doc(content: str, path: str = "src/app.py") -> RepositoryDocument:
    return RepositoryDocument(
        repository="pallets/flask",
        owner="pallets",
        repo_name="flask",
        branch="main",
        file_path=path,
        file_name=path.split("/")[-1],
        category="source",
        language="Python",
        sha="123",
        content=content,
        size_bytes=len(content),
    )


@pytest.mark.asyncio
class TestRAGRetrievalFallback:
    """Tests for vector -> keyword fallback mechanism."""

    async def test_fallback_when_vector_search_returns_no_results(self):
        doc = _make_doc("def create_app(): return Flask(__name__)")

        mock_loader = AsyncMock()
        mock_loader.load_documents.return_value = ([doc], MagicMock(documents_loaded=1, documents_skipped=0, truncated_files=0, total_content_chars=50))

        mock_vector_retriever = AsyncMock()
        # Vector retriever returns 0 results (unindexed repository)
        mock_vector_retriever.retrieve.return_value = []

        service = RepositoryRAGService(
            document_loader=mock_loader,
            vector_retriever=mock_vector_retriever,
        )

        result = await service.retrieve_for_query(
            url="https://github.com/pallets/flask",
            query="create_app",
            retrieval_mode="vector",
        )

        # Vector retriever was tried
        mock_vector_retriever.retrieve.assert_called_once()
        # Fell back to keyword retrieval
        assert result.retrieval_mode == "keyword_fallback"
        assert len(result.results) > 0
        assert "create_app" in result.results[0].chunk.content

    async def test_fallback_when_vector_search_raises_exception(self):
        doc = _make_doc("def create_app(): return Flask(__name__)")

        mock_loader = AsyncMock()
        mock_loader.load_documents.return_value = ([doc], MagicMock(documents_loaded=1, documents_skipped=0, truncated_files=0, total_content_chars=50))

        mock_vector_retriever = AsyncMock()
        # Database connection failure
        mock_vector_retriever.retrieve.side_effect = ConnectionRefusedError("PostgreSQL port 5432 unreachable")

        service = RepositoryRAGService(
            document_loader=mock_loader,
            vector_retriever=mock_vector_retriever,
        )

        result = await service.retrieve_for_query(
            url="https://github.com/pallets/flask",
            query="create_app",
            retrieval_mode="vector",
        )

        assert result.retrieval_mode == "keyword_fallback"
        assert len(result.results) > 0

    async def test_explicit_keyword_mode_skips_vector_retriever(self):
        doc = _make_doc("def create_app(): return Flask(__name__)")

        mock_loader = AsyncMock()
        mock_loader.load_documents.return_value = ([doc], MagicMock(documents_loaded=1, documents_skipped=0, truncated_files=0, total_content_chars=50))

        mock_vector_retriever = AsyncMock()

        service = RepositoryRAGService(
            document_loader=mock_loader,
            vector_retriever=mock_vector_retriever,
        )

        result = await service.retrieve_for_query(
            url="https://github.com/pallets/flask",
            query="create_app",
            retrieval_mode="keyword",
        )

        # Vector retriever should NOT be called
        mock_vector_retriever.retrieve.assert_not_called()
        assert result.retrieval_mode == "keyword"
        assert len(result.results) > 0

    async def test_context_for_query_preserves_retrieval_mode(self):
        doc = _make_doc("def create_app(): return Flask(__name__)")

        mock_loader = AsyncMock()
        mock_loader.load_documents.return_value = ([doc], MagicMock(documents_loaded=1, documents_skipped=0, truncated_files=0, total_content_chars=50))

        mock_vector_retriever = AsyncMock()
        mock_vector_retriever.retrieve.return_value = []

        service = RepositoryRAGService(
            document_loader=mock_loader,
            vector_retriever=mock_vector_retriever,
        )

        context_res = await service.context_for_query(
            url="https://github.com/pallets/flask",
            query="create_app",
            retrieval_mode="vector",
        )

        assert context_res.retrieval_mode == "keyword_fallback"
        assert "create_app" in context_res.context
