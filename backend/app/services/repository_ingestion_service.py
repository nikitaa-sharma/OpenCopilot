"""
Repository ingestion orchestration service for OpenSource Copilot.
Coordinates tree retrieval, file filtering, language detection, safety limits,
and source-code ingestion without executing any repository code.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.github_service import (
    github_service,
    parse_github_url,
    GitHubService,
)
from app.services.repository_file_filter import (
    classify_file,
    detect_language,
    is_relevant_for_ingestion,
)

logger = logging.getLogger(__name__)


class RepositoryIngestionService:
    """
    Orchestration service for repository file tree inspection and code ingestion.
    """

    def __init__(self, service: Optional[GitHubService] = None):
        self.github_service = service or github_service

    async def get_repository_tree(
        self, owner: str, repo: str, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch and enrich repository tree with file classifications and language tags.
        Applies MAX_TREE_ITEMS limit.
        """
        # If branch is not specified, fetch repository default branch
        target_branch = branch
        if not target_branch:
            try:
                repo_meta = await self.github_service.fetch_repository(owner, repo)
                target_branch = repo_meta.get("default_branch", "main")
            except Exception as exc:
                logger.warning(
                    f"Could not determine default branch for {owner}/{repo}, falling back to 'HEAD': {exc}"
                )
                target_branch = "HEAD"

        raw_tree_data = await self.github_service.fetch_tree(
            owner, repo, branch=target_branch, recursive=True
        )

        items = raw_tree_data.get("tree", [])
        truncated = raw_tree_data.get("truncated", False)

        # Enforce MAX_TREE_ITEMS safety limit
        if len(items) > settings.MAX_TREE_ITEMS:
            items = items[: settings.MAX_TREE_ITEMS]
            truncated = True

        enriched_tree: List[Dict[str, Any]] = []
        for item in items:
            path = item.get("path", "")
            item_type = item.get("type", "file")

            category = None
            language = None
            if item_type == "file":
                category = classify_file(path)
                language = detect_language(path)

            enriched_tree.append({
                "path": path,
                "type": item_type,
                "size": item.get("size"),
                "sha": item.get("sha"),
                "category": category,
                "language": language,
            })

        return {
            "repository": f"{owner}/{repo}",
            "branch": target_branch,
            "truncated": truncated,
            "total_items": len(enriched_tree),
            "tree": enriched_tree,
        }

    async def get_file_content(
        self, owner: str, repo: str, path: str, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch individual file content with metadata, language, and category.
        """
        file_data = await self.github_service.fetch_file_content(
            owner, repo, path=path, branch=branch
        )

        category = classify_file(path)
        language = detect_language(path)

        return {
            "path": file_data["path"],
            "name": file_data["name"],
            "language": language,
            "category": category,
            "size": file_data["size"],
            "sha": file_data["sha"],
            "content": file_data["content"],
            "encoding": "utf-8",
            "is_binary": file_data["is_binary"],
            "skip_reason": file_data["skip_reason"],
        }

    async def ingest_repository(
        self, url: str, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest relevant repository source files up to safety thresholds.
        Tracks ingestion metrics and filters out binaries, tests, and build artifacts.
        """
        owner, repo = parse_github_url(url)

        # 1. Fetch tree
        tree_response = await self.get_repository_tree(owner, repo, branch=branch)
        target_branch = tree_response["branch"]
        tree_items = tree_response["tree"]

        total_tree_items = len(tree_items)
        directories = 0
        total_files = 0
        candidate_files: List[Dict[str, Any]] = []

        for item in tree_items:
            if item["type"] == "directory":
                directories += 1
            else:
                total_files += 1
                if is_relevant_for_ingestion(item["path"], item.get("category")):
                    candidate_files.append(item)

        # 2. Ingest selected files adhering to MAX_SOURCE_FILES and MAX_TOTAL_CODE_BYTES
        ingested_files: List[Dict[str, Any]] = []
        total_code_bytes = 0

        for candidate in candidate_files:
            if len(ingested_files) >= settings.MAX_SOURCE_FILES:
                logger.info(
                    f"Reached MAX_SOURCE_FILES limit ({settings.MAX_SOURCE_FILES}) for {owner}/{repo}"
                )
                break

            if total_code_bytes >= settings.MAX_TOTAL_CODE_BYTES:
                logger.info(
                    f"Reached MAX_TOTAL_CODE_BYTES limit ({settings.MAX_TOTAL_CODE_BYTES}) for {owner}/{repo}"
                )
                break

            try:
                file_info = await self.get_file_content(
                    owner, repo, path=candidate["path"], branch=target_branch
                )
                if file_info.get("content"):
                    content_size = len(file_info["content"].encode("utf-8"))
                    total_code_bytes += content_size

                ingested_files.append(file_info)
            except Exception as exc:
                logger.warning(
                    f"Failed to fetch content for file '{candidate['path']}': {exc}"
                )
                ingested_files.append({
                    "path": candidate["path"],
                    "name": candidate["path"].split("/")[-1],
                    "language": candidate.get("language"),
                    "category": candidate.get("category", "source"),
                    "size": candidate.get("size", 0),
                    "sha": candidate.get("sha"),
                    "content": None,
                    "encoding": "utf-8",
                    "is_binary": False,
                    "skip_reason": f"Fetch failed: {exc}",
                })

        selected_files = len(ingested_files)
        skipped_files = max(0, total_files - selected_files)

        return {
            "repository": {
                "owner": owner,
                "name": repo,
                "branch": target_branch,
            },
            "statistics": {
                "total_tree_items": total_tree_items,
                "directories": directories,
                "files": total_files,
                "selected_files": selected_files,
                "skipped_files": skipped_files,
                "total_code_bytes": total_code_bytes,
            },
            "files": ingested_files,
        }


# Singleton service instance
repository_ingestion_service = RepositoryIngestionService()
