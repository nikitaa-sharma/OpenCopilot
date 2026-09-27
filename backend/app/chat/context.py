"""
Chat context retrieval service for OpenSource Copilot (Phase 9).

Integrates directly with the existing RAG pipeline (Phase 7 & Phase 8):
1. Runs semantic vector retrieval via pgvector.
2. Falls back cleanly to deterministic keyword retrieval when vector retrieval is unavailable.
3. Formats retrieved chunks into bounded prompt context.
4. Prepares verified ChatSource models derived strictly from retrieved chunks.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatQuestion, ChatSource
from app.rag.models import RetrievedChunk
from app.rag.service import RepositoryRAGService, repository_rag_service

logger = logging.getLogger(__name__)


@dataclass
class ChatContextData:
    """Bounded repository context and supporting evidence for LLM prompt."""
    context_text: str
    sources: List[ChatSource] = field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = field(default_factory=list)
    retrieval_mode: str = "vector"
    chunks_count: int = 0


class RepositoryChatContextService:
    """
    Coordinates context retrieval for repository chat using the existing RAG infrastructure.
    Does NOT implement an independent retrieval system.
    """

    def __init__(self, rag_service: Optional[RepositoryRAGService] = None):
        self.rag_service = rag_service or repository_rag_service

    async def get_context_for_question(
        self,
        question: ChatQuestion,
        session: Optional[AsyncSession] = None,
    ) -> ChatContextData:
        """
        Retrieves grounded repository context for a user question.

        Flow:
        1. Query RAG service with repository URL and question text.
        2. RAG service tries vector retrieval; falls back to keyword retrieval if needed.
        3. Format bounded context markdown string.
        4. Convert retrieved chunks to domain ChatSource instances.
        """
        retrieval = await self.rag_service.retrieve_for_query(
            url=question.repository_url,
            query=question.question,
            branch=question.branch,
            top_k=question.top_k,
            session=session,
        )

        context_text = self.rag_service.build_context(retrieval.results)

        sources: List[ChatSource] = []
        for rc in retrieval.results:
            sources.append(
                ChatSource(
                    path=rc.chunk.file_path,
                    chunk_id=rc.chunk.chunk_id,
                    start_line=rc.chunk.start_line,
                    end_line=rc.chunk.end_line,
                    category=rc.chunk.category,
                    score=rc.score,
                    retrieval_reason=rc.retrieval_reason,
                )
            )

        return ChatContextData(
            context_text=context_text,
            sources=sources,
            retrieved_chunks=retrieval.results,
            retrieval_mode=retrieval.retrieval_mode,
            chunks_count=len(retrieval.results),
        )


repository_chat_context_service = RepositoryChatContextService()
