"""
Remote OpenAI-compatible embedding provider.
Calls the OpenAI /v1/embeddings API or any compatible endpoint.
Defaults to text-embedding-3-small with dimension=384.
"""

import logging
import math
from typing import List, Optional
import httpx

from app.core.config import settings
from app.embeddings.base import (
    EmbeddingInferenceError,
    EmbeddingProvider,
)

logger = logging.getLogger(__name__)


def _normalize(vec: List[float]) -> List[float]:
    """L2-normalize a vector to unit length (norm = 1.0)."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Remote embedding provider using OpenAI-compatible embeddings API.
    Lightweight, fast, and does not require PyTorch or local weights.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        dimension: Optional[int] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self._api_key = api_key or settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        configured_model = model_name or settings.EMBEDDING_MODEL
        if not configured_model or "bge" in configured_model.lower():
            self._model_name = "text-embedding-3-small"
        else:
            self._model_name = configured_model

        self._dimension = dimension or settings.EMBEDDING_DIMENSION or 384

        base = (
            base_url
            or settings.EMBEDDING_BASE_URL
            or (settings.LLM_BASE_URL if "openai" in (settings.LLM_BASE_URL or "") else "")
            or "https://api.openai.com/v1"
        ).rstrip("/")

        if base == "http://localhost:11434" or not base:
            base = "https://api.openai.com/v1"

        if base.endswith("/embeddings"):
            self._url = base
        elif base.endswith("/v1"):
            self._url = f"{base}/embeddings"
        else:
            self._url = f"{base}/v1/embeddings"

        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _call_api(self, texts: List[str]) -> List[List[float]]:
        if not self._api_key:
            raise EmbeddingInferenceError(
                "API key is not configured for OpenAI embedding provider. "
                "Please set EMBEDDING_API_KEY or LLM_API_KEY."
            )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self._model_name,
        }
        # text-embedding-3-* models natively support custom dimensions
        if "text-embedding-3" in self._model_name:
            payload["dimensions"] = self._dimension

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(self._url, json=payload, headers=headers)
        except Exception as exc:
            logger.error(f"Failed to connect to embedding API at {self._url}: {exc}")
            raise EmbeddingInferenceError(f"Embedding API connection failed: {exc}") from exc

        if response.status_code != 200:
            logger.error(f"Embedding API error HTTP {response.status_code}: {response.text}")
            raise EmbeddingInferenceError(
                f"Embedding API error (HTTP {response.status_code}): {response.text}"
            )

        try:
            data = response.json()
            items = data.get("data", [])
            sorted_items = sorted(items, key=lambda x: x.get("index", 0))
            vectors = [item["embedding"] for item in sorted_items]

            result = []
            for v in vectors:
                if len(v) != self._dimension:
                    if len(v) > self._dimension:
                        v = v[:self._dimension]
                    else:
                        v = v + [0.0] * (self._dimension - len(v))
                result.append(_normalize(v))
            return result
        except Exception as exc:
            if isinstance(exc, EmbeddingInferenceError):
                raise
            raise EmbeddingInferenceError(f"Failed to parse embedding response: {exc}") from exc

    def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dimension
        results = self._call_api([text.strip()])
        if not results:
            return [0.0] * self._dimension
        return results[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        batch_size = 32
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = [t.strip() if t.strip() else " " for t in texts[i:i + batch_size]]
            all_embeddings.extend(self._call_api(batch))
        return all_embeddings
