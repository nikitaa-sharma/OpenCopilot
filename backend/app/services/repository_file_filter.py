"""
Repository file filtering and classification service for OpenSource Copilot.
Identifies relevant source and documentation files for code understanding,
while safely filtering out binary, generated, and ignored directories/artifacts.
"""

import os
import re
from typing import Optional, Set

# Ignored directory names anywhere in the file path
IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".gradle",
    ".idea",
    ".vscode",
    "out",
    ".nuget",
    "packages",
    "bin",
    "obj",
    ".cache",
}

# Binary, compiled, media, and archive file extensions
BINARY_AND_ARCHIVE_EXTENSIONS: Set[str] = {
    # Images & Media
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".flac",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Archives & Compressed
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".tgz",
    # Executables & Binaries
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".dmg",
    # Compiled Code
    ".class", ".jar", ".war", ".ear", ".pyc", ".pyo", ".pyd", ".wasm", ".o", ".a",
    # Documents / Bundles
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Databases
    ".db", ".sqlite", ".sqlite3",
    # Source Maps & Minified
    ".map",
}

# Recognized source code extensions
SOURCE_EXTENSIONS: Set[str] = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".dart",
    ".scala",
    ".lua",
    ".sh",
    ".bash",
    ".zsh",
    ".r",
    ".m",
    ".sql",
    ".vue",
    ".svelte",
    ".proto",
}

# Recognized documentation extensions
DOCUMENTATION_EXTENSIONS: Set[str] = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".adoc",
    ".asciidoc",
}

# Configuration and structured data formats
CONFIGURATION_EXTENSIONS: Set[str] = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".ini",
    ".cfg",
    ".env.example",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
}

# Canonical programming language mapping
LANGUAGE_EXTENSION_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C/C++ Header",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".dart": "Dart",
    ".scala": "Scala",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".r": "R",
    ".m": "Objective-C",
    ".sql": "SQL",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".proto": "Protocol Buffers",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".mdx": "MDX",
    ".rst": "reStructuredText",
}

# Generated lockfiles or package manifests that can be classified as generated_or_ignored
GENERATED_OR_LOCK_FILES: Set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Gemfile.lock",
    "composer.lock",
    "Cargo.lock",
}


def should_ignore_path(path: str) -> bool:
    """
    Determine if a file path belongs to an ignored directory or has an ignored extension.
    """
    normalized = path.replace("\\", "/").strip("/")
    segments = normalized.split("/")

    # Check for path traversal or dangerous segments
    for seg in segments:
        if seg in ("..", ".") or seg.startswith(".."):
            return True

    # Check for ignored directories in any part of the path
    for seg in segments[:-1]:
        if seg.lower() in IGNORED_DIRECTORIES:
            return True


    # If the item itself is a directory in IGNORED_DIRECTORIES
    if segments and segments[-1].lower() in IGNORED_DIRECTORIES:
        return True

    filename = segments[-1].lower() if segments else ""

    # Check minified scripts/styles
    if filename.endswith(".min.js") or filename.endswith(".min.css"):
        return True

    # Check binary / archive extensions
    _, ext = os.path.splitext(filename)
    if ext in BINARY_AND_ARCHIVE_EXTENSIONS:
        return True

    return False


def is_test_file(path: str) -> bool:
    """
    Identify if a file is a test file based on its path or filename convention.
    """
    normalized = path.replace("\\", "/").lower()
    segments = normalized.split("/")
    filename = segments[-1] if segments else ""

    # Check directory segment conventions
    for seg in segments[:-1]:
        if seg in ("test", "tests", "__tests__", "testing", "spec", "specs"):
            return True

    # Check filename conventions
    if (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith(".test.ts")
        or filename.endswith(".test.tsx")
        or filename.endswith(".test.js")
        or filename.endswith(".test.jsx")
        or filename.endswith(".spec.ts")
        or filename.endswith(".spec.tsx")
        or filename.endswith(".spec.js")
        or filename.endswith(".spec.jsx")
        or filename.endswith("_spec.rb")
        or filename.endswith("test.java")
    ):
        return True

    return False


def classify_file(path: str) -> str:
    """
    Classify a file path into one of the designated categories:
    - 'source'
    - 'test'
    - 'documentation'
    - 'configuration'
    - 'generated_or_ignored'
    - 'binary_or_unsupported'
    """
    normalized = path.replace("\\", "/").strip("/")
    segments = normalized.split("/")
    filename = segments[-1].lower() if segments else ""

    # 1. Ignored directories
    for seg in segments[:-1]:
        if seg.lower() in IGNORED_DIRECTORIES:
            return "generated_or_ignored"

    # 2. Lockfiles
    if filename in {name.lower() for name in GENERATED_OR_LOCK_FILES}:
        return "generated_or_ignored"

    # 3. Binary or archive extensions
    _, ext = os.path.splitext(filename)
    if ext in BINARY_AND_ARCHIVE_EXTENSIONS or filename.endswith(".min.js") or filename.endswith(".min.css"):
        return "binary_or_unsupported"

    # 4. Test files
    if is_test_file(path):
        return "test"

    # 5. Documentation
    if ext in DOCUMENTATION_EXTENSIONS:
        return "documentation"

    # 6. Source code
    if ext in SOURCE_EXTENSIONS:
        return "source"

    # 7. Configuration & Web formats
    if ext in CONFIGURATION_EXTENSIONS or filename in ("dockerfile", "makefile", "license", "licence"):
        return "configuration"

    # Fallback for unrecognized non-binary text files or unknown formats
    return "binary_or_unsupported"


def detect_language(path: str) -> Optional[str]:
    """
    Determine the canonical language name for a given file path.
    """
    normalized = path.replace("\\", "/").strip("/")
    filename = normalized.split("/")[-1].lower() if normalized else ""

    # Special filenames
    if filename == "dockerfile":
        return "Dockerfile"
    if filename == "makefile":
        return "Makefile"

    _, ext = os.path.splitext(filename)
    return LANGUAGE_EXTENSION_MAP.get(ext)


def is_relevant_for_ingestion(path: str, category: Optional[str] = None) -> bool:
    """
    Determine whether a file should be included in source code ingestion.
    Relevant categories: 'source', 'test', 'documentation', 'configuration'.
    """
    if should_ignore_path(path):
        return False

    cat = category or classify_file(path)
    return cat in ("source", "test", "documentation", "configuration")
