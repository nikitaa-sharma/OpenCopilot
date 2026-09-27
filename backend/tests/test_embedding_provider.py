"""
Unit tests for local embedding provider subsystem (Phase 8).
Tests lazy loading, configuration, dimension, query prefixing, and error handling without downloading weights.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.embeddings.base import (
    EmbeddingInferenceError,
    EmbeddingModelLoadError,
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.embeddings.factory import get_embedding_provider, reset_embedding_provider
from app.embeddings.sentence_transformer_provider import (
    _BGE_QUERY_PREFIX,
    SentenceTransformerEmbeddingProvider,
)


class TestSentenceTransformerEmbeddingProvider:
    """Tests for SentenceTransformerEmbeddingProvider."""

    def test_provider_configuration(self):
        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
            device="cpu",
        )
        assert provider.model_name == "BAAI/bge-small-en-v1.5"
        assert provider.dimension == 384
        assert provider._device == "cpu"
        # Model should NOT be loaded upon instantiation
        assert provider._model is None

    def test_embed_text_with_mock_model(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384

        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
            model_instance=mock_model,
        )

        vector = provider.embed_text("Test python function", is_query=False)
        assert len(vector) == 384
        assert vector[0] == 0.1
        # Should not apply query prefix for documents
        mock_model.encode.assert_called_once_with(
            "Test python function",
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def test_embed_text_query_prefix_applied_for_bge(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.2] * 384

        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
            model_instance=mock_model,
        )

        vector = provider.embed_text("Where is the database session defined?", is_query=True)
        assert len(vector) == 384

        # Verify BGE query prefix was applied
        expected_call_arg = f"{_BGE_QUERY_PREFIX}Where is the database session defined?"
        mock_model.encode.assert_called_once_with(
            expected_call_arg,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def test_embed_text_empty_returns_zero_vector(self):
        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
        )
        vector = provider.embed_text("")
        assert vector == [0.0] * 384

        vector_whitespace = provider.embed_text("   ")
        assert vector_whitespace == [0.0] * 384

    def test_embed_documents_batch(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1] * 384, [0.2] * 384]

        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
            model_instance=mock_model,
        )

        docs = ["def hello(): pass", "class World: pass"]
        vectors = provider.embed_documents(docs)

        assert len(vectors) == 2
        assert len(vectors[0]) == 384
        assert len(vectors[1]) == 384
        mock_model.encode.assert_called_once()

    def test_embed_documents_empty_list(self):
        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
        )
        assert provider.embed_documents([]) == []

    def test_model_load_failure_raises_clean_error(self):
        provider = SentenceTransformerEmbeddingProvider(
            model_name="nonexistent/model-that-does-not-exist",
            dimension=384,
        )
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with pytest.raises(EmbeddingModelLoadError) as exc_info:
                provider.embed_text("test")
            assert "Could not load local embedding model" in str(exc_info.value)

    def test_inference_failure_raises_clean_error(self):
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("CUDA Out of Memory")

        provider = SentenceTransformerEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384,
            model_instance=mock_model,
        )
        with pytest.raises(EmbeddingInferenceError) as exc_info:
            provider.embed_text("test")
        assert "Embedding inference failed" in str(exc_info.value)


class TestEmbeddingFactory:
    """Tests for the embedding factory and singleton resolution."""

    def test_get_embedding_provider_sentence_transformers(self):
        reset_embedding_provider()
        with patch("app.core.config.settings.EMBEDDING_PROVIDER", "sentence_transformers"):
            provider = get_embedding_provider()
            assert isinstance(provider, SentenceTransformerEmbeddingProvider)
            assert provider.dimension == 384
            # Should be cached singleton
            assert get_embedding_provider() is provider

    def test_get_embedding_provider_unsupported(self):
        reset_embedding_provider()
        with patch("app.core.config.settings.EMBEDDING_PROVIDER", "unsupported_provider_xyz"):
            with pytest.raises(EmbeddingProviderError) as exc_info:
                get_embedding_provider()
            assert "Unsupported embedding provider" in str(exc_info.value)
