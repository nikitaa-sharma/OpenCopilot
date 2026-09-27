from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Forward reference for factory import to avoid circular dependency
def _lazy_get_llm_provider():
    from app.services.llm_factory import get_llm_provider
    return get_llm_provider

# For backward compatibility
def get_llm_provider(*args, **kwargs):
    from app.services.llm_factory import get_llm_provider as _factory
    return _factory(*args, **kwargs)



# ==============================================================================
# Domain Exceptions for LLM Provider
# ==============================================================================

class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when the LLM service cannot be reached (e.g. Ollama offline)."""
    pass


class LLMModelNotFoundError(LLMProviderError):
    """Raised when the requested model is not installed or pulled."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when the model generation times out."""
    pass


class LLMResponseError(LLMProviderError):
    """Raised when the LLM returns an unexpected or malformed response."""
    pass


# ==============================================================================
# LLM Provider Abstract Interface
# ==============================================================================

class LLMProvider(ABC):
    """
    Abstract interface for replaceable AI / Large Language Model providers.
    Supports local open-source models (e.g., Ollama) or hosted APIs (OpenAI, Anthropic, Groq).
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Generate text completion from a prompt.

        Args:
            prompt: User prompt / task context.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum output tokens to generate.
            json_mode: When True, enforces structured JSON output.

        Returns:
            Generated response string.
        """
        pass

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Backward-compatible text generation wrapper."""
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for input texts (reserved for future RAG phase)."""
        pass


# ==============================================================================
# Ollama Provider (Local Open Source)
# ==============================================================================

class OllamaProvider(LLMProvider):
    """
    Local open-source model provider communicating via Ollama REST API.
    Does not require paid API keys.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "num_predict": max_tokens if max_tokens is not None else settings.LLM_MAX_OUTPUT_TOKENS,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.warning(f"Could not connect to Ollama at {self.base_url}: {exc}")
            raise LLMProviderUnavailableError(
                f"AI provider is unavailable. Make sure Ollama is running at {self.base_url} "
                f"and '{self.model}' is installed."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.warning(f"Ollama generation timed out after {self.timeout}s: {exc}")
            raise LLMTimeoutError(
                f"AI provider request timed out after {self.timeout}s. The model may still be loading."
            ) from exc
        except httpx.RequestError as exc:
            logger.error(f"Network error communicating with Ollama: {exc}")
            raise LLMProviderUnavailableError(
                f"Network error connecting to AI provider at {self.base_url}."
            ) from exc

        if response.status_code == 404:
            err_msg = response.text
            raise LLMModelNotFoundError(
                f"Model '{self.model}' was not found in Ollama. "
                f"Run `ollama pull {self.model}` in your terminal to install it. Details: {err_msg}"
            )
        elif response.status_code != 200:
            raise LLMResponseError(
                f"Ollama API returned HTTP {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
            generated_text = data.get("response")
            if generated_text is None:
                raise LLMResponseError("Ollama response did not contain 'response' field.")
            return generated_text
        except Exception as exc:
            if isinstance(exc, LLMResponseError):
                raise
            raise LLMResponseError(f"Failed to decode Ollama JSON response: {exc}") from exc

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError("Embeddings generation will be connected in RAG phase.")


# ==============================================================================
# Hosted OpenAI-Compatible Provider (OpenAI, Groq, Together, DeepSeek)
# ==============================================================================

class OpenAICompatibleProvider(LLMProvider):
    """
    Hosted API provider conforming to standard OpenAI Chat Completions API format.
    Compatible with OpenAI (e.g. gpt-4o, gpt-4o-mini), Groq, Together, DeepSeek, etc.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        if not self.api_key:
            raise LLMProviderUnavailableError(
                "LLM_API_KEY is not configured for OpenAI-compatible provider. "
                "Set LLM_API_KEY in your environment."
            )

        clean_base = self.base_url.rstrip("/")
        if clean_base.endswith("/chat/completions"):
            url = clean_base
        elif clean_base.endswith("/v1"):
            url = f"{clean_base}/chat/completions"
        else:
            url = f"{clean_base}/v1/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else settings.LLM_MAX_OUTPUT_TOKENS,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.warning(f"Could not connect to LLM provider at {url}: {exc}")
            raise LLMProviderUnavailableError(
                f"AI provider at {url} is unavailable or unreachable."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.warning(f"LLM generation timed out after {self.timeout}s: {exc}")
            raise LLMTimeoutError(
                f"AI provider request timed out after {self.timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            logger.error(f"Network error communicating with LLM provider: {exc}")
            raise LLMProviderUnavailableError(
                f"Network error connecting to AI provider at {url}."
            ) from exc

        if response.status_code == 401:
            raise LLMProviderUnavailableError(
                "Authentication failed with AI provider: Invalid or missing API key."
            )
        elif response.status_code == 404:
            raise LLMModelNotFoundError(
                f"Model '{self.model}' was not found by provider at {url}. Details: {response.text}"
            )
        elif response.status_code != 200:
            raise LLMResponseError(
                f"AI provider API returned HTTP {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise LLMResponseError("LLM response did not contain 'choices'.")
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise LLMResponseError("LLM response choice did not contain 'content'.")
            return content
        except Exception as exc:
            if isinstance(exc, LLMResponseError):
                raise
            raise LLMResponseError(f"Failed to decode LLM JSON response: {exc}") from exc

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        from app.embeddings.factory import get_embedding_provider
        provider = get_embedding_provider()
        return provider.embed_documents(texts)
