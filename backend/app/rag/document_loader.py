"""
Document loader for the RAG pipeline.

Reuses the existing RepositoryIngestionService from Phase 4 to load
repository files as structured RepositoryDocument objects without
duplicating GitHub API calls.
"""

import logging
from typing import List, Optional, Tuple

from app.rag.models import RepositoryDocument, RAGStatistics
from app.services.repository_ingestion_service import (
    RepositoryIngestionService,
    repository_ingestion_service,
)

logger = logging.getLogger(__name__)

# Categories eligible for RAG processing
SUPPORTED_CATEGORIES = {"source", "test", "documentation", "configuration"}


class DocumentLoader:
    """
    Loads repository files into RepositoryDocument objects for RAG processing.

    Delegates to RepositoryIngestionService to avoid duplicating GitHub API calls,
    then filters and normalizes the results into the RAG domain model.
    """

    def __init__(
        self,
        ingestion_service: Optional[RepositoryIngestionService] = None,
    ):
        self.ingestion_service = ingestion_service or repository_ingestion_service

    async def load_documents(
        self,
        url: str,
        branch: Optional[str] = None,
    ) -> Tuple[List[RepositoryDocument], RAGStatistics]:
        """
        Load repository files as structured documents for RAG processing.

        Args:
            url: GitHub repository URL (e.g. "https://github.com/pallets/flask")
            branch: Optional branch or commit ref.

        Returns:
            Tuple of (list of RepositoryDocument, RAGStatistics).
        """
        # Reuse the Phase 4 ingestion pipeline
        ingestion_result = await self.ingestion_service.ingest_repository(
            url=url, branch=branch
        )

        repo_info = ingestion_result["repository"]
        owner = repo_info["owner"]
        repo_name = repo_info["name"]
        target_branch = repo_info["branch"]
        repository = f"{owner}/{repo_name}"

        files = ingestion_result["files"]

        documents: List[RepositoryDocument] = []
        skipped = 0
        truncated = 0
        total_chars = 0

        for file_data in files:
            # Skip binary files
            if file_data.get("is_binary", False):
                skipped += 1
                continue

            # Skip files with a skip reason (fetch failures, size limits, etc.)
            if file_data.get("skip_reason"):
                skipped += 1
                continue

            # Skip files without content
            content = file_data.get("content")
            if not content or not content.strip():
                skipped += 1
                continue

            # Only include supported categories
            category = file_data.get("category", "")
            if category not in SUPPORTED_CATEGORIES:
                skipped += 1
                continue

            file_path = file_data.get("path", "")
            file_name = file_data.get("name", file_path.split("/")[-1] if file_path else "")
            language = file_data.get("language")
            sha = file_data.get("sha")
            size = len(content.encode("utf-8"))

            total_chars += len(content)

            doc = RepositoryDocument(
                repository=repository,
                owner=owner,
                repo_name=repo_name,
                branch=target_branch,
                file_path=file_path,
                file_name=file_name,
                category=category,
                language=language,
                sha=sha,
                content=content,
                size_bytes=size,
            )
            documents.append(doc)

        stats = RAGStatistics(
            documents_loaded=len(documents),
            documents_skipped=skipped,
            truncated_files=truncated,
            total_content_chars=total_chars,
        )

        logger.info(
            f"Loaded {len(documents)} documents from {repository}@{target_branch} "
            f"(skipped {skipped})"
        )

        return documents, stats
