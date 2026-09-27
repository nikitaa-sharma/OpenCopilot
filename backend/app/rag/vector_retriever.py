"""
Semantic vector retriever using PostgreSQL + pgvector.

Generates local query embeddings and performs cosine similarity search
against indexed RepositoryChunk embeddings in PostgreSQL.
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.models.entities import RepositoryChunk as RepositoryChunkModel
from app.rag.models import RepositoryChunk, RetrievedChunk

logger = logging.getLogger(__name__)


class VectorRetriever:
    """
    Retrieves relevant repository chunks via pgvector cosine similarity.

    - Embeds the search query using the configured local embedding model (with query prefix).
    - Queries PostgreSQL pgvector using cosine distance (`<=>` operator).
    - Converts distance to similarity score: similarity = 1.0 - cosine_distance.
    - Returns structured RetrievedChunk models directly compatible with RAGContextBuilder.
    """

    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        self._embedding_provider = embedding_provider

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    async def retrieve(
        self,
        query: str,
        repository_identifier: str,
        top_k: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[RetrievedChunk]:
        """
        Executes semantic vector search for a query across an indexed repository.

        Args:
            query: Natural language or code question.
            repository_identifier: "owner/repo" format.
            top_k: Max chunks to return (default: settings.RAG_TOP_K).
            session: Optional existing database session.

        Returns:
            List of RetrievedChunk sorted by cosine similarity DESC.
        """
        if not query or not query.strip():
            logger.debug("Empty query passed to VectorRetriever.")
            return []

        k = top_k or settings.RAG_TOP_K

        # 1. Generate query embedding (with BGE instruction prefix if applicable)
        provider = self.embedding_provider
        query_vector = provider.embed_text(query, is_query=True)

        # 2. Query pgvector
        if session is not None:
            return await self._search_with_session(session, query, query_vector, repository_identifier, k)
        else:
            async with AsyncSessionLocal() as db_session:
                return await self._search_with_session(db_session, query, query_vector, repository_identifier, k)

    async def _search_with_session(
        self,
        session: AsyncSession,
        query: str,
        query_vector: List[float],
        repository_identifier: str,
        top_k: int,
    ) -> List[RetrievedChunk]:
        """Executes similarity query in given session."""
        # Cosine distance in pgvector: embedding.cosine_distance(query_vector)
        # Cosine similarity = 1.0 - cosine_distance
        distance_expr = RepositoryChunkModel.embedding.cosine_distance(query_vector)

        stmt = (
            select(RepositoryChunkModel, distance_expr.label("distance"))
            .where(
                RepositoryChunkModel.repository_identifier == repository_identifier,
                RepositoryChunkModel.embedding.is_not(None),
            )
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        result = await session.execute(stmt)
        rows = result.all()

        retrieved: List[RetrievedChunk] = []
        for chunk_model, distance in rows:
            # Convert cosine distance to cosine similarity (1.0 = identical, 0.0 = orthogonal)
            dist_val = float(distance) if distance is not None else 1.0
            similarity_score = round(1.0 - dist_val, 4)

            domain_chunk = RepositoryChunk(
                chunk_id=f"{chunk_model.repository_identifier}:{chunk_model.file_path}:{chunk_model.chunk_index}",
                repository=chunk_model.repository_identifier,
                file_path=chunk_model.file_path,
                language=chunk_model.language,
                category=chunk_model.category,
                chunk_index=chunk_model.chunk_index,
                start_line=chunk_model.start_line,
                end_line=chunk_model.end_line,
                content=chunk_model.content,
                metadata=chunk_model.chunk_metadata or {},
            )

            reason = f"Vector semantic similarity: {similarity_score:.4f} (cosine match)."
            retrieved.append(
                RetrievedChunk(
                    chunk=domain_chunk,
                    score=similarity_score,
                    matched_terms=[],
                    retrieval_reason=reason,
                )
            )

        logger.debug(
            f"VectorRetriever returned {len(retrieved)} chunks for repo '{repository_identifier}' (top_k={top_k})"
        )
        return retrieved
