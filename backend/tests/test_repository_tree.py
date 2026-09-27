"""
Tests for repository tree retrieval, classification enrichment, and API endpoint.
All external GitHub HTTP calls are mocked via pytest and httpx MockTransport.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.github_service import GitHubService, GitHubNotFoundError, GitHubRateLimitError
from app.services.repository_ingestion_service import RepositoryIngestionService
from app.core.config import settings

client = TestClient(app)

MOCK_TREE_PAYLOAD = {
    "sha": "c0ffee123456",
    "url": "https://api.github.com/repos/pallets/flask/git/trees/c0ffee123456",
    "tree": [
        {
            "path": "src",
            "mode": "040000",
            "type": "tree",
            "sha": "111111",
            "url": "https://api.github.com/repos/pallets/flask/git/trees/111111",
        },
        {
            "path": "src/flask",
            "mode": "040000",
            "type": "tree",
            "sha": "222222",
            "url": "https://api.github.com/repos/pallets/flask/git/trees/222222",
        },
        {
            "path": "src/flask/app.py",
            "mode": "100644",
            "type": "blob",
            "sha": "333333",
            "size": 45000,
            "url": "https://api.github.com/repos/pallets/flask/git/blobs/333333",
        },
        {
            "path": "tests",
            "mode": "040000",
            "type": "tree",
            "sha": "444444",
            "url": "https://api.github.com/repos/pallets/flask/git/trees/444444",
        },
        {
            "path": "tests/test_basic.py",
            "mode": "100644",
            "type": "blob",
            "sha": "555555",
            "size": 1200,
            "url": "https://api.github.com/repos/pallets/flask/git/blobs/555555",
        },
        {
            "path": "README.md",
            "mode": "100644",
            "type": "blob",
            "sha": "666666",
            "size": 3500,
            "url": "https://api.github.com/repos/pallets/flask/git/blobs/666666",
        },
        {
            "path": "assets/logo.png",
            "mode": "100644",
            "type": "blob",
            "sha": "777777",
            "size": 89000,
            "url": "https://api.github.com/repos/pallets/flask/git/blobs/777777",
        },
    ],
    "truncated": False,
}


@pytest.mark.asyncio
async def test_fetch_tree_success():
    def handler(request: httpx.Request):
        assert "/git/trees/main" in str(request.url)
        assert request.url.params.get("recursive") == "1"
        return httpx.Response(200, json=MOCK_TREE_PAYLOAD)

    transport = httpx.MockTransport(handler)
    service = GitHubService(base_url="https://api.github.com")

    # Monkeypatch transport in httpx.AsyncClient
    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        result = await service.fetch_tree("pallets", "flask", branch="main")
        assert result["branch"] == "main"
        assert result["truncated"] is False
        assert len(result["tree"]) == 7

        # Verify type normalization
        dirs = [item for item in result["tree"] if item["type"] == "directory"]
        files = [item for item in result["tree"] if item["type"] == "file"]
        assert len(dirs) == 3
        assert len(files) == 4
        assert files[0]["path"] == "src/flask/app.py"
        assert files[0]["size"] == 45000
    finally:
        httpx.AsyncClient.__init__ = original_init


@pytest.mark.asyncio
async def test_fetch_tree_404_not_found():
    def handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    service = GitHubService(base_url="https://api.github.com")

    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        with pytest.raises(GitHubNotFoundError):
            await service.fetch_tree("nonexistent", "repo", branch="main")
    finally:
        httpx.AsyncClient.__init__ = original_init


@pytest.mark.asyncio
async def test_ingestion_service_tree_enrichment():
    def handler(request: httpx.Request):
        return httpx.Response(200, json=MOCK_TREE_PAYLOAD)

    transport = httpx.MockTransport(handler)
    gh_service = GitHubService(base_url="https://api.github.com")

    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        ingestion_service = RepositoryIngestionService(service=gh_service)
        result = await ingestion_service.get_repository_tree("pallets", "flask", branch="main")

        assert result["repository"] == "pallets/flask"
        assert result["branch"] == "main"
        assert result["total_items"] == 7

        # Check classification and language enrichment
        by_path = {item["path"]: item for item in result["tree"]}
        assert by_path["src/flask/app.py"]["category"] == "source"
        assert by_path["src/flask/app.py"]["language"] == "Python"
        assert by_path["tests/test_basic.py"]["category"] == "test"
        assert by_path["README.md"]["category"] == "documentation"
        assert by_path["assets/logo.png"]["category"] == "binary_or_unsupported"
        assert by_path["src"]["category"] is None
    finally:
        httpx.AsyncClient.__init__ = original_init


def test_endpoint_get_repository_tree_success():
    def handler(request: httpx.Request):
        return httpx.Response(200, json=MOCK_TREE_PAYLOAD)

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        response = client.get("/api/v1/repositories/pallets/flask/tree?branch=main")
        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "pallets/flask"
        assert data["branch"] == "main"
        assert data["total_items"] == 7
        assert len(data["tree"]) == 7
    finally:
        httpx.AsyncClient.__init__ = original_init
