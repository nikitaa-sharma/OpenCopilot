"""
Context retrieval service for AI Contribution Guide (Phase 11).

Reuses the existing RAG pipeline (Phases 7 & 8) to retrieve repository context
for contribution guide generation. Follows the same pattern as
``app.chat.context.RepositoryChatContextService``.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.contribution.models import ContributionGuideEvidence
from app.rag.models import RetrievedChunk
from app.rag.service import RepositoryRAGService, repository_rag_service

logger = logging.getLogger(__name__)


@dataclass
class ContributionContextData:
    """Bounded repository context and supporting evidence for the contribution guide LLM prompt."""

    context_text: str
    evidence: List[ContributionGuideEvidence] = field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = field(default_factory=list)
    retrieval_mode: str = "vector"
    chunks_count: int = 0


class ContributionGuideContextService:
    """
    Coordinates context retrieval for the AI Contribution Guide using the existing
    RAG infrastructure. Does NOT implement an independent retrieval system.
    """

    def __init__(self, rag_service: Optional[RepositoryRAGService] = None):
        self.rag_service = rag_service or repository_rag_service

    async def get_context_for_issue(
        self,
        owner: str,
        repo: str,
        issue_title: str,
        issue_body: Optional[str] = None,
        branch: Optional[str] = None,
        top_k: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> ContributionContextData:
        """
        Retrieves grounded repository context relevant to a GitHub issue.

        Builds a composite query from the issue title and body, then routes
        through the existing RAG pipeline (vector → keyword fallback).

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_title: GitHub issue title used as primary query text.
            issue_body: Optional issue body for expanded query context.
            branch: Optional branch or commit ref.
            top_k: Number of chunks to retrieve.
            session: Optional async DB session for vector retrieval.

        Returns:
            ContributionContextData with bounded context and evidence list.
        """
        # Build composite query from issue metadata
        query_parts = [issue_title]
        if issue_body and issue_body.strip():
            # Use first ~500 chars of body to augment query without exceeding limits
            body_excerpt = issue_body.strip()[:500]
            query_parts.append(body_excerpt)
        composite_query = " ".join(query_parts)

        repository_url = f"https://github.com/{owner}/{repo}"

        retrieval = await self.rag_service.retrieve_for_query(
            url=repository_url,
            query=composite_query,
            branch=branch,
            top_k=top_k,
            session=session,
        )

        context_text = self.rag_service.build_context(retrieval.results)

        evidence: List[ContributionGuideEvidence] = []
        for rc in retrieval.results:
            evidence.append(
                ContributionGuideEvidence(
                    path=rc.chunk.file_path,
                    chunk_id=rc.chunk.chunk_id,
                    start_line=rc.chunk.start_line,
                    end_line=rc.chunk.end_line,
                    category=rc.chunk.category,
                    score=rc.score,
                    reason=rc.retrieval_reason,
                )
            )

        return ContributionContextData(
            context_text=context_text,
            evidence=evidence,
            retrieved_chunks=retrieval.results,
            retrieval_mode=retrieval.retrieval_mode,
            chunks_count=len(retrieval.results),
        )


contribution_guide_context_service = ContributionGuideContextService()
