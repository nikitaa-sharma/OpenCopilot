"""
Authentication domain package for OpenSource Copilot (Phase 12).

Exports:
- Security utilities (hash_password, verify_password, create_access_token, decode_access_token)
- Pydantic schemas (UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse, AuthStatusResponse)
- AuthService (register_user, authenticate_user, get_user_by_id, get_user_by_email)
- FastAPI dependencies (get_current_user, get_current_user_optional)
"""

from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    TokenDecodeError,
    TokenExpiredError,
)
from app.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    AuthStatusResponse,
)
from app.auth.service import (
    AuthService,
    AuthServiceError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserInactiveError,
    auth_service,
)
from app.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "TokenDecodeError",
    "TokenExpiredError",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserResponse",
    "TokenResponse",
    "AuthStatusResponse",
    "AuthService",
    "AuthServiceError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "UserInactiveError",
    "auth_service",
    "get_current_user",
    "get_current_user_optional",
]
