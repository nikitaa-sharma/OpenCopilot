"""
Authentication API endpoints for Phase 12.

Provides:
- POST /register: Create a new user account (201 Created).
- POST /login: Authenticate with email/password (200 OK with JWT).
- GET /me: Retrieve current authenticated user (200 OK).
- POST /logout: Stateless logout acknowledgement (200 OK).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    AuthStatusResponse,
)
from app.auth.service import (
    auth_service,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserInactiveError,
)
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new user with email, password, and display name. Returns JWT access token.",
    responses={
        201: {"description": "User registered successfully."},
        409: {"description": "A user with this email address already exists."},
        422: {"description": "Invalid input (validation error)."},
    },
)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account and return a signed JWT token."""
    try:
        user, token = await auth_service.register_user(session, request)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Registration error: {exc}", exc_info=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration.",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with email and password",
    description="Validates credentials and returns a signed JWT access token.",
    responses={
        200: {"description": "Login successful."},
        401: {"description": "Invalid email or password."},
        403: {"description": "User account is inactive."},
    },
)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email/password and return a signed JWT token."""
    try:
        user, token = await auth_service.authenticate_user(session, request)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except UserInactiveError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )
    except Exception as exc:
        logger.error(f"Login error: {exc}", exc_info=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login.",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user",
    description="Returns the authenticated user's public profile information.",
    responses={
        200: {"description": "Authenticated user information."},
        401: {"description": "Not authenticated or invalid token."},
    },
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the current authenticated user's public information."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (stateless acknowledgement)",
    description="Acknowledges logout. Client should discard the local JWT token.",
    responses={
        200: {"description": "Logout acknowledged."},
    },
)
async def logout() -> dict:
    """
    Stateless logout acknowledgement.
    The client is responsible for discarding the stored JWT token.
    """
    return {"detail": "Logged out successfully. Please discard your access token."}
