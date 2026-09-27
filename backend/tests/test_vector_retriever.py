"""
Unit tests for VectorRetriever (Phase 8).
Verifies query embedding, pgvector cosine similarity calculation, top_k ordering, and metadata mapping.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.rag.vector_retriever import VectorRetriever


@pytest.mark.asyncio
class TestVectorRetriever:
    """Tests for the pgvector semantic similarity retriever."""

    async def test_empty_query_returns_empty_results(self):
        retriever = VectorRetriever()
        res = await retriever.retrieve(query="", repository_identifier="pallets/flask")
        assert res == []

        res_space = await retriever.retrieve(query="   ", repository_identifier="pallets/flask")
        assert res_space == []

    async def test_retrieve_embeds_query_and_calculates_similarity(self):
        mock_provider = MagicMock()
        mock_provider.dimension = 384
        mock_provider.embed_text.return_value = [0.1] * 384

        retriever = VectorRetriever(embedding_provider=mock_provider)

        # Create mock DB rows: (chunk_model, cosine_distance)
        # Cosine distance 0.15 -> similarity 0.85
        # Cosine distance 0.40 -> similarity 0.60
        chunk_1 = MagicMock()
        chunk_1.repository_identifier = "pallets/flask"
        chunk_1.file_path = "src/flask/app.py"
        chunk_1.language = "Python"
        chunk_1.category = "source"
        chunk_1.chunk_index = 0
        chunk_1.start_line = 1
        chunk_1.end_line = 50
        chunk_1.content = "class Flask: pass"
        chunk_1.chunk_metadata = {"test": True}

        chunk_2 = MagicMock()
        chunk_2.repository_identifier = "pallets/flask"
        chunk_2.file_path = "src/flask/blueprints.py"
        chunk_2.language = "Python"
        chunk_2.category = "source"
        chunk_2.chunk_index = 0
        chunk_2.start_line = 1
        chunk_2.end_line = 40
        chunk_2.content = "class Blueprint: pass"
        chunk_2.chunk_metadata = {}

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (chunk_1, 0.15),
            (chunk_2, 0.40),
        ]
        mock_session.execute.return_value = mock_result

        results = await retriever.retrieve(
            query="Flask application class",
            repository_identifier="pallets/flask",
            top_k=2,
            session=mock_session,
        )

        # Verify query was embedded with is_query=True
        mock_provider.embed_text.assert_called_once_with(
            "Flask application class", is_query=True
        )

        assert len(results) == 2
        # Verify cosine similarity = 1.0 - distance
        assert results[0].score == 0.85
        assert results[0].chunk.file_path == "src/flask/app.py"
        assert "Vector semantic similarity: 0.8500" in results[0].retrieval_reason
        assert results[0].chunk.metadata == {"test": True}

        assert results[1].score == 0.60
        assert results[1].chunk.file_path == "src/flask/blueprints.py"

    async def test_retrieve_no_matches_returns_empty(self):
        mock_provider = MagicMock()
        mock_provider.dimension = 384
        mock_provider.embed_text.return_value = [0.1] * 384

        retriever = VectorRetriever(embedding_provider=mock_provider)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await retriever.retrieve(
            query="unmatched question",
            repository_identifier="pallets/flask",
            top_k=5,
            session=mock_session,
        )

        assert results == []
