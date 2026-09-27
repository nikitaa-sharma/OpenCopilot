"""
Sentence Transformers embedding provider for local CPU execution.

Supports BAAI/bge-small-en-v1.5 and any sentence-transformers model.
Features lazy loading, cosine normalization, and BGE query prefixing.
"""

import logging
import threading
from typing import Any, List, Optional

from app.core.config import settings
from app.embeddings.base import (
    EmbeddingInferenceError,
    EmbeddingModelLoadError,
    EmbeddingProvider,
)

logger = logging.getLogger(__name__)

# Standard instruction prefix recommended by BAAI for BGE query encoding
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider based on the sentence-transformers library.

    - Loads the model lazily on first inference request.
    - Executes on CPU (or configured device).
    - Returns unit-normalized vectors (Euclidean norm = 1.0) so dot product == cosine similarity.
    - Applies the BGE instruction prefix when encoding queries with BGE models.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        dimension: Optional[int] = None,
        device: Optional[str] = None,
        model_instance: Optional[Any] = None,
    ):
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._dimension = dimension or settings.EMBEDDING_DIMENSION
        self._device = device or settings.EMBEDDING_DEVICE
        self._model = model_instance
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_model(self) -> Any:
        """Lazily loads the SentenceTransformer model in a thread-safe manner."""
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            try:
                logger.info(
                    f"Loading local embedding model '{self._model_name}' on device '{self._device}'..."
                )
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(self._model_name, device=self._device)
                self._model = model
                logger.info(
                    f"Embedding model '{self._model_name}' successfully loaded (dimension: {self._dimension})."
                )
                return self._model
            except Exception as exc:
                logger.error(
                    f"Failed to load embedding model '{self._model_name}': {exc}"
                )
                raise EmbeddingModelLoadError(
                    f"Could not load local embedding model '{self._model_name}'. "
                    f"Ensure sentence-transformers and PyTorch are installed and internet/cache is available. Details: {exc}"
                ) from exc

    def _prepare_text(self, text: str, is_query: bool) -> str:
        """Applies query instruction prefix if model is BGE and is_query is True."""
        clean_text = text.strip()
        if is_query and "bge" in self._model_name.lower():
            if not clean_text.startswith(_BGE_QUERY_PREFIX):
                return f"{_BGE_QUERY_PREFIX}{clean_text}"
        return clean_text

    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        """
        Embed a single text string into a normalized vector.
        """
        if not text or not text.strip():
            # Return zero vector if text is empty
            return [0.0] * self._dimension

        prepared = self._prepare_text(text, is_query)
        model = self._get_model()

        try:
            vector = model.encode(
                prepared,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            # Ensure float list
            if hasattr(vector, "tolist"):
                return vector.tolist()
            return list(vector)
        except Exception as exc:
            logger.error(f"Error during single text embedding: {exc}")
            raise EmbeddingInferenceError(f"Embedding inference failed: {exc}") from exc

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of document texts into normalized vectors.
        """
        if not texts:
            return []

        prepared = [self._prepare_text(t, is_query=False) for t in texts]
        model = self._get_model()

        try:
            batch_size = settings.EMBEDDING_BATCH_SIZE
            vectors = model.encode(
                prepared,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            if hasattr(vectors, "tolist"):
                return vectors.tolist()
            return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]
        except Exception as exc:
            logger.error(f"Error during batch document embedding: {exc}")
            raise EmbeddingInferenceError(
                f"Batch document embedding failed: {exc}"
            ) from exc
