import os
import re
from typing import Dict, List, Optional, Tuple
import logging
from app.core.config import settings
from app.schemas.repository import RepositoryInfo, ReadmeInfo, TreeItem

logger = logging.getLogger(__name__)

# Primary package manifests
PRIMARY_MANIFEST_FILENAMES = {
    "package.json", "pyproject.toml", "cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "setup.py", "requirements.txt", "gemfile", "composer.json",
    "mix.exs", "pipfile", "setup.cfg"
}

# Known entrypoint file names and patterns
ENTRY_POINT_FILENAMES = {
    "main.py", "app.py", "index.ts", "index.js", "main.go", "cli.py",
    "__main__.py", "server.js", "server.ts", "run.py", "wsgi.py", "asgi.py",
    "main.rs", "lib.rs", "index.tsx", "app.tsx", "main.cpp", "main.c",
    "mod.rs"
}

# Core build, container, and compilation configuration
CORE_BUILD_CONFIG_FILENAMES = {
    "tsconfig.json", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "makefile", "vite.config.ts", "vite.config.js", "next.config.js",
    "next.config.mjs", "webpack.config.js", "cmakelists.txt"
}

# Secondary tooling, linter, formatter configs to deprioritize
TOOLING_CONFIG_SUBSTRINGS = [
    "oxlint", "eslint", "prettier", "knip", "typedoc", "cspell",
    "editorconfig", "babel.config", "commitlint", "lint-staged"
]


def clean_markdown_for_llm_context(text: str) -> str:
    """
    Cleans badge markdown, image links, and HTML comments from markdown text
    so that LLM context is rich in descriptive prose rather than noisy badge URLs.
    """
    if not text:
        return ""
    # Remove HTML comments
    s = re.sub(r"<!--[\s\S]*?-->", "", text)
    # Remove badge images with links [![...](...)](...)
    s = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", "", s)
    # Remove standalone images ![...](...)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    # Remove HTML tags
    s = re.sub(r"<[^>]+>", " ", s)
    # Normalize multiple blank lines
    lines = [line.strip() for line in s.splitlines()]
    clean_lines = []
    for line in lines:
        if line and not (line.startswith("[![") or line.startswith("![") or "shields.io" in line or "badge.fury.io" in line):
            clean_lines.append(line)
    return "\n".join(clean_lines)


class RepositoryContextBuilder:
    """
    Constructs a controlled, prioritized context payload from repository metadata,
    directory structure, and source files within strict token/character budgets.
    """

    def __init__(
        self,
        max_context_chars: int = settings.AI_MAX_CONTEXT_CHARS,
        max_files_in_context: int = settings.AI_MAX_FILES_IN_CONTEXT,
        max_file_chars: int = settings.AI_MAX_FILE_CHARS,
    ):
        self.max_context_chars = max_context_chars
        self.max_files_in_context = max_files_in_context
        self.max_file_chars = max_file_chars

    @staticmethod
    def get_file_priority(item: TreeItem) -> Tuple[int, str]:
        """
        Assigns a deterministic sorting tuple (tier, path) to a file.
        Lower tier number indicates higher priority.
        """
        path_lower = item.path.lower()
        basename = os.path.basename(path_lower)

        # Tier 1: README files
        if basename.startswith("readme"):
            return (1, item.path)

        # Tier 2: Primary package manifests
        if basename in PRIMARY_MANIFEST_FILENAMES:
            return (2, item.path)

        # Tier 3: Known Entry points
        if basename in ENTRY_POINT_FILENAMES or path_lower.startswith("src/index.") or path_lower.startswith("src/main.") or path_lower.startswith("src/app."):
            return (3, item.path)

        # Tier 4: Core build / architecture config
        if basename in CORE_BUILD_CONFIG_FILENAMES:
            return (4, item.path)

        # Tier 5: Core source code (prioritize shallower directory paths)
        if item.category == "source":
            depth = item.path.count("/")
            return (5 + min(depth, 5), item.path)

        # Tier 12: Secondary tooling / linter / formatter configs (e.g. .oxlintrc, .prettierrc)
        if any(tool in path_lower for tool in TOOLING_CONFIG_SUBSTRINGS):
            return (18, item.path)

        # Tier 14: General configuration
        if item.category == "configuration":
            return (14, item.path)

        # Tier 15: Test files
        if item.category == "test":
            return (15, item.path)

        # Tier 16: General documentation
        if item.category == "documentation":
            return (16, item.path)

        # Tier 20: Other files
        return (20, item.path)

    def select_files_for_context(self, tree: List[TreeItem]) -> List[TreeItem]:
        """
        Selects top candidate files up to max_files_in_context using priority ordering.
        Filters out directories, ignored files, and binary files.
        Ensures source files and manifests are prioritized over secondary tool configs.
        """
        candidate_files = [
            item for item in tree
            if item.type == "file"
            and item.category not in ("generated_or_ignored", "binary_or_unsupported")
        ]

        # Deterministic sort by priority tier, then lexicographical path
        sorted_files = sorted(candidate_files, key=self.get_file_priority)
        return sorted_files[:self.max_files_in_context]

    def format_tree_summary(self, tree: List[TreeItem], max_items: int = 80) -> str:
        """
        Produces a concise text representation of the repository file tree.
        Excludes ignored directories and limits output to prevent prompt overflow.
        """
        filtered_items = [
            item for item in tree
            if item.category != "generated_or_ignored"
        ]

        # Truncate if tree is very large
        display_items = filtered_items[:max_items]

        lines = []
        for item in display_items:
            prefix = "[DIR] " if item.type == "directory" else "      "
            cat_label = f" ({item.category})" if item.category and item.category != "source" else ""
            lang_label = f" [{item.language}]" if item.language else ""
            lines.append(f"{prefix}{item.path}{lang_label}{cat_label}")

        if len(filtered_items) > max_items:
            lines.append(f"... and {len(filtered_items) - max_items} more items in repository tree.")

        return "\n".join(lines) if lines else "No files listed in repository tree."

    def build_context(
        self,
        repository: RepositoryInfo,
        languages: Dict[str, int],
        readme: Optional[ReadmeInfo],
        tree: List[TreeItem],
        file_contents: Dict[str, str],
    ) -> str:
        """
        Assembles all components into a structured text prompt within character limits.
        """
        sections = []

        # 1. Metadata Section
        meta_lines = [
            "### 1. REPOSITORY METADATA",
            f"- Full Name: {repository.full_name}",
            f"- Default Branch: {repository.default_branch}",
            f"- Primary Language: {repository.language or 'Not specified'}",
            f"- Stars: {repository.stars:,} | Forks: {repository.forks:,} | Open Issues/PRs: {repository.open_issues_count:,}",
            f"- License: {repository.license.name if repository.license else 'Not specified'}",
        ]
        if repository.description:
            meta_lines.append(f"- Description: {repository.description}")
        if repository.topics:
            meta_lines.append(f"- Topics: {', '.join(repository.topics)}")
        sections.append("\n".join(meta_lines))

        # 2. Languages Section
        if languages:
            total_bytes = sum(languages.values()) or 1
            lang_breakdown = [
                f"{lang}: {bytes_count:,} bytes ({bytes_count / total_bytes * 100:.1f}%)"
                for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:8]
            ]
            sections.append(
                "### 2. LANGUAGE BREAKDOWN (BY BYTES)\n" + "\n".join(f"- {item}" for item in lang_breakdown)
            )

        # 3. Repository Structure / Tree
        tree_text = self.format_tree_summary(tree)
        sections.append(f"### 3. REPOSITORY FILE STRUCTURE\n```\n{tree_text}\n```")

        # 4. README Section (Cleaned of noisy badge markup)
        if readme and readme.content:
            cleaned_readme = clean_markdown_for_llm_context(readme.content)
            readme_text = cleaned_readme.strip() if cleaned_readme.strip() else readme.content.strip()
            max_readme_chars = min(12000, self.max_file_chars * 2)
            if len(readme_text) > max_readme_chars:
                readme_text = readme_text[:max_readme_chars] + "\n\n[... README truncated for brevity ...]"
            sections.append(f"### 4. README CONTENT ({readme.name})\n```markdown\n{readme_text}\n```")
        else:
            sections.append("### 4. README CONTENT\nNo README file detected in repository.")

        # 5. Selected Source Files Section
        if file_contents:
            file_sections = ["### 5. SELECTED SOURCE AND CONFIGURATION FILES"]
            # Sort files according to priority
            for path, content in sorted(file_contents.items()):
                if not content:
                    continue
                trimmed_content = content.strip()
                if len(trimmed_content) > self.max_file_chars:
                    trimmed_content = (
                        trimmed_content[:self.max_file_chars]
                        + f"\n\n[... File truncated: showing first {self.max_file_chars} characters ...]"
                    )
                file_sections.append(f"#### File: {path}\n```\n{trimmed_content}\n```")

            sections.append("\n\n".join(file_sections))

        full_context = "\n\n".join(sections)

        # Enforce global character budget safety limit
        if len(full_context) > self.max_context_chars:
            logger.warning(
                f"Context length ({len(full_context)} chars) exceeds maximum budget "
                f"({self.max_context_chars} chars). Truncating safely."
            )
            full_context = (
                full_context[:self.max_context_chars]
                + "\n\n[... Total context truncated to fit model context limit ...]"
            )

        return full_context


repository_context_builder = RepositoryContextBuilder()
