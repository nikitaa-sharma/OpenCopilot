"""
RAG context builder for the RAG pipeline.

Converts retrieved chunks into a bounded, structured text block suitable
for use as LLM context in future phases. Enforces character limits and
produces explicit truncation notices.
"""

import logging
from typing import List

from app.core.config import settings
from app.rag.models import RetrievedChunk

logger = logging.getLogger(__name__)

_CHUNK_SEPARATOR = "\n---\n\n"
_TRUNCATION_NOTICE = "\n[Context truncated: character limit reached. Additional relevant chunks exist.]\n"


class RAGContextBuilder:
    """
    Converts retrieved chunks into bounded LLM-ready context.

    Format:
        File: src/example.py
        Language: Python
        Lines: 20-48

        <chunk content>

        ---

    Enforces RAG_MAX_CONTEXT_CHARS. Adds explicit truncation notice when budget exceeded.
    """

    def __init__(self, max_context_chars: int | None = None):
        self.max_context_chars = max_context_chars or settings.RAG_MAX_CONTEXT_CHARS

    def build_context(
        self,
        retrieved_chunks: List[RetrievedChunk],
        max_chars: int | None = None,
    ) -> str:
        """
        Build a formatted context string from retrieved chunks.

        Args:
            retrieved_chunks: Ordered list of RetrievedChunk objects.
            max_chars: Optional override for context character limit.

        Returns:
            Formatted context string, truncated if necessary.
        """
        limit = max_chars or self.max_context_chars

        if not retrieved_chunks:
            return "[No relevant repository context found for this query.]\n"

        parts: List[str] = []
        total_chars = 0
        included = 0
        truncated = False

        header = "Repository Context\n" + "=" * 60 + "\n\n"
        total_chars += len(header)

        for rc in retrieved_chunks:
            chunk = rc.chunk

            block_header = (
                f"File: {chunk.file_path}\n"
                f"Language: {chunk.language or 'Unknown'}\n"
                f"Lines: {chunk.start_line}-{chunk.end_line}\n\n"
            )
            block_content = chunk.content
            block = block_header + block_content + _CHUNK_SEPARATOR

            if total_chars + len(block) > limit:
                # Try to fit a truncated version of the content
                remaining = limit - total_chars - len(block_header) - len(_CHUNK_SEPARATOR) - len(_TRUNCATION_NOTICE) - 10
                if remaining > 100:
                    truncated_content = block_content[:remaining] + "\n[... truncated ...]\n"
                    block = block_header + truncated_content + _CHUNK_SEPARATOR
                    parts.append(block)
                    included += 1
                truncated = True
                break

            parts.append(block)
            total_chars += len(block)
            included += 1

        result = header + "".join(parts)
        if truncated:
            result += _TRUNCATION_NOTICE

        logger.debug(
            f"Built RAG context: {included}/{len(retrieved_chunks)} chunks, "
            f"{len(result)} chars (limit: {limit})"
        )

        return result
