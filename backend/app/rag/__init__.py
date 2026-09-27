"""
RAG (Retrieval-Augmented Generation) pipeline for OpenSource Copilot.

Phase 7: Deterministic keyword-based retrieval pipeline.
Architecture: DocumentLoader → Chunker → Retriever → ContextBuilder
"""

from app.rag.models import (
    RepositoryDocument,
    RepositoryChunk,
    RetrievedChunk,
    RAGStatistics,
)
from app.rag.document_loader import DocumentLoader
from app.rag.chunker import RepositoryChunker
from app.rag.retriever import KeywordRetriever
from app.rag.context import RAGContextBuilder
from app.rag.indexer import RAGIndexResult, RepositoryIndexer
from app.rag.service import RepositoryRAGService
from app.rag.vector_retriever import VectorRetriever

__all__ = [
    "RepositoryDocument",
    "RepositoryChunk",
    "RetrievedChunk",
    "RAGStatistics",
    "DocumentLoader",
    "RepositoryChunker",
    "KeywordRetriever",
    "RAGContextBuilder",
    "RepositoryIndexer",
    "RAGIndexResult",
    "VectorRetriever",
    "RepositoryRAGService",
]
