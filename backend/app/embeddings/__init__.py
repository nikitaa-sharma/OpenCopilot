"""
Embedding subsystem package for OpenSource Copilot.
"""

from app.embeddings.base import (
    EmbeddingInferenceError,
    EmbeddingModelLoadError,
    EmbeddingProvider,
    EmbeddingProviderError,
)
from app.embeddings.factory import get_embedding_provider, reset_embedding_provider
from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingModelLoadError",
    "EmbeddingInferenceError",
    "SentenceTransformerEmbeddingProvider",
    "get_embedding_provider",
    "reset_embedding_provider",
]
