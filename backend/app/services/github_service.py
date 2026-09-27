import base64
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.path_validator import validate_repository_path, PathTraversalError

logger = logging.getLogger(__name__)



class GitHubException(Exception):
    """Base exception for GitHub integration errors."""
    pass


class InvalidGitHubURLError(GitHubException):
    """Raised when the provided GitHub URL is invalid or malformed."""
    pass


class GitHubNotFoundError(GitHubException):
    """Raised when the repository does not exist or is private."""
    pass


class GitHubRateLimitError(GitHubException):
    """Raised when GitHub API rate limits are exceeded."""
    pass


class GitHubServiceError(GitHubException):
    """Raised when GitHub API requests fail unexpectedly or timeout."""
    pass


# Reserved GitHub paths that are not repositories
RESERVED_GITHUB_PATHS = {
    "about", "features", "explore", "trending", "collections", "events",
    "sponsors", "site", "security", "customer-stories", "pricing",
    "login", "join", "settings", "notifications", "search", "pulls",
    "issues", "marketplace", "orgs", "organizations", "users"
}


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Validate and extract (owner, repo) from a GitHub repository URL.

    Accepts formats such as:
      - github.com/owner/repo
      - https://github.com/owner/repo
      - https://www.github.com/owner/repo
      - https://github.com/owner/repo/ (trailing slash)
      - https://github.com/owner/repo.git (.git extension)
      - https://github.com/owner/repo?tab=readme (query string)
      - https://github.com/owner/repo#readme (fragment)

    Rejects non-GitHub domains, malformed URLs, and URLs lacking owner/repo.
    """
    if not url or not isinstance(url, str):
        raise InvalidGitHubURLError("Repository URL cannot be empty.")

    clean_url = url.strip()

    # Prepend scheme if missing for urlparse compatibility
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", clean_url):
        clean_url = "https://" + clean_url

    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        raise InvalidGitHubURLError(f"Invalid URL structure: {exc}") from exc

    # Validate hostname is strictly github.com (or www.github.com)
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("github.com", "www.github.com"):
        raise InvalidGitHubURLError(
            f"Unsupported domain '{hostname}'. Only public GitHub repository URLs are accepted."
        )

    # Clean path segments
    path = parsed.path.strip("/")
    segments = [seg for seg in path.split("/") if seg]

    # Must have exactly 2 main segments: owner and repo
    if len(segments) < 2:
        raise InvalidGitHubURLError(
            "GitHub repository URL must include both owner and repository name."
        )

    # Disallow URLs pointing deeper than the repo root (e.g. /owner/repo/pulls/123)
    # Exception: allow .git or single sub-segment if it's .git
    owner = segments[0].strip()
    repo = segments[1].strip()

    if len(segments) > 2:
        raise InvalidGitHubURLError(
            "URL appears to point to a sub-resource or page rather than the repository root."
        )

    # Check for reserved paths
    if owner.lower() in RESERVED_GITHUB_PATHS:
        raise InvalidGitHubURLError(
            f"'{owner}' is a reserved GitHub path, not a repository owner."
        )

    # Strip .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]

    # Validate owner and repo against valid GitHub naming conventions
    # GitHub username: alphanumeric and single hyphens, cannot begin/end with hyphen
    # GitHub repo: alphanumeric, hyphens, underscores, dots
    owner_pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$"
    repo_pattern = r"^[a-zA-Z0-9_.-]+$"

    if not re.match(owner_pattern, owner) or not re.match(repo_pattern, repo):
        raise InvalidGitHubURLError(
            f"Invalid GitHub repository or owner name format: '{owner}/{repo}'."
        )

    if not owner or not repo:
        raise InvalidGitHubURLError("Owner and repository name must not be empty.")

    return owner, repo


class GitHubService:
    """
    Asynchronous client for interacting with the GitHub REST API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.GITHUB_API_BASE_URL).rstrip("/")
        self._explicit_token = token
        self.timeout = timeout if timeout is not None else settings.GITHUB_REQUEST_TIMEOUT
        logger.info(f"GitHubService initialized (authenticated: {self.is_authenticated})")

    @property
    def token(self) -> str:
        """Read explicit token if provided, otherwise dynamically resolve from settings."""
        if self._explicit_token is not None:
            return self._explicit_token
        return settings.GITHUB_TOKEN or ""

    @token.setter
    def token(self, value: Optional[str]) -> None:
        self._explicit_token = value

    @property
    def is_authenticated(self) -> bool:
        """Safe diagnostic: returns True if a GitHub token is configured, without exposing the token."""
        return bool(self.token and self.token.strip())

    def _get_headers(self) -> Dict[str, str]:
        """Generate headers required for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "OpenSourceCopilot",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token_val = self.token.strip() if self.token else ""
        if token_val:
            headers["Authorization"] = f"Bearer {token_val}"
        return headers

    def _handle_error_response(self, response: httpx.Response, context: str) -> None:
        """Translate GitHub HTTP error status codes into descriptive domain exceptions."""
        status = response.status_code

        if status == 404:
            raise GitHubNotFoundError(
                "GitHub repository not found or is not publicly accessible."
            )

        if status == 403:
            # Check rate limit headers or body message
            remaining = response.headers.get("x-ratelimit-remaining")
            message = ""
            try:
                data = response.json()
                message = data.get("message", "")
            except Exception:
                pass

            if remaining == "0" or "rate limit" in message.lower():
                raise GitHubRateLimitError(
                    "GitHub API rate limit exceeded. Please try again later or configure a GitHub token."
                )
            raise GitHubServiceError(
                f"GitHub API access forbidden: {message or 'Forbidden'}"
            )

        if 400 <= status < 500:
            msg = "Client error from GitHub API"
            try:
                msg = response.json().get("message", msg)
            except Exception:
                pass
            raise GitHubServiceError(f"{msg} (HTTP {status})")

        if status >= 500:
            raise GitHubServiceError(
                f"GitHub API server error encountered while {context}. Please try again later."
            )

    async def fetch_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch general repository metadata from GET /repos/{owner}/{repo}."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching repository {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    "GitHub API request timed out while fetching repository metadata."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching repository {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.is_error:
            self._handle_error_response(response, f"fetching repository {owner}/{repo}")

        data = response.json()
        license_info = None
        if data.get("license"):
            license_info = {
                "key": data["license"].get("key"),
                "name": data["license"].get("name"),
                "spdx_id": data["license"].get("spdx_id"),
                "url": data["license"].get("url"),
            }

        return {
            "id": data.get("id"),
            "owner": data.get("owner", {}).get("login", owner),
            "name": data.get("name", repo),
            "full_name": data.get("full_name", f"{owner}/{repo}"),
            "description": data.get("description"),
            "html_url": data.get("html_url"),
            "default_branch": data.get("default_branch", "main"),
            "visibility": data.get("visibility", "public"),
            "language": data.get("language"),
            "license": license_info,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "watchers": data.get("watchers_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
            "topics": data.get("topics", []),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "pushed_at": data.get("pushed_at"),
        }

    async def fetch_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Fetch language byte counts from GET /repos/{owner}/{repo}/languages."""
        url = f"{self.base_url}/repos/{owner}/{repo}/languages"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching languages for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    "GitHub API request timed out while fetching languages."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching languages for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.is_error:
            self._handle_error_response(response, f"fetching languages for {owner}/{repo}")

        return response.json()

    async def fetch_readme(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Fetch repository README from GET /repos/{owner}/{repo}/readme.
        Decodes base64 content if present. Returns None if README does not exist (404).
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/readme"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching readme for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    "GitHub API request timed out while fetching README."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching readme for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.status_code == 404:
            return None

        if response.is_error:
            self._handle_error_response(response, f"fetching readme for {owner}/{repo}")

        data = response.json()
        raw_content = data.get("content", "")
        encoding = data.get("encoding", "")

        decoded_text = ""
        if encoding == "base64" and raw_content:
            try:
                decoded_bytes = base64.b64decode(raw_content)
                decoded_text = decoded_bytes.decode("utf-8", errors="replace")
            except Exception as exc:
                logger.warning(f"Failed to decode base64 README for {owner}/{repo}: {exc}")
                decoded_text = ""
        else:
            decoded_text = raw_content

        return {
            "name": data.get("name", "README.md"),
            "content": decoded_text,
            "html_url": data.get("html_url"),
            "size": data.get("size", 0),
        }

    async def fetch_issues(
        self, owner: str, repo: str, per_page: int = 20, state: str = "open"
    ) -> List[Dict[str, Any]]:
        """
        Fetch issues from GET /repos/{owner}/{repo}/issues?state={state}&per_page=...
        Strictly excludes pull requests (entries containing 'pull_request' key).
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        headers = self._get_headers()
        # Request slightly more items to account for PRs that will be filtered out
        request_limit = min(per_page * 2, 60)
        params = {"state": state, "per_page": str(request_limit)}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching issues for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    "GitHub API request timed out while fetching issues."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching issues for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.is_error:
            self._handle_error_response(response, f"fetching issues for {owner}/{repo}")

        items = response.json()
        issues: List[Dict[str, Any]] = []

        for item in items:
            # Exclude pull requests
            if "pull_request" in item:
                continue

            labels = [
                label.get("name", "")
                for label in item.get("labels", [])
                if isinstance(label, dict) and label.get("name")
            ]

            user_login = item.get("user", {}).get("login", "") if item.get("user") else ""

            issues.append({
                "id": item.get("id"),
                "number": item.get("number"),
                "title": item.get("title", ""),
                "body": item.get("body") or "",
                "state": item.get("state", "open"),
                "html_url": item.get("html_url", ""),
                "labels": labels,
                "user": user_login,
                "comments_count": item.get("comments", 0),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })

            if len(issues) >= per_page:
                break

        return issues

    async def fetch_single_issue(
        self, owner: str, repo: str, issue_number: int
    ) -> Dict[str, Any]:
        """
        Fetch a single issue by number from GET /repos/{owner}/{repo}/issues/{issue_number}.
        Returns normalized issue dict, strictly verifying it is not a pull request.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching issue #{issue_number} for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    f"GitHub API request timed out while fetching issue #{issue_number}."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching issue #{issue_number} for {owner}/{repo}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.status_code == 404:
            raise GitHubNotFoundError(
                f"Issue #{issue_number} not found in repository {owner}/{repo}."
            )

        if response.is_error:
            self._handle_error_response(response, f"fetching issue #{issue_number} for {owner}/{repo}")

        item = response.json()

        # Reject pull requests
        if "pull_request" in item:
            raise GitHubNotFoundError(
                f"Item #{issue_number} in {owner}/{repo} is a pull request, not an issue."
            )

        labels = [
            label.get("name", "")
            for label in item.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        ]
        user_login = item.get("user", {}).get("login", "") if item.get("user") else ""

        return {
            "id": item.get("id"),
            "number": item.get("number"),
            "title": item.get("title", ""),
            "body": item.get("body") or "",
            "state": item.get("state", "open"),
            "html_url": item.get("html_url", ""),
            "labels": labels,
            "user": user_login,
            "comments_count": item.get("comments", 0),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }

    async def fetch_tree(
        self, owner: str, repo: str, branch: Optional[str] = None, recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch repository file tree from GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1.
        Uses branch name (or 'HEAD' as default) and normalizes 'blob' -> 'file' and 'tree' -> 'directory'.
        """
        target_ref = branch.strip() if branch and branch.strip() else "HEAD"
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{target_ref}"
        params = {"recursive": "1"} if recursive else {}
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching tree for {owner}/{repo}@{target_ref}: {exc}")
                raise GitHubServiceError(
                    "GitHub API request timed out while fetching repository tree."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching tree for {owner}/{repo}@{target_ref}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.status_code == 404:
            raise GitHubNotFoundError(
                f"Repository or branch '{target_ref}' not found."
            )

        if response.is_error:
            self._handle_error_response(response, f"fetching tree for {owner}/{repo}@{target_ref}")

        data = response.json()
        raw_tree = data.get("tree", [])
        truncated = data.get("truncated", False)

        normalized_tree = []
        for item in raw_tree:
            raw_type = item.get("type", "")
            if raw_type == "blob":
                item_type = "file"
            elif raw_type == "tree":
                item_type = "directory"
            else:
                item_type = raw_type

            normalized_tree.append({
                "path": item.get("path", ""),
                "type": item_type,
                "sha": item.get("sha", ""),
                "size": item.get("size"),
                "url": item.get("url"),
            })

        return {
            "sha": data.get("sha", ""),
            "branch": target_ref,
            "truncated": truncated,
            "tree": normalized_tree,
        }

    async def fetch_file_content(
        self, owner: str, repo: str, path: str, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch individual file content from GET /repos/{owner}/{repo}/contents/{path}.
        Decodes base64 content safely, validates UTF-8 text, and applies size checks.
        """
        try:
            clean_path = validate_repository_path(path)
        except (PathTraversalError, ValueError) as exc:
            raise InvalidGitHubURLError(f"Invalid file path: {exc}") from exc

        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{clean_path}"

        params = {}
        if branch and branch.strip():
            params["ref"] = branch.strip()
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
            except httpx.TimeoutException as exc:
                logger.error(f"Timeout fetching file {owner}/{repo}:{clean_path}: {exc}")
                raise GitHubServiceError(
                    f"GitHub API request timed out while fetching file '{clean_path}'."
                ) from exc
            except httpx.RequestError as exc:
                logger.error(f"Network error fetching file {owner}/{repo}:{clean_path}: {exc}")
                raise GitHubServiceError(
                    f"Network error communicating with GitHub API: {exc}"
                ) from exc

        if response.status_code == 404:
            raise GitHubNotFoundError(f"File '{clean_path}' not found in repository.")

        if response.is_error:
            self._handle_error_response(response, f"fetching file '{clean_path}' for {owner}/{repo}")

        data = response.json()

        # If path points to a directory instead of a file, GitHub returns a list
        if isinstance(data, list):
            return {
                "path": clean_path,
                "name": clean_path.split("/")[-1],
                "sha": None,
                "size": 0,
                "content": None,
                "is_binary": False,
                "skip_reason": f"'{clean_path}' is a directory, not a file.",
            }

        item_type = data.get("type", "file")
        if item_type != "file":
            return {
                "path": clean_path,
                "name": data.get("name", clean_path.split("/")[-1]),
                "sha": data.get("sha"),
                "size": data.get("size", 0),
                "content": None,
                "is_binary": False,
                "skip_reason": f"Unsupported object type '{item_type}'.",
            }

        size = data.get("size", 0)
        sha = data.get("sha")
        name = data.get("name", clean_path.split("/")[-1])
        encoding = data.get("encoding", "")
        raw_content = data.get("content", "")

        # Check file size limit
        if size > settings.MAX_FILE_SIZE_BYTES:
            return {
                "path": clean_path,
                "name": name,
                "sha": sha,
                "size": size,
                "content": None,
                "is_binary": False,
                "skip_reason": f"File size ({size} bytes) exceeds maximum limit of {settings.MAX_FILE_SIZE_BYTES} bytes.",
            }

        # Decode base64 content safely
        decoded_text: Optional[str] = None
        is_binary = False
        skip_reason: Optional[str] = None

        if encoding == "base64" and raw_content:
            try:
                raw_bytes = base64.b64decode(raw_content)
                # Check for null bytes / binary data
                if b"\x00" in raw_bytes:
                    is_binary = True
                    skip_reason = "Binary file detected (contains null bytes)."
                else:
                    decoded_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                is_binary = True
                skip_reason = "File contains non-UTF-8 or binary encoding."
            except Exception as exc:
                skip_reason = f"Failed to decode base64 content: {exc}"
        else:
            decoded_text = raw_content

        return {
            "path": clean_path,
            "name": name,
            "sha": sha,
            "size": size,
            "content": decoded_text,
            "is_binary": is_binary,
            "skip_reason": skip_reason,
        }

    async def analyze_repository(self, url: str) -> Dict[str, Any]:
        """
        Full orchestration: validate URL and fetch metadata, languages, README, and issues.
        """
        owner, repo = parse_github_url(url)

        # Fetch repository metadata first (will fail with 404/403 if invalid or rate limited)
        repo_data = await self.fetch_repository(owner, repo)

        # Fetch languages, readme, and issues
        languages_data = await self.fetch_languages(owner, repo)
        readme_data = await self.fetch_readme(owner, repo)
        issues_data = await self.fetch_issues(owner, repo, per_page=20)

        return {
            "repository": repo_data,
            "languages": languages_data,
            "readme": readme_data,
            "issues": issues_data,
            "source": {
                "provider": "github",
                "owner": owner,
                "repository": repo,
            },
        }


# Singleton service instance
github_service = GitHubService()

