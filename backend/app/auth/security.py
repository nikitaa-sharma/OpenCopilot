"""
Security and cryptographic utilities for Phase 12: Authentication & User Accounts.

Provides:
- Secure salted password hashing using bcrypt.
- Constant-time password verification.
- Signed JSON Web Token (JWT) encoding and validation with HMAC-SHA256.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenDecodeError(Exception):
    """Raised when an authentication token is invalid or cannot be decoded."""
    pass


class TokenExpiredError(TokenDecodeError):
    """Raised when an authentication token has expired."""
    pass


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with a random salt.
    Plaintext password is never stored or returned.
    """
    if not password or not password.strip():
        raise ValueError("Password cannot be empty or whitespace-only.")
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash using constant-time comparison.
    Returns True if valid, False otherwise. Never raises an exception on mismatch.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception as exc:
        logger.warning(f"Password verification encountered an error: {exc}")
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token containing subject claims and expiration.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
    })

    return jwt.encode(
        to_encode,
        settings.AUTH_SECRET_KEY,
        algorithm=settings.AUTH_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a signed JWT access token.
    Raises TokenExpiredError if expired, TokenDecodeError if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Authentication token has expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenDecodeError("Invalid authentication token.") from exc
    except Exception as exc:
        raise TokenDecodeError(f"Token validation error: {exc}") from exc
