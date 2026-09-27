import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.llm_provider import (
    OllamaProvider,
    LLMProviderUnavailableError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMResponseError,
)
from app.services.llm_factory import get_llm_provider, UnsupportedLLMProviderError


@pytest.mark.asyncio
async def test_ollama_generate_success():
    """Verify OllamaProvider parses successful HTTP 200 response."""
    provider = OllamaProvider(base_url="http://fake-ollama:11434", model="llama3.2:3b")

    mock_response = httpx.Response(
        status_code=200,
        json={"response": '{"summary": "Test repo summary"}'},
        request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_response) as mock_post:
        result = await provider.generate(
            prompt="Analyze this code",
            system_prompt="You are an expert",
            json_mode=True,
        )

        assert result == '{"summary": "Test repo summary"}'
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "llama3.2:3b"
        assert call_kwargs["json"]["format"] == "json"
        assert call_kwargs["json"]["system"] == "You are an expert"


@pytest.mark.asyncio
async def test_ollama_connect_error():
    """Verify ConnectError maps to LLMProviderUnavailableError."""
    provider = OllamaProvider(base_url="http://fake-ollama:11434", model="llama3.2:3b")

    with patch.object(
        httpx.AsyncClient,
        "post",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        with pytest.raises(LLMProviderUnavailableError) as exc_info:
            await provider.generate("hello")

        assert "Make sure Ollama is running" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_timeout():
    """Verify TimeoutException maps to LLMTimeoutError."""
    provider = OllamaProvider(base_url="http://fake-ollama:11434", model="llama3.2:3b", timeout=5.0)

    with patch.object(
        httpx.AsyncClient,
        "post",
        side_effect=httpx.ReadTimeout("Timeout"),
    ):
        with pytest.raises(LLMTimeoutError) as exc_info:
            await provider.generate("hello")

        assert "timed out after 5.0s" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_model_not_found():
    """Verify 404 response maps to LLMModelNotFoundError."""
    provider = OllamaProvider(base_url="http://fake-ollama:11434", model="nonexistent-model")

    mock_response = httpx.Response(
        status_code=404,
        text="model 'nonexistent-model' not found, try pulling it first",
        request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_response):
        with pytest.raises(LLMModelNotFoundError) as exc_info:
            await provider.generate("hello")

        assert "ollama pull nonexistent-model" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_http_500():
    """Verify 500 response maps to LLMResponseError."""
    provider = OllamaProvider(base_url="http://fake-ollama:11434", model="llama3.2:3b")

    mock_response = httpx.Response(
        status_code=500,
        text="Internal server error in Ollama",
        request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_response):
        with pytest.raises(LLMResponseError) as exc_info:
            await provider.generate("hello")

        assert "HTTP 500" in str(exc_info.value)


def test_llm_factory():
    """Verify factory returns appropriate provider or raises for unsupported."""
    ollama = get_llm_provider("ollama")
    assert isinstance(ollama, OllamaProvider)

    with pytest.raises(UnsupportedLLMProviderError):
        get_llm_provider("unknown_fancy_ai")


def test_ollama_provider_default_model_is_llama32_3b():
    """Verify project defaults resolve OLLAMA_MODEL to llama3.2:3b and does not fall back to llama3."""
    assert settings.OLLAMA_MODEL == "llama3.2:3b"
    provider = OllamaProvider()
    assert provider.model == "llama3.2:3b"


def test_llm_factory_passes_configured_model_to_ollama_provider():
    """Verify factory passes dynamically configured OLLAMA_MODEL from settings to OllamaProvider."""
    with patch.object(settings, "OLLAMA_MODEL", "custom-configured-model:latest"):
        provider = get_llm_provider("ollama")
        assert isinstance(provider, OllamaProvider)
        assert provider.model == "custom-configured-model:latest"


@pytest.mark.asyncio
async def test_ollama_provider_passes_configured_model_to_api_call():
    """Verify that the model configured in settings is actually sent in the POST request to Ollama."""
    with patch.object(settings, "OLLAMA_MODEL", "llama3.2:3b"):
        provider = get_llm_provider("ollama")
        mock_response = httpx.Response(
            status_code=200,
            json={"response": "ok"},
            request=httpx.Request("POST", "http://localhost:11434/api/generate"),
        )
        with patch.object(httpx.AsyncClient, "post", return_value=mock_response) as mock_post:
            await provider.generate("test prompt")
            mock_post.assert_called_once()
            assert mock_post.call_args[1]["json"]["model"] == "llama3.2:3b"

