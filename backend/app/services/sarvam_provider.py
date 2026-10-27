"""
Sarvam AI Provider for OpenSource Copilot.

Provides chat completions via the Sarvam AI API using the sarvam-105b model.
Grounded in repository context retrieved from pgvector / keyword fallback.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.services.llm_provider import (
    LLMProvider,
    LLMProviderUnavailableError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMResponseError,
)

logger = logging.getLogger(__name__)

# Retry configuration for transient API errors (429, 502, 503)
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds — exponential: 2s, 4s, 8s


class SarvamProvider(LLMProvider):
    """
    Hosted API provider for Sarvam AI models (e.g. sarvam-105b).
    Conforms to the Sarvam AI chat completions REST API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.name = "sarvam"
        self.api_key = api_key if api_key is not None else (settings.SARVAM_API_KEY or settings.LLM_API_KEY)
        self.base_url = (base_url or settings.SARVAM_BASE_URL or "https://api.sarvam.ai/v1").rstrip("/")
        self.model = model or settings.SARVAM_CHAT_MODEL or "sarvam-105b"
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT or 60.0

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate a grounded text or structured JSON completion from Sarvam AI.

        Args:
            prompt: User question with retrieved repository context.
            system_prompt: Grounding system prompt with safety constraints.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum tokens in response.
            json_mode: When True, requests structured JSON object response.
            history: Optional bounded conversation turns for multi-turn chat.

        Returns:
            The raw text or JSON string response from the model.
        """
        if not self.api_key:
            raise LLMProviderUnavailableError(
                "SARVAM_API_KEY is not configured for Sarvam AI provider. "
                "Please configure SARVAM_API_KEY in your backend environment."
            )

        clean_base = self.base_url.rstrip("/")
        if clean_base.endswith("/chat/completions"):
            url = clean_base
        elif clean_base.endswith("/v1"):
            url = f"{clean_base}/chat/completions"
        else:
            url = f"{clean_base}/v1/chat/completions"

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Append recent bounded conversation history if provided (up to last 6 turns)
        if history and isinstance(history, list):
            for turn in history[-6:]:
                if isinstance(turn, dict) and "role" in turn and "content" in turn:
                    role = str(turn["role"]).strip().lower()
                    if role in ("user", "assistant"):
                        messages.append({"role": role, "content": str(turn["content"])})

        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else settings.LLM_MAX_OUTPUT_TOKENS,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "api-subscription-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Retry loop with exponential backoff for transient errors (429, 502, 503)
        last_exception: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                logger.warning("Attempt %d/%d: Could not connect to Sarvam AI at %s: %s", attempt, MAX_RETRIES, url, exc)
                last_exception = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                    continue
                raise LLMProviderUnavailableError(
                    f"Sarvam AI provider at {url} is unavailable after {MAX_RETRIES} attempts."
                ) from exc
            except httpx.TimeoutException as exc:
                logger.warning("Attempt %d/%d: Sarvam AI timed out after %ss: %s", attempt, MAX_RETRIES, self.timeout, exc)
                last_exception = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                    continue
                raise LLMTimeoutError(
                    f"Sarvam AI request timed out after {self.timeout}s ({MAX_RETRIES} attempts)."
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Attempt %d/%d: Network error with Sarvam AI: %s", attempt, MAX_RETRIES, exc)
                last_exception = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                    continue
                raise LLMProviderUnavailableError(
                    f"Network error connecting to Sarvam AI at {url} after {MAX_RETRIES} attempts."
                ) from exc

            # Non-retryable status codes — fail immediately
            if response.status_code in (401, 403):
                raise LLMProviderUnavailableError(
                    "Authentication failed with Sarvam AI: Invalid or missing API key."
                )
            elif response.status_code == 404:
                raise LLMModelNotFoundError(
                    f"Model '{self.model}' was not found by Sarvam AI at {url}. Details: {response.text}"
                )

            # Retryable status codes — 429 (rate limit), 502/503 (overload)
            if response.status_code in (429, 502, 503):
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                reason = "rate limit exceeded" if response.status_code == 429 else "service overloaded"
                logger.warning(
                    "Attempt %d/%d: Sarvam AI returned HTTP %d (%s). Retrying in %.1fs...",
                    attempt, MAX_RETRIES, response.status_code, reason, delay,
                )
                last_exception = LLMProviderUnavailableError(
                    f"Sarvam AI returned HTTP {response.status_code}: {response.text[:200]}"
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(delay)
                    continue
                if response.status_code == 429:
                    raise LLMProviderUnavailableError(
                        f"Sarvam AI rate limit exceeded (HTTP 429) after {MAX_RETRIES} retries. "
                        f"Please try again in a few moments."
                    )
                raise LLMProviderUnavailableError(
                    f"Sarvam AI API is overloaded (HTTP {response.status_code}) after {MAX_RETRIES} retries. "
                    f"Please try again in a few moments."
                )

            # Other non-200 errors — fail immediately
            if response.status_code != 200:
                raise LLMResponseError(
                    f"Sarvam AI API returned HTTP {response.status_code}: {response.text}"
                )

            # Successful response — parse and return
            try:
                data = response.json()
                choices = data.get("choices")
                if not choices or not isinstance(choices, list):
                    # Treat missing choices as a transient error — retry
                    logger.warning(
                        "Attempt %d/%d: Sarvam AI response missing 'choices'. Body: %s",
                        attempt, MAX_RETRIES, response.text[:300],
                    )
                    last_exception = LLMResponseError("Sarvam AI response did not contain 'choices' array.")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                        continue
                    raise last_exception

                content = choices[0].get("message", {}).get("content")

                # Handle empty content gracefully — the model may return empty content
                # under overload conditions. Return a fallback instead of crashing.
                if content is None or (isinstance(content, str) and not content.strip()):
                    logger.warning(
                        "Attempt %d/%d: Sarvam AI returned empty content in response.",
                        attempt, MAX_RETRIES,
                    )
                    last_exception = LLMResponseError("Sarvam AI returned empty content.")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                        continue
                    # After all retries, return a graceful fallback message
                    return (
                        "I apologize, but I'm experiencing temporary difficulties generating a response. "
                        "The AI service may be under heavy load. Please try again in a moment."
                    )

                return content
            except Exception as exc:
                if isinstance(exc, (LLMResponseError, LLMProviderUnavailableError)):
                    raise
                raise LLMResponseError(f"Failed to decode Sarvam AI JSON response: {exc}") from exc

        # Should not reach here, but safety fallback
        raise LLMProviderUnavailableError(
            f"Sarvam AI failed after {MAX_RETRIES} attempts."
        )

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        from app.embeddings.factory import get_embedding_provider
        provider = get_embedding_provider()
        return provider.embed_documents(texts)

