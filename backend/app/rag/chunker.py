"""
Intelligent repository document chunker for the RAG pipeline.

Splits documents into structured chunks using structure-aware strategies:
- Source code: function/class boundary splitting
- Markdown/documentation: heading-based splitting
- Configuration: section-based splitting
- Generic fallback: line-based overlap splitting
"""

import logging
import re
from typing import List, Optional

from app.core.config import settings
from app.rag.models import RepositoryChunk, RepositoryDocument, RAGStatistics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language-specific boundary patterns
# ---------------------------------------------------------------------------

# Python: function or class definition at top level or indented
_PY_BOUNDARY = re.compile(
    r"^(async\s+def\s|def\s|class\s)",
    re.MULTILINE,
)

# JavaScript / TypeScript: function, class, export declarations
_JS_BOUNDARY = re.compile(
    r"^(export\s+(?:default\s+)?(?:async\s+)?(?:function|class)\s"
    r"|(?:async\s+)?function\s"
    r"|class\s)",
    re.MULTILINE,
)

# Go: func declarations
_GO_BOUNDARY = re.compile(r"^func\s", re.MULTILINE)

# Rust: fn or impl blocks
_RUST_BOUNDARY = re.compile(r"^(pub\s+)?(?:async\s+)?fn\s|^impl\s", re.MULTILINE)

# Java / C# / Kotlin: method/class declarations
_JAVA_BOUNDARY = re.compile(
    r"^(?:public|private|protected|static|final|abstract|override|async)[\s\w<\[\]@]*"
    r"(?:class|interface|void|int|String|bool|Boolean|List|Map)\s",
    re.MULTILINE,
)

# Markdown headings
_MD_HEADING = re.compile(r"^#{1,6}\s+.+", re.MULTILINE)

# RST headings (underline style)
_RST_SECTION_UNDERLINE = re.compile(r"^[=\-`:.~^_*+#]{3,}\s*$", re.MULTILINE)

# YAML/TOML top-level keys (no leading whitespace)
_YAML_TOP_KEY = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]*\s*[:=]", re.MULTILINE)

# JSON top-level keys
_JSON_TOP_KEY = re.compile(r'^\s{0,2}"[^"]+"\s*:', re.MULTILINE)


def _make_chunk_id(repository: str, file_path: str, index: int) -> str:
    return f"{repository}:{file_path}:{index}"


def _line_number_map(content: str) -> List[int]:
    """Return the character offset of each line start (0-indexed list)."""
    offsets = [0]
    for char in content:
        if char == "\n":
            offsets.append(offsets[-1] + 1)
        else:
            offsets[-1] += 1
    # Convert cumulative to absolute offsets
    absolute: List[int] = []
    pos = 0
    for line in content.split("\n"):
        absolute.append(pos)
        pos += len(line) + 1  # +1 for \n
    return absolute


def _char_offset_to_line(offset: int, line_starts: List[int]) -> int:
    """Convert a character offset to a 1-based line number."""
    lo, hi = 0, len(line_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1  # 1-based


def _build_chunks_from_splits(
    document: RepositoryDocument,
    split_offsets: List[int],
    max_chunk_size: int,
    max_chunks: int,
) -> List[RepositoryChunk]:
    """
    Given a list of character offsets where splits should occur, build chunks.
    Each split offset marks the START of a new logical block.
    If a block exceeds max_chunk_size, it is sub-split by character budget.
    """
    content = document.content
    line_starts = _line_number_map(content)
    chunks: List[RepositoryChunk] = []

    # Ensure we start from 0
    if not split_offsets or split_offsets[0] != 0:
        split_offsets = [0] + split_offsets

    # Add sentinel at end
    split_offsets = split_offsets + [len(content)]

    for i in range(len(split_offsets) - 1):
        if len(chunks) >= max_chunks:
            break

        block_start = split_offsets[i]
        block_end = split_offsets[i + 1]
        block = content[block_start:block_end]

        if not block.strip():
            continue

        # Sub-split large blocks
        if len(block) > max_chunk_size:
            sub_offset = block_start
            while sub_offset < block_end and len(chunks) < max_chunks:
                sub_end = min(sub_offset + max_chunk_size, block_end)
                sub_content = content[sub_offset:sub_end]
                if sub_content.strip():
                    sl = _char_offset_to_line(sub_offset, line_starts)
                    el = _char_offset_to_line(sub_end - 1, line_starts)
                    idx = len(chunks)
                    chunks.append(
                        RepositoryChunk(
                            chunk_id=_make_chunk_id(
                                document.repository, document.file_path, idx
                            ),
                            repository=document.repository,
                            file_path=document.file_path,
                            language=document.language,
                            category=document.category,
                            chunk_index=idx,
                            start_line=sl,
                            end_line=el,
                            content=sub_content,
                            metadata={
                                "repository": document.repository,
                                "file_path": document.file_path,
                                "language": document.language,
                                "category": document.category,
                                "start_line": sl,
                                "end_line": el,
                            },
                        )
                    )
                sub_offset = sub_end
        else:
            sl = _char_offset_to_line(block_start, line_starts)
            el = _char_offset_to_line(
                block_end - 1 if block_end > block_start else block_start,
                line_starts,
            )
            idx = len(chunks)
            chunks.append(
                RepositoryChunk(
                    chunk_id=_make_chunk_id(
                        document.repository, document.file_path, idx
                    ),
                    repository=document.repository,
                    file_path=document.file_path,
                    language=document.language,
                    category=document.category,
                    chunk_index=idx,
                    start_line=sl,
                    end_line=el,
                    content=block,
                    metadata={
                        "repository": document.repository,
                        "file_path": document.file_path,
                        "language": document.language,
                        "category": document.category,
                        "start_line": sl,
                        "end_line": el,
                    },
                )
            )

    return chunks


def _line_based_chunks(
    document: RepositoryDocument,
    chunk_size: int,
    overlap: int,
    max_chunks: int,
) -> List[RepositoryChunk]:
    """
    Fallback: line-based splitting with character budget and overlap.
    """
    lines = document.content.split("\n")
    chunks: List[RepositoryChunk] = []

    i = 0
    while i < len(lines) and len(chunks) < max_chunks:
        accumulated = []
        char_count = 0
        j = i
        while j < len(lines):
            line_len = len(lines[j]) + 1  # +1 for \n
            if char_count + line_len > chunk_size and accumulated:
                break
            accumulated.append(lines[j])
            char_count += line_len
            j += 1

        content = "\n".join(accumulated)
        if content.strip():
            idx = len(chunks)
            sl = i + 1  # 1-based
            el = j  # inclusive
            chunks.append(
                RepositoryChunk(
                    chunk_id=_make_chunk_id(
                        document.repository, document.file_path, idx
                    ),
                    repository=document.repository,
                    file_path=document.file_path,
                    language=document.language,
                    category=document.category,
                    chunk_index=idx,
                    start_line=sl,
                    end_line=el,
                    content=content,
                    metadata={
                        "repository": document.repository,
                        "file_path": document.file_path,
                        "language": document.language,
                        "category": document.category,
                        "start_line": sl,
                        "end_line": el,
                    },
                )
            )

        # Move forward, applying overlap in terms of characters
        # Calculate how many lines to step back for overlap
        overlap_lines = 0
        overlap_chars = 0
        for k in range(len(accumulated) - 1, -1, -1):
            overlap_chars += len(accumulated[k]) + 1
            if overlap_chars >= overlap:
                break
            overlap_lines += 1

        step = max(1, len(accumulated) - overlap_lines)
        i += step

    return chunks


def _chunk_source_code(
    document: RepositoryDocument,
    chunk_size: int,
    max_chunks: int,
) -> List[RepositoryChunk]:
    """Split source code on function/class boundaries."""
    content = document.content
    language = (document.language or "").lower()

    # Select boundary pattern by language
    pattern: Optional[re.Pattern] = None
    if "python" in language:
        pattern = _PY_BOUNDARY
    elif any(l in language for l in ("javascript", "typescript", "jsx", "tsx")):
        pattern = _JS_BOUNDARY
    elif language == "go":
        pattern = _GO_BOUNDARY
    elif "rust" in language:
        pattern = _RUST_BOUNDARY
    elif any(l in language for l in ("java", "kotlin", "c#", "c++")):
        pattern = _JAVA_BOUNDARY

    if pattern:
        matches = list(pattern.finditer(content))
        if matches:
            split_offsets = [m.start() for m in matches]
            return _build_chunks_from_splits(
                document, split_offsets, chunk_size, max_chunks
            )

    # Fallback: line-based
    return _line_based_chunks(
        document,
        chunk_size=chunk_size,
        overlap=settings.RAG_CHUNK_OVERLAP,
        max_chunks=max_chunks,
    )


def _chunk_markdown(
    document: RepositoryDocument,
    chunk_size: int,
    max_chunks: int,
) -> List[RepositoryChunk]:
    """Split Markdown on heading boundaries."""
    content = document.content

    matches = list(_MD_HEADING.finditer(content))
    if matches:
        split_offsets = [m.start() for m in matches]
        return _build_chunks_from_splits(
            document, split_offsets, chunk_size, max_chunks
        )

    # Try RST-style sections
    rst_matches = list(_RST_SECTION_UNDERLINE.finditer(content))
    if rst_matches:
        # The section title is the line BEFORE the underline
        offsets: List[int] = []
        lines = content.split("\n")
        char_pos = 0
        for i, line in enumerate(lines):
            if i > 0 and _RST_SECTION_UNDERLINE.match(line):
                # Title is line i-1
                prev_start = sum(len(l) + 1 for l in lines[: i - 1])
                offsets.append(prev_start)
            char_pos += len(line) + 1
        if offsets:
            return _build_chunks_from_splits(document, offsets, chunk_size, max_chunks)

    return _line_based_chunks(
        document,
        chunk_size=chunk_size,
        overlap=settings.RAG_CHUNK_OVERLAP,
        max_chunks=max_chunks,
    )


def _chunk_configuration(
    document: RepositoryDocument,
    chunk_size: int,
    max_chunks: int,
) -> List[RepositoryChunk]:
    """Split configuration files on top-level key boundaries."""
    content = document.content
    ext = document.file_path.rsplit(".", 1)[-1].lower() if "." in document.file_path else ""

    pattern: Optional[re.Pattern] = None
    if ext in ("yaml", "yml", "toml", "ini", "cfg"):
        pattern = _YAML_TOP_KEY
    elif ext == "json":
        pattern = _JSON_TOP_KEY

    if pattern:
        matches = list(pattern.finditer(content))
        # Only split if there are multiple top-level keys (otherwise keep as one chunk)
        if len(matches) > 1:
            split_offsets = [m.start() for m in matches]
            return _build_chunks_from_splits(
                document, split_offsets, chunk_size, max_chunks
            )

    return _line_based_chunks(
        document,
        chunk_size=chunk_size,
        overlap=settings.RAG_CHUNK_OVERLAP,
        max_chunks=max_chunks,
    )


class RepositoryChunker:
    """
    Splits RepositoryDocument objects into RepositoryChunk objects using
    structure-aware strategies. Enforces configurable safety limits.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        max_chunks_per_file: Optional[int] = None,
        max_total_chunks: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
        self.max_chunks_per_file = max_chunks_per_file or settings.RAG_MAX_CHUNKS_PER_FILE
        self.max_total_chunks = max_total_chunks or settings.RAG_MAX_TOTAL_CHUNKS

    def chunk_document(self, document: RepositoryDocument) -> List[RepositoryChunk]:
        """Chunk a single document using the appropriate strategy."""
        category = document.category
        language = (document.language or "").lower()
        ext = document.file_path.rsplit(".", 1)[-1].lower() if "." in document.file_path else ""

        if category in ("source", "test"):
            chunks = _chunk_source_code(
                document,
                chunk_size=self.chunk_size,
                max_chunks=self.max_chunks_per_file,
            )
        elif category == "documentation" or ext in ("md", "mdx", "rst", "txt", "adoc"):
            chunks = _chunk_markdown(
                document,
                chunk_size=self.chunk_size,
                max_chunks=self.max_chunks_per_file,
            )
        elif category == "configuration":
            chunks = _chunk_configuration(
                document,
                chunk_size=self.chunk_size,
                max_chunks=self.max_chunks_per_file,
            )
        else:
            chunks = _line_based_chunks(
                document,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap,
                max_chunks=self.max_chunks_per_file,
            )

        if len(chunks) == self.max_chunks_per_file:
            logger.info(
                f"File '{document.file_path}' reached MAX_CHUNKS_PER_FILE "
                f"({self.max_chunks_per_file}) limit."
            )

        return chunks

    def chunk_documents(
        self,
        documents: List[RepositoryDocument],
    ) -> List[RepositoryChunk]:
        """
        Chunk all documents. Enforces max_total_chunks across the repository.
        Returns all chunks sorted by file_path, then chunk_index.
        """
        all_chunks: List[RepositoryChunk] = []
        truncated_files = 0

        for doc in documents:
            if len(all_chunks) >= self.max_total_chunks:
                logger.info(
                    f"Reached RAG_MAX_TOTAL_CHUNKS ({self.max_total_chunks}). "
                    f"Stopping chunking."
                )
                break

            remaining = self.max_total_chunks - len(all_chunks)
            chunks = self.chunk_document(doc)

            if len(chunks) > remaining:
                chunks = chunks[:remaining]
                truncated_files += 1
                logger.info(
                    f"Truncated chunks for '{doc.file_path}' to fit total limit."
                )

            all_chunks.extend(chunks)

        logger.info(
            f"Generated {len(all_chunks)} chunks from {len(documents)} documents "
            f"({truncated_files} files truncated)."
        )

        return all_chunks
