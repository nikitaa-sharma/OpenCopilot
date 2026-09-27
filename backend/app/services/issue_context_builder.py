import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.schemas.repository import RepositoryInfo, TreeItem

logger = logging.getLogger(__name__)


class IssueContextBuilder:
    """
    Constructs a focused, grounded context payload for analyzing a specific GitHub issue.
    Integrates issue details, repository metadata, complete tree paths, and targeted candidate
    file excerpts within strict token/character budgets.
    """

    def __init__(
        self,
        max_context_chars: int = settings.AI_MAX_CONTEXT_CHARS,
        max_candidate_files: int = 5,
        max_file_chars: int = 4000,
    ):
        self.max_context_chars = max_context_chars
        self.max_candidate_files = max_candidate_files
        self.max_file_chars = max_file_chars

    @staticmethod
    def extract_keywords_from_issue(title: str, body: str, labels: List[str]) -> Set[str]:
        """
        Extract meaningful identifiers, filenames, and keywords from issue text.
        Includes words mentioned in backticks, file extensions, and CamelCase/snake_case tokens.
        """
        combined = f"{title} {body} {' '.join(labels)}"
        keywords: Set[str] = set()

        # Extract items in backticks (e.g. `fastapi/routing.py`, `get_param`)
        backtick_tokens = re.findall(r"`([^`]+)`", combined)
        for token in backtick_tokens:
            token_clean = token.strip()
            if "/" in token_clean or "." in token_clean or "_" in token_clean:
                keywords.add(token_clean.lower())
                # Also add path components
                for part in token_clean.split("/"):
                    if len(part) > 2:
                        keywords.add(part.lower())

        # Extract file paths or filenames (e.g. test_foo.py, utils.py)
        file_matches = re.findall(r"[\w\-\./]+\.[a-zA-Z0-9]+", combined)
        for match in file_matches:
            if len(match) > 3 and not match.startswith("http"):
                keywords.add(match.lower())
                keywords.add(os.path.basename(match).lower())

        # Extract general tokens with length >= 4
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", combined)
        common_stop_words = {
            "this", "that", "with", "from", "have", "would", "could", "should",
            "there", "where", "which", "about", "issue", "error", "problem",
            "please", "thanks", "hello", "using", "when", "after", "before"
        }
        for word in words:
            w_lower = word.lower()
            if w_lower not in common_stop_words:
                keywords.add(w_lower)

        return keywords

    def rank_candidate_files(
        self,
        tree: List[TreeItem],
        keywords: Set[str],
    ) -> List[Tuple[TreeItem, int]]:
        """
        Ranks repository files by relevance to the issue based on keyword matching
        against the file path, filename, and directory structure.
        Returns list of (TreeItem, score) sorted descending by score.
        """
        scored: List[Tuple[TreeItem, int]] = []

        for item in tree:
            if item.type != "file":
                continue
            if item.category in ("generated_or_ignored", "binary_or_unsupported"):
                continue

            path_lower = item.path.lower()
            base_name = os.path.basename(path_lower)
            name_without_ext, _ = os.path.splitext(base_name)
            score = 0

            for kw in keywords:
                # Exact path match
                if kw == path_lower or kw == base_name:
                    score += 20
                # Exact filename match
                elif kw == name_without_ext:
                    score += 15
                # Substring in filename
                elif kw in base_name:
                    score += 8
                # Substring in path directory
                elif kw in path_lower:
                    score += 4

            if score > 0:
                scored.append((item, score))

        # Sort by score desc, then path length asc (prefer more specific or higher match)
        scored.sort(key=lambda x: (-x[1], len(x[0].path), x[0].path))
        return scored

    def format_tree_for_prompt(self, tree: List[TreeItem], max_paths: int = 200) -> str:
        """
        Formats repository tree paths concisely so the LLM knows all existing candidate files.
        """
        file_paths = [
            item.path for item in tree
            if item.type == "file"
            and item.category not in ("generated_or_ignored", "binary_or_unsupported")
        ]

        if not file_paths:
            return "No files identified in repository tree."

        if len(file_paths) > max_paths:
            displayed = file_paths[:max_paths]
            return "\n".join(displayed) + f"\n... and {len(file_paths) - max_paths} more files."
        return "\n".join(file_paths)

    def build_context(
        self,
        issue: Dict[str, Any],
        repository: RepositoryInfo,
        languages: Dict[str, int],
        tree: List[TreeItem],
        readme_content: Optional[str] = None,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """
        Assembles structured prompt context for issue analysis.

        Returns:
            Tuple of (formatted_context_string, stats_dict)
        """
        file_contents = file_contents or {}
        sections: List[str] = []

        # 1. Issue Information
        issue_number = issue.get("number")
        issue_title = issue.get("title", "Untitled Issue")
        issue_body = issue.get("body", "") or "No description provided."
        issue_labels = issue.get("labels", [])
        issue_author = issue.get("user", "Unknown")
        issue_state = issue.get("state", "open")

        labels_formatted = ", ".join(issue_labels) if issue_labels else "None"

        # Limit issue body to 8000 chars if excessively large
        if len(issue_body) > 8000:
            issue_body = issue_body[:8000] + "\n\n[... Remaining issue body truncated for context length ...]"

        issue_section = (
            f"### ISSUE DETAILS\n"
            f"- Issue Number: #{issue_number}\n"
            f"- Title: {issue_title}\n"
            f"- State: {issue_state}\n"
            f"- Author: {issue_author}\n"
            f"- Labels: {labels_formatted}\n\n"
            f"#### Issue Description:\n"
            f"{issue_body}"
        )
        sections.append(issue_section)

        # 2. Repository Overview
        top_languages = list(languages.keys())[:5]
        lang_str = ", ".join(top_languages) if top_languages else "Not specified"
        repo_section = (
            f"### REPOSITORY OVERVIEW\n"
            f"- Repository: {repository.owner}/{repository.name}\n"
            f"- Description: {repository.description or 'None provided'}\n"
            f"- Primary Languages: {lang_str}\n"
            f"- Default Branch: {repository.default_branch}"
        )
        sections.append(repo_section)

        # 3. Readme Excerpt (if available and space permits)
        if readme_content:
            clean_readme = readme_content.strip()
            if len(clean_readme) > 2000:
                clean_readme = clean_readme[:2000] + "\n[... README excerpt truncated ...]"
            sections.append(f"### REPOSITORY README (EXCERPT)\n{clean_readme}")

        # 4. Repository File Tree
        tree_text = self.format_tree_for_prompt(tree, max_paths=180)
        sections.append(f"### REPOSITORY FILE TREE (Existing Valid Paths)\n{tree_text}")

        # 5. Targeted Candidate File Contents
        files_included = 0
        if file_contents:
            file_sections: List[str] = []
            for path, content in file_contents.items():
                clean_content = content.strip()
                if len(clean_content) > self.max_file_chars:
                    clean_content = (
                        clean_content[: self.max_file_chars]
                        + f"\n\n[... File '{path}' truncated at {self.max_file_chars} characters ...]"
                    )
                file_sections.append(
                    f"#### File: {path}\n```\n{clean_content}\n```"
                )
                files_included += 1

            if file_sections:
                sections.append(
                    "### CANDIDATE FILE EXCERPTS (Heuristically Selected for Reference)\n"
                    + "\n\n".join(file_sections)
                )

        full_context = "\n\n" + ("\n\n---\n\n".join(sections)) + "\n\n"

        # Ensure we stay strictly within max_context_chars
        if len(full_context) > self.max_context_chars:
            logger.warning(
                f"Context size ({len(full_context)} chars) exceeds budget ({self.max_context_chars} chars). Truncating."
            )
            full_context = full_context[: self.max_context_chars] + "\n\n[... Context truncated to character budget ...]"

        stats = {
            "files_included": files_included,
            "total_context_chars": len(full_context),
        }

        return full_context, stats


issue_context_builder = IssueContextBuilder()
