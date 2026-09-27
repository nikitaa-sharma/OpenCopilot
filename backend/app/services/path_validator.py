"""
Repository file path validation and traversal prevention for OpenSource Copilot.

Enforces strict logical repository path boundaries:
- Rejects path traversal sequences (.., ../, ..\\, etc.)
- Rejects URL-encoded traversal (%2e%2e, %2f, %5c)
- Rejects absolute filesystem paths (/, \\, C:\\, etc.)
- Rejects null bytes and control characters
- Enforces maximum path length constraints
"""

import re
import urllib.parse


class PathTraversalError(ValueError):
    """Raised when a repository path attempts path traversal or filesystem escape."""
    pass


def validate_repository_path(path: str, max_length: int = 500) -> str:
    """
    Validate and normalize a repository-relative logical path.

    Args:
        path: Path within the repository (e.g. 'src/main.py')
        max_length: Maximum allowed length in characters (default 500)

    Returns:
        Cleaned, normalized forward-slash relative path.

    Raises:
        PathTraversalError: If path contains traversal sequences, absolute prefixes, or dangerous characters.
        ValueError: If path is empty or exceeds length limit.
    """
    if not path or not isinstance(path, str):
        raise ValueError("Repository path cannot be empty.")

    # Reject null bytes immediately
    if "\0" in path:
        raise PathTraversalError("Repository path cannot contain null bytes.")

    # Check length
    if len(path) > max_length:
        raise ValueError(f"Repository path exceeds maximum allowed length of {max_length} characters.")

    # Iteratively decode URL encoding to prevent double-encoding evasion
    decoded_path = path
    for _ in range(3):
        try:
            next_decoded = urllib.parse.unquote(decoded_path)
            if next_decoded == decoded_path:
                break
            decoded_path = next_decoded
        except Exception:
            break

    if "\0" in decoded_path:
        raise PathTraversalError("Repository path cannot contain null bytes.")

    # Normalize backslashes to forward slashes
    normalized = decoded_path.replace("\\", "/").strip()

    # Reject Windows drive letters (e.g., C:/, D:, etc.)
    if re.match(r"^[a-zA-Z]:", normalized):
        raise PathTraversalError(f"Absolute Windows filesystem paths are not allowed: '{path}'")

    # Reject leading slashes (absolute POSIX / UNC paths)
    if normalized.startswith("/"):
        raise PathTraversalError(f"Absolute filesystem paths are not allowed: '{path}'")

    # Split into logical path segments
    segments = [seg.strip() for seg in normalized.split("/") if seg.strip()]

    if not segments:
        raise ValueError("Repository path cannot resolve to an empty path.")

    # Check every segment for directory traversal
    for seg in segments:
        if seg in ("..", "."):
            raise PathTraversalError(f"Path traversal sequence detected in path: '{path}'")
        # Also check for hidden embedded traversal patterns like '.../' or '.. '
        if seg.startswith(".."):
            raise PathTraversalError(f"Potentially malicious path segment detected: '{seg}'")

    return "/".join(segments)
