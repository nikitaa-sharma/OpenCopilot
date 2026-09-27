"""
Tests for file content retrieval, safety limits, batch ingestion, and API endpoints.
All external GitHub HTTP calls are mocked via pytest and httpx MockTransport.
"""

import base64
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.github_service import GitHubService, GitHubNotFoundError
from app.services.repository_ingestion_service import RepositoryIngestionService
from app.core.config import settings

client = TestClient(app)

SAMPLE_CODE = "from flask import Flask\napp = Flask(__name__)\n"
SAMPLE_CODE_B64 = base64.b64encode(SAMPLE_CODE.encode("utf-8")).decode("ascii")


@pytest.mark.asyncio
async def test_fetch_file_content_valid_base64():
    mock_payload = {
        "name": "app.py",
        "path": "src/app.py",
        "sha": "abc1234",
        "size": len(SAMPLE_CODE),
        "type": "file",
        "content": SAMPLE_CODE_B64,
        "encoding": "base64",
    }

    def handler(request: httpx.Request):
        assert "/contents/src/app.py" in str(request.url)
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    service = GitHubService(base_url="https://api.github.com")

    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        result = await service.fetch_file_content("pallets", "flask", "src/app.py", branch="main")
        assert result["path"] == "src/app.py"
        assert result["content"] == SAMPLE_CODE
        assert result["is_binary"] is False
        assert result["skip_reason"] is None
    finally:
        httpx.AsyncClient.__init__ = original_init


@pytest.mark.asyncio
async def test_fetch_file_content_oversized():
    huge_size = settings.MAX_FILE_SIZE_BYTES + 5000
    mock_payload = {
        "name": "huge.py",
        "path": "src/huge.py",
        "sha": "huge123",
        "size": huge_size,
        "type": "file",
        "content": "some_content",
        "encoding": "base64",
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    service = GitHubService(base_url="https://api.github.com")

    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        result = await service.fetch_file_content("pallets", "flask", "src/huge.py")
        assert result["content"] is None
        assert "exceeds maximum limit" in result["skip_reason"]
    finally:
        httpx.AsyncClient.__init__ = original_init


@pytest.mark.asyncio
async def test_fetch_file_content_binary():
    # Null bytes indicate binary
    binary_data = b"\x00\x01\x02\x03\xff"
    binary_b64 = base64.b64encode(binary_data).decode("ascii")

    mock_payload = {
        "name": "image.png",
        "path": "assets/image.png",
        "sha": "bin123",
        "size": len(binary_data),
        "type": "file",
        "content": binary_b64,
        "encoding": "base64",
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    service = GitHubService(base_url="https://api.github.com")

    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        result = await service.fetch_file_content("pallets", "flask", "assets/image.png")
        assert result["content"] is None
        assert result["is_binary"] is True
        assert "Binary file detected" in result["skip_reason"]
    finally:
        httpx.AsyncClient.__init__ = original_init


def test_endpoint_get_file_content_success():
    mock_payload = {
        "name": "app.py",
        "path": "src/flask/app.py",
        "sha": "abc1234",
        "size": len(SAMPLE_CODE),
        "type": "file",
        "content": SAMPLE_CODE_B64,
        "encoding": "base64",
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        response = client.get("/api/v1/repositories/pallets/flask/files/src/flask/app.py?branch=main")
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "src/flask/app.py"
        assert data["language"] == "Python"
        assert data["category"] == "source"
        assert data["content"] == SAMPLE_CODE
        assert data["is_binary"] is False
    finally:
        httpx.AsyncClient.__init__ = original_init


def test_endpoint_get_file_content_not_found():
    def handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        response = client.get("/api/v1/repositories/pallets/flask/files/nonexistent.py")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        httpx.AsyncClient.__init__ = original_init


def test_endpoint_ingest_repository_success():
    tree_mock = {
        "sha": "tree123",
        "tree": [
            {"path": "src", "type": "tree", "sha": "t1"},
            {"path": "src/app.py", "type": "blob", "sha": "b1", "size": len(SAMPLE_CODE)},
            {"path": "assets/logo.png", "type": "blob", "sha": "b2", "size": 500},
            {"path": "node_modules/pkg/index.js", "type": "blob", "sha": "b3", "size": 100},
        ],
        "truncated": False,
    }

    file_mock = {
        "name": "app.py",
        "path": "src/app.py",
        "sha": "b1",
        "size": len(SAMPLE_CODE),
        "type": "file",
        "content": SAMPLE_CODE_B64,
        "encoding": "base64",
    }

    repo_mock = {
        "id": 1234,
        "owner": {"login": "pallets"},
        "name": "flask",
        "full_name": "pallets/flask",
        "default_branch": "main",
    }

    def handler(request: httpx.Request):
        url_str = str(request.url)
        if "/git/trees/" in url_str:
            return httpx.Response(200, json=tree_mock)
        elif "/contents/" in url_str:
            return httpx.Response(200, json=file_mock)
        elif "/repos/pallets/flask" in url_str:
            return httpx.Response(200, json=repo_mock)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def mock_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init
    try:
        response = client.post(
            "/api/v1/repositories/ingest",
            json={"url": "https://github.com/pallets/flask", "branch": "main"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["repository"]["owner"] == "pallets"
        assert data["repository"]["name"] == "flask"
        assert data["repository"]["branch"] == "main"

        stats = data["statistics"]
        assert stats["total_tree_items"] == 4
        assert stats["directories"] == 1
        assert stats["files"] == 3
        # Only src/app.py is selected (logo.png is binary, node_modules is ignored)
        assert stats["selected_files"] == 1
        assert stats["skipped_files"] == 2

        assert len(data["files"]) == 1
        assert data["files"][0]["path"] == "src/app.py"
        assert data["files"][0]["content"] == SAMPLE_CODE
    finally:
        httpx.AsyncClient.__init__ = original_init
