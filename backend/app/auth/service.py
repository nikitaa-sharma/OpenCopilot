"""
Authentication service for OpenSource Copilot (Phase 12).

Orchestrates:
- User registration with unique email validation and bcrypt hashing.
- User login with constant-time password verification.
- Safe user lookups and profile association.
"""

import logging
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.schemas import UserLoginRequest, UserRegisterRequest
from app.auth.security import create_access_token, hash_password, verify_password
from app.models.entities import DeveloperProfile, User

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """Base exception for authentication service errors."""
    pass


class UserAlreadyExistsError(AuthServiceError):
    """Raised when attempting to register an email that already exists."""
    pass


class InvalidCredentialsError(AuthServiceError):
    """Raised when authentication credentials (email/password) are incorrect."""
    pass


class UserInactiveError(AuthServiceError):
    """Raised when an inactive user attempts to log in or access protected endpoints."""
    pass


class AuthService:
    """
    Domain service handling user registration, authentication, and session generation.
    """

    async def register_user(
        self,
        session: AsyncSession,
        request: UserRegisterRequest,
    ) -> Tuple[User, str]:
        """
        Register a new user account:
        1. Verifies the email is not already in use.
        2. Hashes password using bcrypt.
        3. Creates persistent User record and associated empty DeveloperProfile.
        4. Issues signed JWT access token.
        """
        normalized_email = request.email.strip().lower()

        # Check for existing user with same normalized email
        existing_user = await self.get_user_by_email(session, normalized_email)
        if existing_user is not None:
            logger.info(f"Registration rejected: email '{normalized_email}' already exists.")
            raise UserAlreadyExistsError("A user with this email address is already registered.")

        # Hash password securely
        password_hash = hash_password(request.password)

        # Create user record
        user = User(
            email=normalized_email,
            password_hash=password_hash,
            display_name=request.display_name.strip(),
            is_active=True,
        )
        session.add(user)
        await session.flush()

        # Create initial developer profile attached to this user
        profile = DeveloperProfile(
            user_id=user.id,
            programming_languages=[],
            frameworks=[],
            tools=[],
            domains=[],
            experience_level="beginner",
            interests=[],
        )
        session.add(profile)
        await session.commit()
        await session.refresh(user)

        # Generate JWT access token
        token = create_access_token({"sub": str(user.id), "email": user.email})
        logger.info(f"User registered successfully: id={user.id}, email={user.email}")
        return user, token

    async def authenticate_user(
        self,
        session: AsyncSession,
        request: UserLoginRequest,
    ) -> Tuple[User, str]:
        """
        Authenticate user with email and password:
        1. Looks up user by normalized email.
        2. Validates password hash with bcrypt.
        3. Confirms user is active.
        4. Issues signed JWT access token.
        """
        normalized_email = request.email.strip().lower()

        user = await self.get_user_by_email(session, normalized_email)
        if user is None:
            # Generic error prevents account enumeration
            logger.info(f"Authentication failed: user not found for '{normalized_email}'")
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            logger.warning(f"Authentication rejected: user id={user.id} is inactive.")
            raise UserInactiveError("User account is inactive. Please contact support.")

        if not verify_password(request.password, user.password_hash):
            logger.info(f"Authentication failed: invalid password for user id={user.id}")
            raise InvalidCredentialsError("Invalid email or password.")

        token = create_access_token({"sub": str(user.id), "email": user.email})
        logger.info(f"User authenticated successfully: id={user.id}")
        return user, token

    async def get_user_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """Look up user by normalized email address."""
        stmt = select(User).where(User.email == email.strip().lower())
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        """Look up user by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalars().first()


auth_service = AuthService()
