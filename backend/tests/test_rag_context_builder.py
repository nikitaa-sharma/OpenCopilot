"""
Tests for the RAGContextBuilder.
"""

import pytest
from app.rag.context import RAGContextBuilder, _TRUNCATION_NOTICE
from app.rag.models import RepositoryChunk, RetrievedChunk


def _make_retrieved_chunk(
    content: str,
    file_path: str = "src/app.py",
    language: str = "Python",
    start_line: int = 1,
    end_line: int = 10,
    score: float = 5.0,
) -> RetrievedChunk:
    chunk = RepositoryChunk(
        chunk_id=f"pallets/flask:{file_path}:0",
        repository="pallets/flask",
        file_path=file_path,
        language=language,
        category="source",
        chunk_index=0,
        start_line=start_line,
        end_line=end_line,
        content=content,
        metadata={},
    )
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        matched_terms=["flask"],
        retrieval_reason="Matched flask in content.",
    )


@pytest.fixture
def builder():
    return RAGContextBuilder(max_context_chars=5000)


def test_file_path_included_in_context(builder):
    """Context output includes the file path."""
    rc = _make_retrieved_chunk("def create_app():\n    pass", file_path="src/flask/app.py")
    context = builder.build_context([rc])
    assert "src/flask/app.py" in context


def test_line_ranges_included(builder):
    """Context output includes the line range."""
    rc = _make_retrieved_chunk("x = 1", start_line=20, end_line=25)
    context = builder.build_context([rc])
    assert "20" in context
    assert "25" in context


def test_chunk_content_in_context(builder):
    """The actual chunk content is present in the output."""
    rc = _make_retrieved_chunk("def create_app():\n    return Flask(__name__)")
    context = builder.build_context([rc])
    assert "def create_app" in context
    assert "Flask" in context


def test_language_in_context(builder):
    """The language label is present in the context block."""
    rc = _make_retrieved_chunk("x = 1", language="Python")
    context = builder.build_context([rc])
    assert "Python" in context


def test_chunk_boundaries_preserved(builder):
    """Multiple chunks each have their own file/language/lines header."""
    chunks = [
        _make_retrieved_chunk("def f1():\n    pass", file_path="src/a.py", start_line=1, end_line=2),
        _make_retrieved_chunk("def f2():\n    pass", file_path="src/b.py", start_line=10, end_line=12),
    ]
    context = builder.build_context(chunks)
    assert "src/a.py" in context
    assert "src/b.py" in context
    assert "def f1" in context
    assert "def f2" in context


def test_context_size_limit_respected():
    """Context output does not exceed max_context_chars."""
    builder = RAGContextBuilder(max_context_chars=200)
    # Create many large chunks that would exceed the limit
    large_chunks = [
        _make_retrieved_chunk(
            "x = " + "a" * 100, file_path=f"src/file{i}.py", score=float(10 - i)
        )
        for i in range(10)
    ]
    context = builder.build_context(large_chunks)
    assert len(context) <= 200 + len(_TRUNCATION_NOTICE) + 50  # allow some buffer for headers


def test_truncation_notice_added_when_exceeded():
    """A truncation notice is added when the context limit is hit."""
    builder = RAGContextBuilder(max_context_chars=100)
    large_chunks = [
        _make_retrieved_chunk("x = " + "a" * 200, file_path=f"src/file{i}.py")
        for i in range(3)
    ]
    context = builder.build_context(large_chunks)
    assert "truncated" in context.lower()


def test_empty_chunks_returns_no_context_message(builder):
    """Empty retrieved_chunks produces a no-context placeholder."""
    context = builder.build_context([])
    assert "No relevant repository context found" in context


def test_context_has_repository_header(builder):
    """Context starts with a 'Repository Context' header."""
    rc = _make_retrieved_chunk("def f():\n    pass")
    context = builder.build_context([rc])
    assert "Repository Context" in context
