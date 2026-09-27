import pytest
from app.services.github_service import parse_github_url, InvalidGitHubURLError


def test_parse_valid_standard_url():
    owner, repo = parse_github_url("https://github.com/facebook/react")
    assert owner == "facebook"
    assert repo == "react"


def test_parse_valid_url_without_scheme():
    owner, repo = parse_github_url("github.com/pallets/flask")
    assert owner == "pallets"
    assert repo == "flask"


def test_parse_valid_url_with_www():
    owner, repo = parse_github_url("https://www.github.com/fastapi/fastapi")
    assert owner == "fastapi"
    assert repo == "fastapi"


def test_parse_valid_url_with_trailing_slash():
    owner, repo = parse_github_url("https://github.com/owner/repository/")
    assert owner == "owner"
    assert repo == "repository"


def test_parse_valid_url_with_git_suffix():
    owner, repo = parse_github_url("https://github.com/owner/repository.git")
    assert owner == "owner"
    assert repo == "repository"


def test_parse_valid_url_with_query_and_fragment():
    owner, repo = parse_github_url("https://github.com/owner/repository?tab=readme#contributing")
    assert owner == "owner"
    assert repo == "repository"


def test_parse_valid_url_with_dots_and_hyphens():
    owner, repo = parse_github_url("https://github.com/org-name/repo.js-v2")
    assert owner == "org-name"
    assert repo == "repo.js-v2"


def test_reject_gitlab_url():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://gitlab.com/owner/repo")
    assert "Unsupported domain" in str(exc.value)


def test_reject_bitbucket_url():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://bitbucket.org/owner/repo")
    assert "Unsupported domain" in str(exc.value)


def test_reject_arbitrary_website():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://example.com/owner/repo")
    assert "Unsupported domain" in str(exc.value)


def test_reject_missing_owner():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://github.com/")
    assert "must include both owner and repository name" in str(exc.value)


def test_reject_missing_repo():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://github.com/owner")
    assert "must include both owner and repository name" in str(exc.value)


def test_reject_deep_subresources():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://github.com/owner/repo/pulls/123")
    assert "sub-resource" in str(exc.value)


def test_reject_reserved_github_paths():
    with pytest.raises(InvalidGitHubURLError) as exc:
        parse_github_url("https://github.com/settings/profile")
    assert "reserved GitHub path" in str(exc.value)


def test_reject_empty_and_whitespace():
    with pytest.raises(InvalidGitHubURLError):
        parse_github_url("")
    with pytest.raises(InvalidGitHubURLError):
        parse_github_url("   ")
