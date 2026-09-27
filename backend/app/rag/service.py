"""
RAG orchestration service for OpenSource Copilot.

Composes DocumentLoader → Chunker → Retriever (Keyword / Vector) → ContextBuilder.
Supports local embeddings via sentence-transformers and PostgreSQL pgvector,
with seamless fallback to deterministic keyword retrieval.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.chunker import RepositoryChunker
from app.rag.context import RAGContextBuilder
from app.rag.document_loader import DocumentLoader
from app.rag.indexer import RAGIndexResult, RepositoryIndexer
from app.rag.models import (
    RAGStatistics,
    RepositoryChunk,
    RepositoryDocument,
    RetrievedChunk,
)
from app.rag.retriever import KeywordRetriever
from app.rag.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)


@dataclass
class RAGRetrievalResult:
    """Complete result from a retrieval operation."""
    repository: str
    query: str
    results: List[RetrievedChunk]
    statistics: RAGStatistics
    retrieval_mode: str = "keyword"


@dataclass
class RAGContextResult:
    """Complete result from a context-building operation."""
    repository: str
    query: str
    context: str
    retrieved_chunks: List[RetrievedChunk]
    statistics: RAGStatistics
    retrieval_mode: str = "keyword"


class RepositoryRAGService:
    """
    Orchestration service for OpenSource Copilot RAG pipeline (Phase 7 & Phase 8).

    Responsibilities:
    1. DocumentLoader: Load repository files from GitHub via RepositoryIngestionService
    2. RepositoryChunker: Split documents into structure-aware chunks
    3. RepositoryIndexer: Batch embed chunks and persist in PostgreSQL pgvector
    4. VectorRetriever / KeywordRetriever: Semantic or keyword-based chunk retrieval
    5. Fallback Mechanism: Falls back to KeywordRetriever when pgvector/DB is unavailable
    6. RAGContextBuilder: Format top chunks into bounded LLM prompt context
    """

    def __init__(
        self,
        document_loader: Optional[DocumentLoader] = None,
        chunker: Optional[RepositoryChunker] = None,
        retriever: Optional[KeywordRetriever] = None,
        vector_retriever: Optional[VectorRetriever] = None,
        indexer: Optional[RepositoryIndexer] = None,
        context_builder: Optional[RAGContextBuilder] = None,
    ):
        self.document_loader = document_loader or DocumentLoader()
        self.chunker = chunker or RepositoryChunker()
        self.retriever = retriever or KeywordRetriever()
        self.vector_retriever = vector_retriever or VectorRetriever()
        self.indexer = indexer or RepositoryIndexer(
            document_loader=self.document_loader,
            chunker=self.chunker,
        )
        self.context_builder = context_builder or RAGContextBuilder()

    async def prepare_documents(
        self,
        url: str,
        branch: Optional[str] = None,
    ) -> tuple[List[RepositoryDocument], RAGStatistics]:
        """Load and return repository documents with loading statistics."""
        return await self.document_loader.load_documents(url=url, branch=branch)

    def chunk_documents(
        self,
        documents: List[RepositoryDocument],
    ) -> List[RepositoryChunk]:
        """Chunk a list of documents into RepositoryChunk objects."""
        return self.chunker.chunk_documents(documents)

    def retrieve(
        self,
        query: str,
        chunks: List[RepositoryChunk],
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """Keyword retrieval over in-memory chunks."""
        k = top_k or settings.RAG_TOP_K
        return self.retriever.retrieve(query=query, chunks=chunks, top_k=k)

    def build_context(
        self,
        retrieved_chunks: List[RetrievedChunk],
    ) -> str:
        """Format retrieved chunks into bounded context text."""
        return self.context_builder.build_context(retrieved_chunks)

    async def index_repository(
        self,
        url: str,
        branch: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> RAGIndexResult:
        """
        Indexes repository chunks into PostgreSQL with pgvector embeddings.
        """
        return await self.indexer.index_repository(url=url, branch=branch, session=session)

    async def retrieve_for_query(
        self,
        url: str,
        query: str,
        branch: Optional[str] = None,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> RAGRetrievalResult:
        """
        Retrieval pipeline supporting both vector and keyword modes with automatic fallback.

        Args:
            url: GitHub repository URL.
            query: User question or search query.
            branch: Optional branch or commit ref.
            top_k: Max results to return.
            retrieval_mode: 'vector' or 'keyword' (defaults to settings.RAG_RETRIEVAL_MODE).
            session: Optional database session for vector retrieval.
        """
        k = top_k or settings.RAG_TOP_K
        mode = (retrieval_mode or settings.RAG_RETRIEVAL_MODE).lower().strip()

        # Step 1: Always load repository documents to have repository info and keyword fallback ready
        documents, load_stats = await self.prepare_documents(url=url, branch=branch)
        repository = documents[0].repository if documents else url
        chunks = self.chunk_documents(documents)

        # Attempt Vector Retrieval if requested
        if mode == "vector":
            try:
                vector_results = await self.vector_retriever.retrieve(
                    query=query,
                    repository_identifier=repository,
                    top_k=k,
                    session=session,
                )

                if vector_results:
                    stats = RAGStatistics(
                        documents_loaded=load_stats.documents_loaded,
                        documents_skipped=load_stats.documents_skipped,
                        chunks_created=len(chunks),
                        chunks_searched=len(chunks),
                        results_returned=len(vector_results),
                        truncated_files=load_stats.truncated_files,
                        total_content_chars=load_stats.total_content_chars,
                    )
                    logger.info(
                        f"RAG vector retrieve: {repository} | query='{query[:60]}' | "
                        f"results={len(vector_results)}"
                    )
                    return RAGRetrievalResult(
                        repository=repository,
                        query=query,
                        results=vector_results,
                        statistics=stats,
                        retrieval_mode="vector",
                    )
                else:
                    logger.warning(
                        f"Vector retrieval returned 0 results for '{repository}' "
                        f"(repository may not be indexed yet). Falling back to keyword retriever."
                    )
            except Exception as exc:
                logger.warning(
                    f"Vector retrieval unavailable for '{repository}' ({exc}). "
                    f"Falling back to deterministic keyword retrieval."
                )

            # Fallback to keyword retrieval
            keyword_results = self.retrieve(query=query, chunks=chunks, top_k=k)
            stats = RAGStatistics(
                documents_loaded=load_stats.documents_loaded,
                documents_skipped=load_stats.documents_skipped,
                chunks_created=len(chunks),
                chunks_searched=len(chunks),
                results_returned=len(keyword_results),
                truncated_files=load_stats.truncated_files,
                total_content_chars=load_stats.total_content_chars,
            )
            return RAGRetrievalResult(
                repository=repository,
                query=query,
                results=keyword_results,
                statistics=stats,
                retrieval_mode="keyword_fallback",
            )

        # Pure keyword mode
        keyword_results = self.retrieve(query=query, chunks=chunks, top_k=k)
        stats = RAGStatistics(
            documents_loaded=load_stats.documents_loaded,
            documents_skipped=load_stats.documents_skipped,
            chunks_created=len(chunks),
            chunks_searched=len(chunks),
            results_returned=len(keyword_results),
            truncated_files=load_stats.truncated_files,
            total_content_chars=load_stats.total_content_chars,
        )
        return RAGRetrievalResult(
            repository=repository,
            query=query,
            results=keyword_results,
            statistics=stats,
            retrieval_mode="keyword",
        )

    async def context_for_query(
        self,
        url: str,
        query: str,
        branch: Optional[str] = None,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> RAGContextResult:
        """
        Full context pipeline: retrieve chunks (vector or keyword) → build formatted context.
        """
        retrieval = await self.retrieve_for_query(
            url=url,
            query=query,
            branch=branch,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            session=session,
        )

        context = self.build_context(retrieval.results)

        return RAGContextResult(
            repository=retrieval.repository,
            query=query,
            context=context,
            retrieved_chunks=retrieval.results,
            statistics=retrieval.statistics,
            retrieval_mode=retrieval.retrieval_mode,
        )


# Singleton instance
repository_rag_service = RepositoryRAGService()
