"""
Unit tests for Vercel deployment providers (Phase 16).
Tests OpenAICompatibleProvider, OpenAIEmbeddingProvider, and factory dispatching.
"""

from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.core.config import settings
from app.embeddings.base import EmbeddingInferenceError
from app.embeddings.factory import get_embedding_provider, reset_embedding_provider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.services.llm_factory import get_llm_provider
from app.services.llm_provider import (
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMResponseError,
    LLMTimeoutError,
    OpenAICompatibleProvider,
)


# ==============================================================================
# OpenAICompatibleProvider Tests
# ==============================================================================

class TestOpenAICompatibleProvider:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        provider = OpenAICompatibleProvider(
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )

        mock_resp = httpx.Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {"content": "This is a test response."},
                        "finish_reason": "stop",
                    }
                ]
            },
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )

        with patch.object(httpx.AsyncClient, "post", return_value=mock_resp) as mock_post:
            result = await provider.generate(
                prompt="Hello AI",
                system_prompt="Be helpful",
                json_mode=True,
            )

            assert result == "This is a test response."
            mock_post.assert_called_once()
            kwargs = mock_post.call_args[1]
            assert kwargs["headers"]["Authorization"] == "Bearer test-api-key"
            payload = kwargs["json"]
            assert payload["model"] == "gpt-4o-mini"
            assert payload["response_format"] == {"type": "json_object"}
            assert len(payload["messages"]) == 2
            assert payload["messages"][0]["role"] == "system"
            assert payload["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_error(self):
        provider = OpenAICompatibleProvider(api_key="")
        with pytest.raises(LLMProviderUnavailableError) as exc_info:
            await provider.generate("test")
        assert "LLM_API_KEY is not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_failure_401(self):
        provider = OpenAICompatibleProvider(api_key="bad-key")
        mock_resp = httpx.Response(
            status_code=401,
            json={"error": {"message": "Invalid API key"}},
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
            with pytest.raises(LLMProviderUnavailableError) as exc_info:
                await provider.generate("test")
            assert "Invalid or missing API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_model_not_found_404(self):
        provider = OpenAICompatibleProvider(api_key="valid-key", model="nonexistent-model")
        mock_resp = httpx.Response(
            status_code=404,
            text="Model not found",
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
            with pytest.raises(LLMModelNotFoundError):
                await provider.generate("test")

    @pytest.mark.asyncio
    async def test_timeout_maps_to_llm_timeout_error(self):
        provider = OpenAICompatibleProvider(api_key="valid-key")
        with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Timed out")):
            with pytest.raises(LLMTimeoutError):
                await provider.generate("test")

    def test_factory_resolves_openai_and_groq(self):
        openai_provider = get_llm_provider("openai")
        assert isinstance(openai_provider, OpenAICompatibleProvider)
        assert openai_provider.model == "gpt-4o-mini" or openai_provider.model == settings.LLM_MODEL

        groq_provider = get_llm_provider("groq")
        assert isinstance(groq_provider, OpenAICompatibleProvider)
        assert "groq.com" in groq_provider.base_url or groq_provider.base_url == settings.LLM_BASE_URL


# ==============================================================================
# OpenAIEmbeddingProvider Tests
# ==============================================================================

class TestOpenAIEmbeddingProvider:
    def test_provider_initialization_defaults(self):
        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            model_name="text-embedding-3-small",
            dimension=384,
        )
        assert provider.model_name == "text-embedding-3-small"
        assert provider.dimension == 384
        assert "embeddings" in provider._url

    def test_embed_text_empty_returns_zero_vector(self):
        provider = OpenAIEmbeddingProvider(api_key="test-key", dimension=384)
        zero_vec = provider.embed_text("")
        assert len(zero_vec) == 384
        assert all(x == 0.0 for x in zero_vec)

    def test_embed_text_success_with_normalization(self):
        provider = OpenAIEmbeddingProvider(api_key="test-key", dimension=384)

        raw_vec = [1.0, 2.0, 3.0] + [0.0] * 381
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": raw_vec, "index": 0}
            ]
        }

        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            result = provider.embed_text("sample input text")
            assert len(result) == 384
            # Verify unit normalization: sqrt(sum(x^2)) ~= 1.0
            norm = sum(x * x for x in result) ** 0.5
            assert abs(norm - 1.0) < 1e-4

    def test_embed_documents_batching(self):
        provider = OpenAIEmbeddingProvider(api_key="test-key", dimension=384)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.5] * 384, "index": 0},
                {"embedding": [0.2] * 384, "index": 1},
            ]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            docs = ["Doc 1", "Doc 2"]
            embeddings = provider.embed_documents(docs)
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 384

    def test_missing_api_key_raises_error(self):
        provider = OpenAIEmbeddingProvider(api_key="")
        with pytest.raises(EmbeddingInferenceError) as exc_info:
            provider.embed_text("test")
        assert "API key is not configured" in str(exc_info.value)

    def test_factory_resolves_openai_embedding_provider(self):
        reset_embedding_provider()
        with patch.object(settings, "EMBEDDING_PROVIDER", "openai"):
            provider = get_embedding_provider()
            assert isinstance(provider, OpenAIEmbeddingProvider)
            assert provider.dimension == 384
        reset_embedding_provider()
