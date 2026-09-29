"""
Pytest configuration and global fixtures for backend test suite.
"""

import pytest
from app.services.github_service import github_service


@pytest.fixture(autouse=True)
def clear_github_cache():
    """Ensure in-memory GitHub cache is isolated between tests."""
    github_service.clear_cache()
    yield
    github_service.clear_cache()
