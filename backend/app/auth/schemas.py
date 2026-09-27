"""
Pydantic schemas for Phase 12: Authentication & User Accounts.

Strict security guidelines:
- Passwords are validated on input but NEVER stored or returned.
- Password hashes and security secrets are strictly omitted from all response models.
"""

from datetime import datetime
import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""
    email: str = Field(..., max_length=255, description="User email address (normalized case-insensitively)")
    password: str = Field(..., min_length=8, max_length=128, description="User password (minimum 8 characters)")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name for the developer")


    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Email cannot be empty.")
        # Basic RFC-compliant email pattern check
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, trimmed):
            raise ValueError("Invalid email format.")
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or whitespace-only.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Display name cannot be empty or whitespace-only.")
        return trimmed


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    email: str = Field(..., max_length=255, description="Registered email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Email cannot be empty.")
        return trimmed


class UserResponse(BaseModel):
    """
    Public representation of an authenticated user.
    Strictly excludes password_hash and internal credentials.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique user identifier")
    email: str = Field(..., description="Normalized email address")
    display_name: str = Field(..., description="Developer display name")
    is_active: bool = Field(default=True, description="Account active status")
    avatar_url: Optional[str] = Field(default=None, description="Optional avatar URL")
    created_at: Optional[datetime] = Field(default=None, description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class TokenResponse(BaseModel):
    """Response returned upon successful registration or login."""
    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="Authenticated user metadata")


class AuthStatusResponse(BaseModel):
    """Response returned by session verification endpoints."""
    authenticated: bool = Field(..., description="Whether a valid session is active")
    user: Optional[UserResponse] = Field(default=None, description="User object if authenticated")
