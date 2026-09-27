"""
Repository indexing service for local vector embeddings.

Converts repository documents into semantic vector chunks:
Documents → Structure-Aware Chunks → SHA-256 Hash → Batch Embedding → PostgreSQL (pgvector).
Reuses embeddings for unchanged chunks to minimize computation.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.models.entities import Repository, RepositoryChunk as RepositoryChunkModel
from app.rag.chunker import RepositoryChunker
from app.rag.document_loader import DocumentLoader
from app.rag.models import RepositoryChunk, RepositoryDocument

logger = logging.getLogger(__name__)


@dataclass
class RAGIndexResult:
    """Structured statistics returned after a repository indexing operation."""

    repository: str
    documents_processed: int
    chunks_created: int
    chunks_embedded: int
    chunks_reused: int
    chunks_updated: int
    chunks_skipped: int
    embedding_dimension: int
    elapsed_time_seconds: float


def compute_content_hash(content: str) -> str:
    """Computes a deterministic SHA-256 hex digest of chunk text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class RepositoryIndexer:
    """
    Indexes repository chunks into PostgreSQL using pgvector embeddings.

    - Reuses embeddings when content has not changed (content_hash match).
    - Batches embedding computation according to EMBEDDING_BATCH_SIZE.
    - Preserves file paths, line ranges, languages, and metadata.
    """

    def __init__(
        self,
        document_loader: Optional[DocumentLoader] = None,
        chunker: Optional[RepositoryChunker] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.document_loader = document_loader or DocumentLoader()
        self.chunker = chunker or RepositoryChunker()
        self._embedding_provider = embedding_provider

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    async def _get_existing_chunks(
        self, session: AsyncSession, repo_identifier: str
    ) -> Dict[Tuple[str, int], RepositoryChunkModel]:
        """
        Fetches existing indexed chunks for a repository mapped by (file_path, chunk_index).
        """
        stmt = select(RepositoryChunkModel).where(
            RepositoryChunkModel.repository_identifier == repo_identifier
        )
        result = await session.execute(stmt)
        existing = {}
        for row in result.scalars().all():
            existing[(row.file_path, row.chunk_index)] = row
        return existing

    async def _get_or_create_repo_record(
        self, session: AsyncSession, repo_identifier: str, url: str, branch: Optional[str]
    ) -> Optional[int]:
        """
        Finds or creates a parent Repository record in PostgreSQL if possible.
        """
        try:
            parts = repo_identifier.split("/", 1)
            owner = parts[0]
            name = parts[1] if len(parts) > 1 else repo_identifier
            stmt = select(Repository).where(Repository.full_name == repo_identifier)
            res = await session.execute(stmt)
            repo = res.scalar_one_or_none()
            if repo is None:
                repo = Repository(
                    owner=owner,
                    name=name,
                    full_name=repo_identifier,
                    url=url,
                    default_branch=branch or "main",
                )
                session.add(repo)
                await session.flush()
            return repo.id
        except Exception as exc:
            logger.debug(f"Could not link parent Repository record: {exc}")
            return None

    async def index_repository(
        self,
        url: str,
        branch: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> RAGIndexResult:
        """
        Full repository indexing workflow:
        1. Load repository documents
        2. Split into structure-aware chunks
        3. Check existing chunks in PostgreSQL
        4. Re-use matching embeddings via content hash
        5. Embed new/changed chunks in batches
        6. Persist to PostgreSQL + pgvector
        """
        start_time = time.perf_counter()

        # Step 1: Load documents
        documents, load_stats = await self.document_loader.load_documents(url=url, branch=branch)
        repo_identifier = documents[0].repository if documents else url

        # Step 2: Split documents into chunks
        chunks: List[RepositoryChunk] = self.chunker.chunk_documents(documents)

        # Ensure database tables and pgvector extension are initialized
        await init_db()

        # Execute DB operations in session
        if session is not None:
            return await self._index_with_session(
                session, url, branch, repo_identifier, documents, chunks, start_time
            )
        else:
            async with AsyncSessionLocal() as db_session:
                try:
                    result = await self._index_with_session(
                        db_session, url, branch, repo_identifier, documents, chunks, start_time
                    )
                    await db_session.commit()
                    return result
                except Exception:
                    await db_session.rollback()
                    raise

    async def _index_with_session(
        self,
        session: AsyncSession,
        url: str,
        branch: Optional[str],
        repo_identifier: str,
        documents: List[RepositoryDocument],
        chunks: List[RepositoryChunk],
        start_time: float,
    ) -> RAGIndexResult:
        repo_id = await self._get_or_create_repo_record(session, repo_identifier, url, branch)
        existing_chunks = await self._get_existing_chunks(session, repo_identifier)

        chunks_reused = 0
        chunks_embedded = 0
        chunks_updated = 0
        chunks_skipped = 0

        # Identify chunks to embed vs reuse
        to_embed_chunks: List[Tuple[RepositoryChunk, str, Optional[RepositoryChunkModel]]] = []
        kept_keys = set()

        for chunk in chunks:
            key = (chunk.file_path, chunk.chunk_index)
            kept_keys.add(key)
            c_hash = compute_content_hash(chunk.content)
            existing = existing_chunks.get(key)

            if existing is not None and existing.content_hash == c_hash and existing.embedding is not None:
                # Content is identical and already has an embedding — reuse
                chunks_reused += 1
            else:
                # New chunk or modified content — needs embedding
                to_embed_chunks.append((chunk, c_hash, existing))

        # Batch embed only new / modified chunks
        if to_embed_chunks:
            texts_to_embed = [c[0].content for c in to_embed_chunks]
            provider = self.embedding_provider
            embeddings = provider.embed_documents(texts_to_embed)

            for (chunk, c_hash, existing), emb in zip(to_embed_chunks, embeddings):
                if existing is not None:
                    # Update existing chunk
                    existing.content = chunk.content
                    existing.content_hash = c_hash
                    existing.start_line = chunk.start_line
                    existing.end_line = chunk.end_line
                    existing.language = chunk.language
                    existing.category = chunk.category
                    existing.chunk_metadata = chunk.metadata
                    existing.embedding = emb
                    chunks_updated += 1
                else:
                    # Insert new chunk
                    new_model = RepositoryChunkModel(
                        repository_id=repo_id,
                        repository_identifier=repo_identifier,
                        file_path=chunk.file_path,
                        language=chunk.language,
                        category=chunk.category,
                        chunk_index=chunk.chunk_index,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        content_hash=c_hash,
                        chunk_metadata=chunk.metadata,
                        embedding=emb,
                    )
                    session.add(new_model)
                chunks_embedded += 1

        # Delete any old chunks that no longer exist in the repository
        stale_keys = set(existing_chunks.keys()) - kept_keys
        for file_path, chunk_idx in stale_keys:
            stale_chunk = existing_chunks[(file_path, chunk_idx)]
            await session.delete(stale_chunk)

        elapsed = round(time.perf_counter() - start_time, 3)

        logger.info(
            f"Indexed repository '{repo_identifier}': docs={len(documents)}, "
            f"chunks_created={len(chunks)}, embedded={chunks_embedded}, "
            f"reused={chunks_reused}, updated={chunks_updated} in {elapsed}s"
        )

        return RAGIndexResult(
            repository=repo_identifier,
            documents_processed=len(documents),
            chunks_created=len(chunks),
            chunks_embedded=chunks_embedded,
            chunks_reused=chunks_reused,
            chunks_updated=chunks_updated,
            chunks_skipped=chunks_skipped,
            embedding_dimension=self.embedding_provider.dimension,
            elapsed_time_seconds=elapsed,
        )
