import base64
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.services.github_service import (
    GitHubService,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubServiceError,
)


@pytest.fixture
def service():
    return GitHubService(
        base_url="https://api.github.com",
        token="test_token",
        timeout=5,
    )


def test_service_headers_with_token(service):
    assert service.is_authenticated is True
    headers = service._get_headers()
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["User-Agent"] == "OpenSourceCopilot"
    assert headers["Authorization"] == "Bearer test_token"


def test_service_headers_without_token():
    svc = GitHubService(base_url="https://api.github.com", token="")
    assert svc.is_authenticated is False
    headers = svc._get_headers()
    assert "Authorization" not in headers


def test_service_headers_whitespace_token_omits_authorization():
    """Verify whitespace-only token does not produce an invalid/empty Authorization header."""
    svc = GitHubService(base_url="https://api.github.com", token="   ")
    assert svc.is_authenticated is False
    headers = svc._get_headers()
    assert "Authorization" not in headers


def test_service_reads_configured_settings_token():
    """Verify GitHubService dynamically reads settings.GITHUB_TOKEN when no explicit token is passed."""
    with patch("app.services.github_service.settings.GITHUB_TOKEN", "ghp_dynamic_env_token"):
        svc = GitHubService(base_url="https://api.github.com")
        assert svc.is_authenticated is True
        assert svc.token == "ghp_dynamic_env_token"
        headers = svc._get_headers()
        assert headers["Authorization"] == "Bearer ghp_dynamic_env_token"


def test_service_unauthenticated_when_settings_token_empty():
    """Verify GitHubService is unauthenticated when settings.GITHUB_TOKEN is empty."""
    with patch("app.services.github_service.settings.GITHUB_TOKEN", ""):
        svc = GitHubService(base_url="https://api.github.com")
        assert svc.is_authenticated is False
        assert svc.token == ""
        headers = svc._get_headers()
        assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_authenticated_request_includes_auth_header():
    """Verify actual client.get receives Authorization header when token is configured."""
    secret_token = "ghp_valid_secret_token_12345"
    svc = GitHubService(token=secret_token)
    mock_resp = httpx.Response(200, json={"id": 1, "name": "repo", "owner": {"login": "owner"}})

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        await svc.fetch_repository("owner", "repo")
        mock_get.assert_called_once()
        sent_headers = mock_get.call_args[1]["headers"]
        assert "Authorization" in sent_headers
        assert sent_headers["Authorization"] == f"Bearer {secret_token}"


@pytest.mark.asyncio
async def test_unauthenticated_request_omits_auth_header():
    """Verify actual client.get does NOT include Authorization header when unauthenticated."""
    svc = GitHubService(token="")
    mock_resp = httpx.Response(200, json={"id": 1, "name": "repo", "owner": {"login": "owner"}})

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        await svc.fetch_repository("owner", "repo")
        mock_get.assert_called_once()
        sent_headers = mock_get.call_args[1]["headers"]
        assert "Authorization" not in sent_headers


@pytest.mark.asyncio
async def test_token_value_is_never_logged(caplog):
    """Verify the token secret value is never printed to logs during normal calls or error handling."""
    import logging
    secret_token = "ghp_NEVER_PRINT_THIS_TOKEN_IN_LOGS_999"
    svc = GitHubService(token=secret_token)

    # 1. Successful request
    mock_resp_ok = httpx.Response(200, json={"id": 1, "name": "repo", "owner": {"login": "owner"}})
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_ok
        with caplog.at_level(logging.DEBUG):
            await svc.fetch_repository("owner", "repo")

    # 2. Timeout error
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(GitHubServiceError):
                await svc.fetch_repository("owner", "repo")

    # 3. Rate limit 403 error
    mock_resp_403 = httpx.Response(
        403,
        headers={"x-ratelimit-remaining": "0"},
        json={"message": "API rate limit exceeded"},
    )
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_403
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(GitHubRateLimitError):
                await svc.fetch_repository("owner", "repo")

    # Assert secret token was never logged in any record
    for record in caplog.records:
        assert secret_token not in record.message
        assert secret_token not in str(record)
    assert secret_token not in caplog.text


@pytest.mark.asyncio
async def test_fetch_repository_success(service):
    mock_payload = {
        "id": 123456,
        "name": "react",
        "full_name": "facebook/react",
        "owner": {"login": "facebook"},
        "description": "A declarative JavaScript library for building user interfaces",
        "html_url": "https://github.com/facebook/react",
        "default_branch": "main",
        "visibility": "public",
        "language": "JavaScript",
        "stargazers_count": 220000,
        "forks_count": 45000,
        "watchers_count": 220000,
        "open_issues_count": 800,
        "topics": ["react", "javascript", "ui"],
        "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT"},
        "created_at": "2013-05-24T16:15:54Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "pushed_at": "2024-01-02T00:00:00Z",
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("GET", "https://api.github.com/repos/facebook/react"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await service.fetch_repository("facebook", "react")

    assert result["name"] == "react"
    assert result["full_name"] == "facebook/react"
    assert result["stars"] == 220000
    assert result["forks"] == 45000
    assert result["open_issues_count"] == 800
    assert result["topics"] == ["react", "javascript", "ui"]
    assert result["license"]["name"] == "MIT License"


@pytest.mark.asyncio
async def test_fetch_languages_success(service):
    mock_payload = {
        "JavaScript": 500000,
        "TypeScript": 300000,
        "HTML": 20000,
    }
    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("GET", "https://api.github.com/repos/facebook/react/languages"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await service.fetch_languages("facebook", "react")

    assert result == mock_payload


@pytest.mark.asyncio
async def test_fetch_readme_success_base64_decode(service):
    readme_text = "# React\nThe library for web and native user interfaces."
    b64_content = base64.b64encode(readme_text.encode("utf-8")).decode("utf-8")

    mock_payload = {
        "name": "README.md",
        "encoding": "base64",
        "content": b64_content,
        "html_url": "https://github.com/facebook/react/blob/main/README.md",
        "size": len(readme_text),
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("GET", "https://api.github.com/repos/facebook/react/readme"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await service.fetch_readme("facebook", "react")

    assert result is not None
    assert result["name"] == "README.md"
    assert result["content"] == readme_text
    assert result["html_url"] == "https://github.com/facebook/react/blob/main/README.md"


@pytest.mark.asyncio
async def test_fetch_readme_not_found(service):
    mock_resp = httpx.Response(
        status_code=404,
        json={"message": "Not Found"},
        request=httpx.Request("GET", "https://api.github.com/repos/owner/repo/readme"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await service.fetch_readme("owner", "repo")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_issues_excludes_pull_requests(service):
    mock_items = [
        {
            "id": 101,
            "number": 1,
            "title": "Bug in component rendering",
            "body": "Detailed description of the bug.",
            "state": "open",
            "html_url": "https://github.com/facebook/react/issues/1",
            "labels": [{"name": "bug"}, {"name": "good first issue"}],
            "user": {"login": "alice"},
            "comments": 3,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            # No "pull_request" key -> Genuine issue
        },
        {
            "id": 102,
            "number": 2,
            "title": "Fix component rendering PR",
            "body": "Fixes #1",
            "state": "open",
            "html_url": "https://github.com/facebook/react/pull/2",
            "labels": [{"name": "enhancement"}],
            "user": {"login": "bob"},
            "comments": 1,
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-03T00:00:00Z",
            "pull_request": {"url": "https://api.github.com/repos/facebook/react/pulls/2"},  # Pull request!
        },
        {
            "id": 103,
            "number": 3,
            "title": "Documentation typo",
            "body": "Typo in hook docs.",
            "state": "open",
            "html_url": "https://github.com/facebook/react/issues/3",
            "labels": [{"name": "documentation"}],
            "user": {"login": "charlie"},
            "comments": 0,
            "created_at": "2024-01-03T00:00:00Z",
            "updated_at": "2024-01-03T00:00:00Z",
            # No "pull_request" key -> Genuine issue
        },
    ]

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_items,
        request=httpx.Request("GET", "https://api.github.com/repos/facebook/react/issues"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        issues = await service.fetch_issues("facebook", "react", per_page=10)

    # Verify pull request (number 2) was excluded
    assert len(issues) == 2
    assert issues[0]["number"] == 1
    assert issues[0]["title"] == "Bug in component rendering"
    assert issues[0]["labels"] == ["bug", "good first issue"]
    assert issues[0]["user"] == "alice"
    assert issues[1]["number"] == 3
    assert issues[1]["title"] == "Documentation typo"


@pytest.mark.asyncio
async def test_fetch_repository_404_not_found(service):
    mock_resp = httpx.Response(
        status_code=404,
        json={"message": "Not Found"},
        request=httpx.Request("GET", "https://api.github.com/repos/nonexistent/repo"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(GitHubNotFoundError):
            await service.fetch_repository("nonexistent", "repo")


@pytest.mark.asyncio
async def test_fetch_repository_rate_limit_exceeded(service):
    mock_resp = httpx.Response(
        status_code=403,
        headers={"x-ratelimit-remaining": "0"},
        json={"message": "API rate limit exceeded for IP"},
        request=httpx.Request("GET", "https://api.github.com/repos/owner/repo"),
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(GitHubRateLimitError):
            await service.fetch_repository("owner", "repo")


@pytest.mark.asyncio
async def test_fetch_repository_timeout(service):
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Read timeout")
        with pytest.raises(GitHubServiceError) as exc:
            await service.fetch_repository("owner", "repo")
        assert "timed out" in str(exc.value)


@pytest.mark.asyncio
async def test_fetch_single_issue_success():
    """Verify fetch_single_issue normalizes fields and succeeds."""
    service = GitHubService()
    mock_payload = {
        "id": 555,
        "number": 42,
        "title": "Bug in url parser",
        "body": "Detailed description",
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/42",
        "labels": [{"name": "bug"}, {"name": "good first issue"}],
        "user": {"login": "octocat"},
        "comments": 3,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }
    mock_resp = httpx.Response(200, json=mock_payload)
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        issue = await service.fetch_single_issue("owner", "repo", 42)

        assert issue["number"] == 42
        assert issue["title"] == "Bug in url parser"
        assert issue["labels"] == ["bug", "good first issue"]
        assert issue["user"] == "octocat"
        assert issue["comments_count"] == 3


@pytest.mark.asyncio
async def test_fetch_single_issue_rejects_pull_request():
    """Verify fetch_single_issue raises GitHubNotFoundError if item is a PR."""
    service = GitHubService()
    mock_payload = {
        "id": 556,
        "number": 43,
        "title": "PR adding feature",
        "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/43"},
    }
    mock_resp = httpx.Response(200, json=mock_payload)
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(GitHubNotFoundError) as exc:
            await service.fetch_single_issue("owner", "repo", 43)
        assert "pull request" in str(exc.value)

