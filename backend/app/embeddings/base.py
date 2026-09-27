"""
Abstract base class and exception hierarchy for embedding providers.
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProviderError(Exception):
    """Base exception for all embedding provider errors."""
    pass


class EmbeddingModelLoadError(EmbeddingProviderError):
    """Raised when the embedding model cannot be loaded."""
    pass


class EmbeddingInferenceError(EmbeddingProviderError):
    """Raised when embedding generation fails."""
    pass


class EmbeddingProvider(ABC):
    """
    Abstract interface for local and remote embedding providers.
    Decouples the RAG indexing and vector retrieval subsystems
    from specific embedding libraries and models.
    """

    @abstractmethod
    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        """
        Generate a normalized embedding vector for a single text.

        Args:
            text: Input string.
            is_query: Whether this text is a retrieval query (applies query prefix if model requires).

        Returns:
            List of floats representing the embedding vector.
        """
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate normalized embedding vectors for a batch of documents.

        Args:
            texts: List of document/chunk strings.

        Returns:
            List of embedding vectors (one per input text).
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension produced by this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or path of the underlying model."""
        pass
