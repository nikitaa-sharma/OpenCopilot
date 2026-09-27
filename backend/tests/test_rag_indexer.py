"""
Unit tests for RepositoryIndexer service (Phase 8).
Verifies SHA-256 hashing, chunk re-use, batch embedding, and indexing statistics.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.rag.indexer import RepositoryIndexer, compute_content_hash
from app.rag.models import RepositoryChunk, RepositoryDocument


def _make_doc(content: str, path: str = "app/main.py") -> RepositoryDocument:
    return RepositoryDocument(
        repository="test-owner/test-repo",
        owner="test-owner",
        repo_name="test-repo",
        branch="main",
        file_path=path,
        file_name=path.split("/")[-1],
        category="source",
        language="Python",
        sha="abc123",
        content=content,
        size_bytes=len(content),
    )


def test_compute_content_hash_determinism():
    h1 = compute_content_hash("def hello(): return 'world'")
    h2 = compute_content_hash("def hello(): return 'world'")
    h3 = compute_content_hash("def hello(): return 'world!'")

    assert h1 == h2
    assert len(h1) == 64
    assert h1 != h3


@pytest.mark.asyncio
class TestRepositoryIndexer:
    """Tests for repository vector indexing workflow."""

    async def test_index_new_repository_embeds_all_chunks(self):
        doc = _make_doc("def func_one(): pass\n\ndef func_two(): pass")

        mock_loader = AsyncMock()
        mock_stats = MagicMock()
        mock_loader.load_documents.return_value = ([doc], mock_stats)

        mock_provider = MagicMock()
        mock_provider.dimension = 384
        mock_provider.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]

        indexer = RepositoryIndexer(
            document_loader=mock_loader,
            embedding_provider=mock_provider,
        )

        # Mock database session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("app.rag.indexer.init_db", AsyncMock(return_value=True)):
            res = await indexer.index_repository(
                url="https://github.com/test-owner/test-repo",
                session=mock_session,
            )

        assert res.repository == "test-owner/test-repo"
        assert res.documents_processed == 1
        assert res.chunks_created > 0
        assert res.chunks_embedded == res.chunks_created
        assert res.chunks_reused == 0
        assert res.embedding_dimension == 384
        assert res.elapsed_time_seconds >= 0

    async def test_index_unchanged_chunks_reuses_embeddings(self):
        content = "def calculate_sum(a, b): return a + b"
        doc = _make_doc(content, "app/calc.py")

        mock_loader = AsyncMock()
        mock_loader.load_documents.return_value = ([doc], MagicMock())

        mock_provider = MagicMock()
        mock_provider.dimension = 384
        mock_provider.embed_documents.return_value = []

        indexer = RepositoryIndexer(
            document_loader=mock_loader,
            embedding_provider=mock_provider,
        )

        # Simulate existing chunk in database with identical content hash
        c_hash = compute_content_hash(content)
        mock_existing_chunk = MagicMock()
        mock_existing_chunk.file_path = "app/calc.py"
        mock_existing_chunk.chunk_index = 0
        mock_existing_chunk.content_hash = c_hash
        mock_existing_chunk.embedding = [0.1] * 384

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_existing_chunk]
        mock_session.execute.return_value = mock_result

        with patch("app.rag.indexer.init_db", AsyncMock(return_value=True)):
            res = await indexer.index_repository(
                url="https://github.com/test-owner/test-repo",
                session=mock_session,
            )

        assert res.chunks_reused == 1
        assert res.chunks_embedded == 0
        # embed_documents should NOT have been called since chunk was reused
        mock_provider.embed_documents.assert_not_called()

    async def test_index_changed_chunk_updates_embedding(self):
        old_content = "def calc(): return 1"
        new_content = "def calc(): return 2"
        doc = _make_doc(new_content, "app/calc.py")

        mock_loader = AsyncMock()
        mock_loader.load_documents.return_value = ([doc], MagicMock())

        mock_provider = MagicMock()
        mock_provider.dimension = 384
        mock_provider.embed_documents.return_value = [[0.9] * 384]

        indexer = RepositoryIndexer(
            document_loader=mock_loader,
            embedding_provider=mock_provider,
        )

        # Existing chunk has old content hash
        mock_existing_chunk = MagicMock()
        mock_existing_chunk.file_path = "app/calc.py"
        mock_existing_chunk.chunk_index = 0
        mock_existing_chunk.content_hash = compute_content_hash(old_content)
        mock_existing_chunk.embedding = [0.1] * 384

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_existing_chunk]
        mock_session.execute.return_value = mock_result

        with patch("app.rag.indexer.init_db", AsyncMock(return_value=True)):
            res = await indexer.index_repository(
                url="https://github.com/test-owner/test-repo",
                session=mock_session,
            )

        assert res.chunks_reused == 0
        assert res.chunks_embedded == 1
        assert res.chunks_updated == 1
        mock_provider.embed_documents.assert_called_once()
