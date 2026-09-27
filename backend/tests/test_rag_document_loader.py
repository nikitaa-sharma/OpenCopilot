"""
Tests for the RAG DocumentLoader.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.document_loader import DocumentLoader, SUPPORTED_CATEGORIES


def _make_ingestion_result(files):
    return {
        "repository": {"owner": "pallets", "name": "flask", "branch": "main"},
        "statistics": {},
        "files": files,
    }


def _make_file(
    path="src/app.py",
    content="def create_app():\n    return Flask(__name__)",
    category="source",
    language="Python",
    is_binary=False,
    skip_reason=None,
    sha="abc123",
):
    return {
        "path": path,
        "name": path.split("/")[-1],
        "content": content,
        "category": category,
        "language": language,
        "is_binary": is_binary,
        "skip_reason": skip_reason,
        "sha": sha,
        "size": len(content.encode()) if content else 0,
    }


@pytest.fixture
def mock_ingestion_service():
    svc = MagicMock()
    svc.ingest_repository = AsyncMock()
    return svc


@pytest.fixture
def loader(mock_ingestion_service):
    return DocumentLoader(ingestion_service=mock_ingestion_service)


@pytest.mark.asyncio
async def test_source_files_loaded(loader, mock_ingestion_service):
    """Source files with content are loaded as RepositoryDocument."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="src/app.py", category="source"),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 1
    assert docs[0].file_path == "src/app.py"
    assert docs[0].category == "source"
    assert docs[0].repository == "pallets/flask"
    assert stats.documents_loaded == 1
    assert stats.documents_skipped == 0


@pytest.mark.asyncio
async def test_documentation_files_included(loader, mock_ingestion_service):
    """Documentation files (.md, .rst) are loaded."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="README.md", content="# Flask\nA micro web framework.", category="documentation", language="Markdown"),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 1
    assert docs[0].category == "documentation"


@pytest.mark.asyncio
async def test_binary_files_excluded(loader, mock_ingestion_service):
    """Binary files are skipped."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="logo.png", category="binary_or_unsupported", is_binary=True, content=None),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 0
    assert stats.documents_skipped == 1


@pytest.mark.asyncio
async def test_files_with_skip_reason_excluded(loader, mock_ingestion_service):
    """Files with a skip_reason (e.g. fetch failure) are skipped."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="src/big.py", skip_reason="File too large"),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 0
    assert stats.documents_skipped == 1


@pytest.mark.asyncio
async def test_generated_ignored_files_excluded(loader, mock_ingestion_service):
    """Generated/ignored files (e.g. node_modules) are excluded."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="node_modules/lodash/index.js", category="generated_or_ignored"),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 0
    assert stats.documents_skipped == 1


@pytest.mark.asyncio
async def test_empty_content_files_excluded(loader, mock_ingestion_service):
    """Files with empty or whitespace-only content are skipped."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="src/empty.py", content="   \n  "),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 0
    assert stats.documents_skipped == 1


@pytest.mark.asyncio
async def test_multiple_files_mixed(loader, mock_ingestion_service):
    """Mix of valid and invalid files returns only valid documents."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="src/app.py", category="source"),
        _make_file(path="README.md", category="documentation", language="Markdown"),
        _make_file(path="logo.png", category="binary_or_unsupported", is_binary=True, content=None),
        _make_file(path="src/broken.py", skip_reason="Fetch failed"),
    ])
    docs, stats = await loader.load_documents("https://github.com/pallets/flask")
    assert len(docs) == 2
    assert stats.documents_loaded == 2
    assert stats.documents_skipped == 2


@pytest.mark.asyncio
async def test_document_metadata_preserved(loader, mock_ingestion_service):
    """All metadata fields are correctly populated on the RepositoryDocument."""
    mock_ingestion_service.ingest_repository.return_value = _make_ingestion_result([
        _make_file(path="src/app.py", category="source", language="Python", sha="abc123"),
    ])
    docs, _ = await loader.load_documents("https://github.com/pallets/flask", branch="3.x")
    doc = docs[0]
    assert doc.owner == "pallets"
    assert doc.repo_name == "flask"
    assert doc.branch == "main"  # from ingestion result, not passed branch
    assert doc.language == "Python"
    assert doc.sha == "abc123"
    assert doc.size_bytes > 0
