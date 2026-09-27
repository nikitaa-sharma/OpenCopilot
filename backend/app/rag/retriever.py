"""
Deterministic keyword-based retriever for the RAG pipeline.

Scores chunks using multiple lexical signals:
- Exact phrase match in content
- Individual query term matches
- File path segment matches
- Programming identifier matches (camelCase / snake_case splitting)
- Markdown heading matches
- Category relevance boost

No embeddings, no vector search, no external dependencies.
All results are deterministically ordered: score DESC → file_path ASC → chunk_index ASC.
"""

import logging
import re
from typing import List, Tuple

from app.rag.models import RepositoryChunk, RetrievedChunk

logger = logging.getLogger(__name__)

# Category relevance boosts
_CATEGORY_BOOST = {
    "source": 0.5,
    "documentation": 0.4,
    "configuration": 0.2,
    "test": 0.1,
}

# Weights for scoring signals
_W_EXACT_PHRASE = 5.0
_W_TERM_CONTENT = 1.0
_W_TERM_PATH = 3.0
_W_IDENTIFIER = 2.0
_W_HEADING = 2.5

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)", re.MULTILINE)
_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w]")

# Split camelCase: "RepositoryService" → ["repository", "service"]
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace."""
    return _WHITESPACE_RE.sub(" ", text.lower()).strip()


def _split_identifier(term: str) -> List[str]:
    """
    Split a programming identifier into searchable sub-tokens.
    Handles snake_case, camelCase, PascalCase, and kebab-case.
    E.g. "get_user_profile" → ["get", "user", "profile"]
         "RepositoryService" → ["repository", "service"]
         "http-exception" → ["http", "exception"]
    """
    # Split on camelCase / PascalCase boundaries
    camel_parts = _CAMEL_SPLIT_RE.split(term)
    parts: List[str] = []
    for part in camel_parts:
        # Split on snake_case, kebab-case, dots
        sub_parts = re.split(r"[_\-\.]", part)
        parts.extend(p.lower() for p in sub_parts if p)
    return [p for p in parts if len(p) > 1]


def _extract_query_terms(query: str) -> Tuple[str, List[str], List[str]]:
    """
    Parse a query into:
    - normalized_query: full query lowercased
    - terms: individual normalized words
    - identifiers: sub-tokens from identifier splitting
    """
    normalized = _normalize(query)
    # Split into words
    raw_words = _NON_WORD_RE.sub(" ", query).split()
    terms = [w.lower() for w in raw_words if len(w) > 1]

    # Expand each term via identifier splitting
    identifiers: List[str] = []
    for term in raw_words:
        sub = _split_identifier(term)
        identifiers.extend(sub)
    # Deduplicate preserving order
    seen = set()
    unique_identifiers: List[str] = []
    for ident in identifiers:
        if ident not in seen:
            seen.add(ident)
            unique_identifiers.append(ident)

    return normalized, terms, unique_identifiers


def _extract_headings(content: str) -> List[str]:
    """Extract all heading text from Markdown content."""
    return [m.group(1).lower() for m in _HEADING_RE.finditer(content)]


def _score_chunk(
    chunk: RepositoryChunk,
    normalized_query: str,
    terms: List[str],
    identifiers: List[str],
) -> Tuple[float, List[str]]:
    """
    Score a single chunk against a parsed query.

    Returns (score, matched_terms).
    """
    content_lower = _normalize(chunk.content)
    path_lower = chunk.file_path.lower()
    path_parts = re.split(r"[/\\_\-\.]", path_lower)

    score = 0.0
    matched: List[str] = []

    # Signal 1: Exact phrase match in content
    if normalized_query and normalized_query in content_lower:
        score += _W_EXACT_PHRASE
        matched.append(f'exact:"{normalized_query}"')

    # Signal 2: Individual term matches in content
    for term in terms:
        if term in content_lower:
            score += _W_TERM_CONTENT
            if term not in matched:
                matched.append(term)

    # Signal 3: File path segment matches
    for term in terms:
        if any(term == part or term in part for part in path_parts):
            score += _W_TERM_PATH
            path_label = f"path:{term}"
            if path_label not in matched:
                matched.append(path_label)

    # Signal 4: Identifier sub-token matches in content
    for ident in identifiers:
        if ident in content_lower and ident not in [m.split(":", 1)[-1] for m in matched]:
            score += _W_IDENTIFIER
            id_label = f"id:{ident}"
            if id_label not in matched:
                matched.append(id_label)

    # Signal 5: Heading match (for Markdown/documentation)
    if chunk.category == "documentation":
        headings = _extract_headings(chunk.content)
        for term in terms:
            for heading in headings:
                if term in heading:
                    score += _W_HEADING
                    h_label = f"heading:{term}"
                    if h_label not in matched:
                        matched.append(h_label)
                    break

    # Signal 6: Category relevance boost — only applied when there are other matches
    term_score = score  # score before boost
    if term_score > 0:
        score += _CATEGORY_BOOST.get(chunk.category, 0.0)

    return score, matched


def _build_retrieval_reason(matched_terms: List[str], chunk: RepositoryChunk) -> str:
    """Build a human-readable explanation for why this chunk was selected."""
    if not matched_terms:
        return "Category relevance boost only."

    parts = []
    exact = [t for t in matched_terms if t.startswith("exact:")]
    path = [t for t in matched_terms if t.startswith("path:")]
    heading = [t for t in matched_terms if t.startswith("heading:")]
    id_terms = [t for t in matched_terms if t.startswith("id:")]
    regular = [
        t for t in matched_terms
        if not any(t.startswith(p) for p in ("exact:", "path:", "heading:", "id:"))
    ]

    if exact:
        parts.append(f"Exact phrase match in content")
    if regular:
        parts.append(f"Matched query term(s): {', '.join(regular)}")
    if id_terms:
        labels = [t.split(":", 1)[1] for t in id_terms]
        parts.append(f"Matched identifiers: {', '.join(labels)}")
    if path:
        labels = [t.split(":", 1)[1] for t in path]
        parts.append(f"Query term(s) found in file path: {', '.join(labels)}")
    if heading:
        labels = [t.split(":", 1)[1] for t in heading]
        parts.append(f"Matched heading: {', '.join(labels)}")

    return ". ".join(parts) + "."


class KeywordRetriever:
    """
    Deterministic keyword-based chunk retriever.

    Scores chunks using lexical signals without embeddings or external
    search engines. All scoring is deterministic and reproducible.
    """

    def retrieve(
        self,
        query: str,
        chunks: List[RepositoryChunk],
        top_k: int,
    ) -> List[RetrievedChunk]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query: Natural language or code question.
            chunks: All available repository chunks.
            top_k: Maximum number of results to return.

        Returns:
            List of RetrievedChunk sorted by score DESC, file_path ASC, chunk_index ASC.
        """
        if not query or not query.strip():
            logger.debug("Empty query — returning no results.")
            return []

        if not chunks:
            return []

        normalized_query, terms, identifiers = _extract_query_terms(query)

        if not terms:
            return []

        scored: List[Tuple[float, RepositoryChunk, List[str]]] = []

        for chunk in chunks:
            score, matched_terms = _score_chunk(
                chunk, normalized_query, terms, identifiers
            )
            if score > 0:
                scored.append((score, chunk, matched_terms))

        # Deterministic sort: score DESC, file_path ASC, chunk_index ASC
        scored.sort(key=lambda x: (-x[0], x[1].file_path, x[1].chunk_index))

        results: List[RetrievedChunk] = []
        for score, chunk, matched_terms in scored[:top_k]:
            reason = _build_retrieval_reason(matched_terms, chunk)
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=round(score, 4),
                    matched_terms=matched_terms,
                    retrieval_reason=reason,
                )
            )

        logger.debug(
            f"Retrieved {len(results)} chunks from {len(chunks)} for query '{query[:60]}'"
        )

        return results
