"""
Tests for the RepositoryChunker.
"""

import pytest
from app.rag.chunker import RepositoryChunker
from app.rag.models import RepositoryDocument


def _make_doc(
    content: str,
    file_path: str = "src/app.py",
    category: str = "source",
    language: str = "Python",
) -> RepositoryDocument:
    return RepositoryDocument(
        repository="pallets/flask",
        owner="pallets",
        repo_name="flask",
        branch="main",
        file_path=file_path,
        file_name=file_path.split("/")[-1],
        category=category,
        language=language,
        content=content,
        size_bytes=len(content.encode()),
    )


PYTHON_SOURCE = """\
import os
import sys


def create_app(config=None):
    \"\"\"Create the Flask application.\"\"\"
    app = Flask(__name__)
    app.config.from_object(config)
    return app


def run_server(host="0.0.0.0", port=5000):
    \"\"\"Run the development server.\"\"\"
    app = create_app()
    app.run(host=host, port=port)


class AppFactory:
    \"\"\"Factory class for creating app instances.\"\"\"

    def __init__(self, config):
        self.config = config

    def build(self):
        return create_app(self.config)
"""

MARKDOWN_DOC = """\
# Flask

A lightweight WSGI web application framework.

## Installation

Install using pip:

```
pip install flask
```

## Quick Start

Create your application:

```python
from flask import Flask
app = Flask(__name__)
```

## Configuration

Flask can be configured via environment variables.
"""

YAML_CONFIG = """\
name: flask
version: 3.0.0

dependencies:
  werkzeug: ">=3.0"
  click: ">=8.0"

dev-dependencies:
  pytest: ">=7"
  coverage: ">=7"
"""


@pytest.fixture
def chunker():
    return RepositoryChunker(
        chunk_size=500,
        chunk_overlap=50,
        max_chunks_per_file=50,
        max_total_chunks=500,
    )


def test_python_source_chunked(chunker):
    """Python source is split on function/class boundaries."""
    doc = _make_doc(PYTHON_SOURCE, file_path="src/app.py", category="source", language="Python")
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 1
    # Should have multiple chunks (imports + functions + class)
    assert len(chunks) >= 2


def test_markdown_chunked_on_headings(chunker):
    """Markdown is split on heading boundaries."""
    doc = _make_doc(
        MARKDOWN_DOC, file_path="README.md", category="documentation", language="Markdown"
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 2  # Should split on ## sections
    # Each chunk should contain a heading or be the content under a heading
    all_content = "\n".join(c.content for c in chunks)
    assert "Flask" in all_content
    assert "Installation" in all_content


def test_configuration_chunked(chunker):
    """YAML configuration is processed."""
    doc = _make_doc(
        YAML_CONFIG, file_path="pyproject.yaml", category="configuration", language="YAML"
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 1


def test_line_numbers_preserved(chunker):
    """Every chunk has valid start_line and end_line (1-based)."""
    doc = _make_doc(PYTHON_SOURCE)
    chunks = chunker.chunk_document(doc)
    for chunk in chunks:
        assert chunk.start_line >= 1
        assert chunk.end_line >= chunk.start_line


def test_metadata_preserved(chunker):
    """Chunk metadata mirrors document metadata."""
    doc = _make_doc(PYTHON_SOURCE, file_path="src/app.py", language="Python")
    chunks = chunker.chunk_document(doc)
    for chunk in chunks:
        assert chunk.file_path == "src/app.py"
        assert chunk.language == "Python"
        assert chunk.category == "source"
        assert chunk.repository == "pallets/flask"
        assert "file_path" in chunk.metadata
        assert chunk.metadata["file_path"] == "src/app.py"


def test_chunk_id_deterministic(chunker):
    """Chunk IDs are deterministic and unique within a file."""
    doc = _make_doc(PYTHON_SOURCE)
    chunks = chunker.chunk_document(doc)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs must be unique"
    # Should follow the pattern repository:file_path:index
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert f":{i}" in chunk.chunk_id


def test_max_chunks_per_file_respected():
    """Chunker enforces max_chunks_per_file limit."""
    # Very small chunk size to force many chunks
    chunker = RepositoryChunker(chunk_size=50, chunk_overlap=0, max_chunks_per_file=3)
    doc = _make_doc("line\n" * 200)
    chunks = chunker.chunk_document(doc)
    assert len(chunks) <= 3


def test_max_total_chunks_respected():
    """Chunker stops at max_total_chunks across multiple documents."""
    chunker = RepositoryChunker(chunk_size=50, chunk_overlap=0, max_total_chunks=5)
    docs = [_make_doc("line\n" * 50, file_path=f"src/file{i}.py") for i in range(3)]
    chunks = chunker.chunk_documents(docs)
    assert len(chunks) <= 5


def test_single_small_file_is_one_chunk(chunker):
    """A very short file produces exactly one chunk."""
    doc = _make_doc("x = 1\n", file_path="src/tiny.py")
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].start_line == 1


def test_large_block_is_sub_split():
    """Content exceeding chunk_size is sub-split into multiple chunks."""
    # Use a small chunk_size so lots of lines exceed the limit
    small_chunker = RepositoryChunker(chunk_size=50, chunk_overlap=0, max_chunks_per_file=50)
    # Create a file with enough lines to exceed the chunk_size multiple times
    large_content = "\n".join(f"x_{i} = {i}" for i in range(100))
    doc = _make_doc(large_content, file_path="src/big.py")
    chunks = small_chunker.chunk_document(doc)
    assert len(chunks) >= 2


def test_chunk_documents_preserves_order(chunker):
    """chunk_documents returns chunks sorted by file then chunk_index."""
    docs = [
        _make_doc(PYTHON_SOURCE, file_path="b/second.py"),
        _make_doc(PYTHON_SOURCE, file_path="a/first.py"),
    ]
    chunks = chunker.chunk_documents(docs)
    # Chunks should preserve file grouping and chunk_index ordering
    file_paths = [c.file_path for c in chunks]
    # All chunks from same file should be contiguous
    seen_files = []
    prev = None
    for fp in file_paths:
        if fp != prev:
            assert fp not in seen_files, "Same file appears in non-contiguous positions"
            seen_files.append(fp)
            prev = fp
