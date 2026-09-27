"""
Tests for the KeywordRetriever.
"""

import pytest
from app.rag.models import RepositoryChunk
from app.rag.retriever import KeywordRetriever


def _make_chunk(
    content: str,
    file_path: str = "src/app.py",
    category: str = "source",
    language: str = "Python",
    chunk_index: int = 0,
    start_line: int = 1,
    end_line: int = 10,
) -> RepositoryChunk:
    return RepositoryChunk(
        chunk_id=f"pallets/flask:{file_path}:{chunk_index}",
        repository="pallets/flask",
        file_path=file_path,
        language=language,
        category=category,
        chunk_index=chunk_index,
        start_line=start_line,
        end_line=end_line,
        content=content,
        metadata={},
    )


@pytest.fixture
def retriever():
    return KeywordRetriever()


@pytest.fixture
def flask_chunks():
    return [
        _make_chunk(
            content="class Flask:\n    def __init__(self, name):\n        self.name = name",
            file_path="src/flask/app.py",
        ),
        _make_chunk(
            content="def create_app(config=None):\n    app = Flask(__name__)\n    return app",
            file_path="src/flask/app.py",
            chunk_index=1,
        ),
        _make_chunk(
            content="class Blueprint:\n    def route(self, path):\n        pass",
            file_path="src/flask/blueprints.py",
        ),
        _make_chunk(
            content="# Database connection\ndef get_db():\n    return db.connect()",
            file_path="src/flask/db.py",
        ),
        _make_chunk(
            content="# Installation\npip install flask\n\n## Quick start",
            file_path="README.md",
            category="documentation",
            language="Markdown",
        ),
    ]


def test_relevant_chunks_rank_higher(retriever, flask_chunks):
    """Chunks containing query terms rank higher than unrelated ones."""
    results = retriever.retrieve("Flask application class", flask_chunks, top_k=5)
    assert len(results) > 0
    top_files = [r.chunk.file_path for r in results[:2]]
    # Flask app.py should rank high as it contains Flask class
    assert any("app.py" in f for f in top_files)


def test_exact_identifier_match_works(retriever):
    """Exact identifier matches (like function names) are found."""
    chunks = [
        _make_chunk("def get_user(user_id):\n    return db.find(user_id)", file_path="src/users.py"),
        _make_chunk("def send_email(to, subject):\n    smtp.send(to)", file_path="src/email.py"),
    ]
    results = retriever.retrieve("get_user", chunks, top_k=5)
    assert len(results) > 0
    assert results[0].chunk.file_path == "src/users.py"


def test_snake_case_identifier_splitting(retriever):
    """snake_case identifiers are split and each sub-token is searchable."""
    chunks = [
        _make_chunk("class RepositoryService:\n    pass", file_path="src/service.py"),
        _make_chunk("x = 1", file_path="src/other.py"),
    ]
    # "repository_service" should match RepositoryService via identifier splitting
    results = retriever.retrieve("repository_service", chunks, top_k=5)
    assert len(results) > 0
    assert results[0].chunk.file_path == "src/service.py"


def test_camelcase_identifier_splitting(retriever):
    """CamelCase queries are split into sub-tokens for matching."""
    chunks = [
        _make_chunk("class HTTPException:\n    pass", file_path="src/exceptions.py"),
        _make_chunk("class User:\n    pass", file_path="src/models.py"),
    ]
    results = retriever.retrieve("HTTPException", chunks, top_k=5)
    assert len(results) > 0
    assert results[0].chunk.file_path == "src/exceptions.py"


def test_file_path_match_boosts_score(retriever):
    """Query terms matching path segments boost the score."""
    chunks = [
        _make_chunk("def authenticate(user):\n    pass", file_path="src/auth/service.py"),
        _make_chunk("def authenticate(user):\n    pass", file_path="src/other/service.py"),
    ]
    results = retriever.retrieve("authenticate auth service", chunks, top_k=5)
    assert len(results) >= 1
    # The auth path should rank first due to path boost
    assert results[0].chunk.file_path == "src/auth/service.py"


def test_deterministic_ordering_equal_scores(retriever):
    """When scores are equal, ordering is file_path ASC then chunk_index ASC."""
    chunks = [
        _make_chunk("flask app", file_path="z/last.py", chunk_index=0),
        _make_chunk("flask app", file_path="a/first.py", chunk_index=0),
        _make_chunk("flask app", file_path="a/first.py", chunk_index=1),
    ]
    results = retriever.retrieve("flask app", chunks, top_k=5)
    files = [r.chunk.file_path for r in results]
    # a/first.py should come before z/last.py (alphabetical when equal score)
    assert files.index("a/first.py") < files.index("z/last.py")
    # Within same file, chunk 0 before chunk 1
    a_indices = [r.chunk.chunk_index for r in results if r.chunk.file_path == "a/first.py"]
    assert a_indices == sorted(a_indices)


def test_top_k_respected(retriever, flask_chunks):
    """Retriever returns at most top_k results."""
    results = retriever.retrieve("Flask application", flask_chunks, top_k=2)
    assert len(results) <= 2


def test_empty_query_returns_empty(retriever, flask_chunks):
    """Empty query returns an empty result list."""
    results = retriever.retrieve("", flask_chunks, top_k=5)
    assert results == []


def test_whitespace_only_query_returns_empty(retriever, flask_chunks):
    """Whitespace-only query returns empty results."""
    results = retriever.retrieve("   ", flask_chunks, top_k=5)
    assert results == []


def test_no_match_returns_empty(retriever):
    """Query with no matching chunks returns empty list."""
    chunks = [_make_chunk("def create_app():\n    pass")]
    results = retriever.retrieve("xyzzy_nonexistent_term_12345", chunks, top_k=5)
    assert results == []


def test_matched_terms_populated(retriever):
    """matched_terms contains the terms that were found."""
    chunks = [_make_chunk("def get_user(user_id):\n    return db.find(user_id)")]
    results = retriever.retrieve("get_user database", chunks, top_k=5)
    assert len(results) > 0
    assert any("get" in t or "user" in t or "get_user" in t for t in results[0].matched_terms)


def test_retrieval_reason_populated(retriever):
    """retrieval_reason is a non-empty human-readable string."""
    chunks = [_make_chunk("def create_app():\n    app = Flask(__name__)\n    return app")]
    results = retriever.retrieve("Flask application", chunks, top_k=5)
    assert len(results) > 0
    assert len(results[0].retrieval_reason) > 0
    assert results[0].retrieval_reason.endswith(".")


def test_score_is_positive(retriever):
    """All returned chunks have a positive score."""
    chunks = [_make_chunk("def create_app():\n    return Flask(__name__)")]
    results = retriever.retrieve("Flask", chunks, top_k=5)
    for r in results:
        assert r.score > 0


def test_github_api_query(retriever):
    """Query about 'GitHub API' finds relevant chunks."""
    chunks = [
        _make_chunk("def fetch_repository(owner, repo):\n    return github_api.get(owner, repo)",
                    file_path="src/github_service.py"),
        _make_chunk("class FlaskApp:\n    def run(self):\n        pass",
                    file_path="src/app.py"),
    ]
    results = retriever.retrieve("GitHub API repository", chunks, top_k=5)
    assert len(results) > 0
    assert results[0].chunk.file_path == "src/github_service.py"
