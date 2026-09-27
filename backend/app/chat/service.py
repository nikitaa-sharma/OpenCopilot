"""
Repository Chat Service for OpenSource Copilot (Phase 9).

Orchestrates:
1. Retrieval of repository chunks via pgvector / keyword fallback.
2. Context bounding and prompt preparation.
3. Replaceable LLM invocation (Ollama / local model by default).
4. Safe structured JSON output parsing with fallback normalization.
5. Strict source validation: eliminates any hallucinated file paths not present
   in actual retrieved chunks.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.context import (
    ChatContextData,
    RepositoryChatContextService,
    repository_chat_context_service,
)
from app.chat.models import ChatAnswer, ChatQuestion, ChatSource
from app.core.config import settings
from app.prompts.repository_chat import (
    REPOSITORY_CHAT_SYSTEM_PROMPT,
    build_repository_chat_user_prompt,
)
from app.services.llm_factory import get_llm_provider
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class RepositoryChatService:
    """
    Main domain service for repository-aware AI chat.
    Decoupled from specific LLM providers and database models.
    """

    def __init__(
        self,
        context_service: Optional[RepositoryChatContextService] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.context_service = context_service or repository_chat_context_service
        self._llm_provider = llm_provider

    @property
    def llm_provider(self) -> LLMProvider:
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    async def chat(
        self,
        question: ChatQuestion,
        session: Optional[AsyncSession] = None,
    ) -> ChatAnswer:
        """
        Process a repository chat question end-to-end.
        """
        # Validate question
        cleaned_question = question.question.strip()
        if not cleaned_question:
            raise ValueError("Question cannot be empty.")

        # Step 1: Retrieve context using existing RAG pipeline
        context_data: ChatContextData = await self.context_service.get_context_for_question(
            question=question,
            session=session,
        )

        # Step 2: Handle no-context scenario safely without hallucination
        if context_data.chunks_count == 0 or not context_data.context_text.strip():
            logger.info(
                f"No context found for repository chat: {question.repository_identifier} | "
                f"query='{cleaned_question[:60]}'"
            )
            return ChatAnswer(
                answer=(
                    f"No relevant repository context could be found for your question in "
                    f"'{question.repository_identifier}'. Please ensure the repository is indexed "
                    f"or try rephrasing your search query."
                ),
                sources=[],
                retrieval_mode="none",
                retrieved_chunks_count=0,
                uncertainties=[
                    "Repository context for this query was not found in the indexed files."
                ],
            )

        # Step 3: Build grounded prompts
        user_prompt = build_repository_chat_user_prompt(
            repository=question.repository_identifier,
            question=cleaned_question,
            context=context_data.context_text,
            branch=question.branch,
        )

        # Step 4: Call LLM provider with JSON mode
        logger.info(
            f"Invoking LLM for repository chat: {question.repository_identifier} | "
            f"chunks={context_data.chunks_count} | mode={context_data.retrieval_mode}"
        )
        raw_output = await self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=REPOSITORY_CHAT_SYSTEM_PROMPT,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            json_mode=True,
        )

        # Step 5: Safe structured parsing
        parsed = self._safe_parse_response(raw_output)

        # Step 6: Validate sources against actual retrieved chunks
        validated_sources = self._validate_sources(
            evidence=parsed.get("evidence", []),
            retrieved_sources=context_data.sources,
        )

        answer_text = parsed.get("answer", "").strip()
        if not answer_text:
            answer_text = raw_output.strip()

        uncertainties = parsed.get("uncertainties", [])
        if not isinstance(uncertainties, list):
            uncertainties = [str(uncertainties)] if uncertainties else []

        return ChatAnswer(
            answer=answer_text,
            sources=validated_sources,
            retrieval_mode=context_data.retrieval_mode,
            retrieved_chunks_count=context_data.chunks_count,
            uncertainties=[str(u) for u in uncertainties if u],
        )

    def _safe_parse_response(self, text: str) -> Dict[str, Any]:
        """
        Safely extracts and parses JSON output from the LLM.
        Applies fallback heuristics if model enclosed JSON in markdown or added commentary.
        """
        cleaned = text.strip()

        # Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Attempt direct JSON parse
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # Attempt regex extraction of JSON object
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        # Safe fallback: treat entire response as the answer text
        logger.warning("LLM output could not be parsed as JSON. Falling back to plain text answer.")
        return {
            "answer": text.strip(),
            "evidence": [],
            "uncertainties": ["Structured JSON parsing failed; displayed raw response."],
        }

    def _validate_sources(
        self,
        evidence: List[Any],
        retrieved_sources: List[ChatSource],
    ) -> List[ChatSource]:
        """
        Validates model citations against actual retrieved repository chunks.

        Rules:
        1. Never trust the LLM to invent source paths.
        2. Only files present in `retrieved_sources` can be exposed as verified evidence.
        3. If evidence lists a valid retrieved file, attach metadata from the retrieved chunk.
        4. If evidence is empty or invalid, fallback to presenting the top retrieved sources.
        """
        retrieved_by_path: Dict[str, List[ChatSource]] = {}
        for s in retrieved_sources:
            retrieved_by_path.setdefault(s.path, []).append(s)

        validated: List[ChatSource] = []
        seen_paths: Set[str] = set()

        if isinstance(evidence, list):
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path", "")).strip()
                if not path:
                    continue

                # Check if path or normalized path was retrieved
                matching_chunks = retrieved_by_path.get(path)
                if not matching_chunks:
                    # Also try matching filename suffix (e.g. app.py vs src/flask/app.py)
                    matching_chunks = [
                        src for p, srcs in retrieved_by_path.items()
                        if p.endswith(path) or path.endswith(p)
                        for src in srcs
                    ]

                if matching_chunks and path not in seen_paths:
                    seen_paths.add(path)
                    primary_chunk = matching_chunks[0]

                    # Use verified start/end lines from chunk, or model if valid int within bounds
                    start_line = primary_chunk.start_line
                    end_line = primary_chunk.end_line
                    if item.get("start_line") is not None and isinstance(item.get("start_line"), int):
                        start_line = item.get("start_line")
                    if item.get("end_line") is not None and isinstance(item.get("end_line"), int):
                        end_line = item.get("end_line")

                    reason = str(item.get("reason", "")).strip() or primary_chunk.retrieval_reason

                    validated.append(
                        ChatSource(
                            path=primary_chunk.path,
                            chunk_id=primary_chunk.chunk_id,
                            start_line=start_line,
                            end_line=end_line,
                            category=primary_chunk.category,
                            score=primary_chunk.score,
                            retrieval_reason=reason,
                        )
                    )

        # If model provided no valid evidence citations, include the actual retrieved sources
        if not validated:
            for s in retrieved_sources[: settings.RAG_TOP_K]:
                if s.path not in seen_paths:
                    seen_paths.add(s.path)
                    validated.append(s)

        return validated


repository_chat_service = RepositoryChatService()
