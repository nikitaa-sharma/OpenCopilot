from typing import Optional
import logging
from app.core.config import settings
from app.services.llm_provider import (
    LLMProvider,
    LLMProviderError,
    OllamaProvider,
    OpenAICompatibleProvider,
)

logger = logging.getLogger(__name__)


class UnsupportedLLMProviderError(LLMProviderError):
    """Raised when an unrecognized LLM provider is requested."""
    pass


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function to resolve and instantiate the configured LLM provider.

    Args:
        provider_name: Optional override for provider name. Defaults to settings.LLM_PROVIDER.

    Returns:
        LLMProvider instance.

    Raises:
        UnsupportedLLMProviderError: If the specified provider is unknown.
    """
    resolved_name = (provider_name or settings.LLM_PROVIDER).lower().strip()

    if resolved_name == "ollama":
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
    elif resolved_name in ("openai", "hosted", "api"):
        base_url = settings.LLM_BASE_URL
        if not base_url or base_url == "http://localhost:11434":
            base_url = "https://api.openai.com/v1"
        model = settings.LLM_MODEL
        if model == "llama3.2:3b":
            model = "gpt-4o-mini"
        return OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=base_url,
            model=model,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
    elif resolved_name == "groq":
        base_url = settings.LLM_BASE_URL
        if not base_url or base_url == "http://localhost:11434":
            base_url = "https://api.groq.com/openai/v1"
        model = settings.LLM_MODEL
        if model == "llama3.2:3b":
            model = "llama-3.3-70b-versatile"
        return OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=base_url,
            model=model,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
    else:
        raise UnsupportedLLMProviderError(
            f"Unsupported LLM provider '{resolved_name}'. "
            f"Supported providers: 'ollama', 'openai', 'groq'."
        )
