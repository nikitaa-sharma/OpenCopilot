from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.github_service import (
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubServiceError,
)


@pytest.fixture
def mock_analysis_data():
    return {
        "repository": {
            "id": 12345,
            "owner": "pallets",
            "name": "flask",
            "full_name": "pallets/flask",
            "description": "The Python micro framework for building web applications.",
            "html_url": "https://github.com/pallets/flask",
            "default_branch": "main",
            "visibility": "public",
            "language": "Python",
            "license": {"key": "bsd-3-clause", "name": "BSD 3-Clause License", "spdx_id": "BSD-3-Clause"},
            "stars": 65000,
            "forks": 16000,
            "watchers": 65000,
            "open_issues_count": 15,
            "topics": ["python", "flask", "wsgi", "web-framework"],
            "created_at": "2010-04-06T11:11:59Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-02T00:00:00Z",
        },
        "languages": {
            "Python": 800000,
            "HTML": 5000,
        },
        "readme": {
            "name": "README.md",
            "content": "# Flask\nFlask is a lightweight WSGI web application framework.",
            "html_url": "https://github.com/pallets/flask/blob/main/README.md",
            "size": 55,
        },
        "issues": [
            {
                "id": 101,
                "number": 12,
                "title": "Clarify blueprint registration documentation",
                "body": "Add code examples showing how nested blueprints function.",
                "state": "open",
                "html_url": "https://github.com/pallets/flask/issues/12",
                "labels": ["documentation"],
                "user": "contributor_bob",
                "comments_count": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ],
        "source": {
            "provider": "github",
            "owner": "pallets",
            "repository": "flask",
        },
    }


@pytest.mark.asyncio
async def test_analyze_repository_success_v1(mock_analysis_data):
    transport = ASGITransport(app=app)
    with patch("app.api.v1.endpoints.repositories.github_service.analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_analysis_data

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/repositories/analyze",
                json={"url": "https://github.com/pallets/flask"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["repository"]["name"] == "flask"
    assert data["repository"]["owner"] == "pallets"
    assert data["repository"]["stars"] == 65000
    assert data["languages"]["Python"] == 800000
    assert data["readme"]["name"] == "README.md"
    assert len(data["issues"]) == 1
    assert data["issues"][0]["number"] == 12
    assert data["source"]["owner"] == "pallets"


@pytest.mark.asyncio
async def test_analyze_repository_success_direct_prefix(mock_analysis_data):
    transport = ASGITransport(app=app)
    with patch("app.api.v1.endpoints.repositories.github_service.analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_analysis_data

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/repositories/analyze",
                json={"url": "github.com/pallets/flask"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["repository"]["name"] == "flask"


@pytest.mark.asyncio
async def test_analyze_repository_invalid_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repositories/analyze",
            json={"url": "https://gitlab.com/owner/repo"},
        )

    assert response.status_code == 400
    assert "Unsupported domain" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_repository_not_found():
    transport = ASGITransport(app=app)
    with patch("app.api.v1.endpoints.repositories.github_service.analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.side_effect = GitHubNotFoundError("Not found")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/repositories/analyze",
                json={"url": "https://github.com/owner/missing-repo"},
            )

    assert response.status_code == 404
    assert "not found or is not publicly accessible" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_repository_rate_limit():
    transport = ASGITransport(app=app)
    with patch("app.api.v1.endpoints.repositories.github_service.analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.side_effect = GitHubRateLimitError("Rate limit exceeded")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/repositories/analyze",
                json={"url": "https://github.com/owner/repo"},
            )

    assert response.status_code == 403
    assert "rate limit exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_repository_timeout_service_error():
    transport = ASGITransport(app=app)
    with patch("app.api.v1.endpoints.repositories.github_service.analyze_repository", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.side_effect = GitHubServiceError("GitHub API request timed out.")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/repositories/analyze",
                json={"url": "https://github.com/owner/repo"},
            )

    assert response.status_code == 503
    assert "timed out" in response.json()["detail"]
