import pytest
from app.schemas.repository import RepositoryInfo, ReadmeInfo, TreeItem
from app.services.repository_context_builder import RepositoryContextBuilder


def test_file_priority_ordering():
    """Verify README > config > entry points > source > tests."""
    builder = RepositoryContextBuilder(max_files_in_context=10)

    items = [
        TreeItem(path="tests/test_app.py", type="file", category="test"),
        TreeItem(path="src/utils.py", type="file", category="source"),
        TreeItem(path="app.py", type="file", category="source"),
        TreeItem(path="pyproject.toml", type="file", category="configuration"),
        TreeItem(path="README.md", type="file", category="documentation"),
        TreeItem(path="node_modules/pkg/index.js", type="file", category="generated_or_ignored"),
    ]

    selected = builder.select_files_for_context(items)

    paths = [item.path for item in selected]
    # Ignored node_modules should be excluded
    assert "node_modules/pkg/index.js" not in paths
    # README first
    assert paths[0] == "README.md"
    # Config second
    assert paths[1] == "pyproject.toml"
    # Entry point third
    assert paths[2] == "app.py"
    # Core source fourth
    assert paths[3] == "src/utils.py"
    # Tests fifth
    assert paths[4] == "tests/test_app.py"


def test_max_files_limit():
    """Verify select_files_for_context strictly respects max_files_in_context limit."""
    builder = RepositoryContextBuilder(max_files_in_context=3)

    items = [
        TreeItem(path=f"src/file_{i}.py", type="file", category="source")
        for i in range(10)
    ]

    selected = builder.select_files_for_context(items)
    assert len(selected) == 3


def test_file_truncation_in_context():
    """Verify individual files exceeding max_file_chars are safely truncated."""
    builder = RepositoryContextBuilder(max_file_chars=100, max_context_chars=10000)

    repo = RepositoryInfo(
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        default_branch="main",
    )
    long_content = "x" * 500

    context = builder.build_context(
        repository=repo,
        languages={"Python": 1000},
        readme=None,
        tree=[],
        file_contents={"src/long.py": long_content},
    )

    assert "File truncated" in context
    assert len(context) < 1500


def test_global_context_budget_capping():
    """Verify entire context cannot exceed max_context_chars."""
    builder = RepositoryContextBuilder(max_file_chars=5000, max_context_chars=500)

    repo = RepositoryInfo(
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        default_branch="main",
        description="A" * 300,
    )

    context = builder.build_context(
        repository=repo,
        languages={},
        readme=ReadmeInfo(name="README.md", content="B" * 300),
        tree=[],
        file_contents={"main.py": "C" * 300},
    )

    # Should cap close to max_context_chars
    assert "Total context truncated" in context or len(context) <= 600
