"""
FastAPI authentication dependencies for Phase 12.

Provides:
- get_current_user: Requires valid Bearer token, returns User.
- get_current_user_optional: Returns User if valid token present, else None.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token, TokenDecodeError, TokenExpiredError
from app.core.database import get_db
from app.models.entities import User
from app.auth.service import auth_service

logger = logging.getLogger(__name__)

# Required bearer token scheme (auto_error=True raises 401 if missing)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

# Optional bearer token scheme (auto_error=False returns None if missing)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates Bearer token, extracts user ID, loads user from DB.
    Raises 401 Unauthorized on invalid/expired token or unknown/inactive user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (TokenDecodeError, ValueError, TypeError):
        raise credentials_exception

    user = await auth_service.get_user_by_id(session, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    session: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Returns user if valid token present; returns None if no token provided.
    Silently ignores invalid tokens (returns None instead of raising).
    """
    if token is None:
        return None

    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (TokenDecodeError, TokenExpiredError, ValueError, TypeError):
        return None

    user = await auth_service.get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        return None

    return user
