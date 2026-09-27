"""
Factory for creating and resolving the configured EmbeddingProvider.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.embeddings.base import EmbeddingProvider, EmbeddingProviderError
from app.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider

logger = logging.getLogger(__name__)

_cached_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """
    Returns the singleton EmbeddingProvider configured in settings.
    Avoids repeatedly loading model weights or recreating providers.
    """
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider

    provider_name = settings.EMBEDDING_PROVIDER.lower().strip()

    if provider_name in ("sentence_transformers", "sentence-transformers", "local"):
        _cached_provider = SentenceTransformerEmbeddingProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
            device=settings.EMBEDDING_DEVICE,
        )
        return _cached_provider
    elif provider_name in ("openai", "remote", "hosted"):
        from app.embeddings.openai_provider import OpenAIEmbeddingProvider

        _cached_provider = OpenAIEmbeddingProvider(
            api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
            base_url=settings.EMBEDDING_BASE_URL,
        )
        return _cached_provider

    raise EmbeddingProviderError(
        f"Unsupported embedding provider '{settings.EMBEDDING_PROVIDER}'. "
        f"Supported providers: 'sentence_transformers', 'openai'."
    )


def reset_embedding_provider() -> None:
    """Reset cached provider (useful for testing)."""
    global _cached_provider
    _cached_provider = None
