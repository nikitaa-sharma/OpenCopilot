"""
Developer Skill Profile Endpoints for Phase 10 + Phase 12 Authentication.

Provides GET and POST endpoints for managing the developer skill profile.
- If the user is authenticated, loads/saves their persistent DeveloperProfile in PostgreSQL.
- If the user is not authenticated, falls back to the existing in-memory profile (backward compatibility).
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_optional
from app.core.database import get_db
from app.models.entities import DeveloperProfile as DeveloperProfileModel, User
from app.schemas.profile import DeveloperSkillProfile
from app.services.profile_service import profile_service
from app.services.skill_normalizer import normalize_profile

router = APIRouter()


async def _load_db_profile(
    session: AsyncSession, user: User
) -> DeveloperSkillProfile:
    """Load the authenticated user's profile from PostgreSQL."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(DeveloperProfileModel).where(DeveloperProfileModel.user_id == user.id)
    result = await session.execute(stmt)
    db_profile = result.scalars().first()

    if db_profile is None:
        return DeveloperSkillProfile(
            programming_languages=[],
            frameworks=[],
            tools=[],
            domains=[],
            experience_level="beginner",
            interests=[],
        )

    return DeveloperSkillProfile(
        programming_languages=db_profile.programming_languages or [],
        frameworks=db_profile.frameworks or [],
        tools=db_profile.tools or [],
        domains=db_profile.domains or [],
        experience_level=db_profile.experience_level or "beginner",
        interests=db_profile.interests or [],
    )


async def _save_db_profile(
    session: AsyncSession, user: User, profile: DeveloperSkillProfile
) -> DeveloperSkillProfile:
    """Save the authenticated user's profile to PostgreSQL."""
    from sqlalchemy import select

    normalized = normalize_profile(profile)

    stmt = select(DeveloperProfileModel).where(DeveloperProfileModel.user_id == user.id)
    result = await session.execute(stmt)
    db_profile = result.scalars().first()

    if db_profile is None:
        db_profile = DeveloperProfileModel(
            user_id=user.id,
            programming_languages=normalized.programming_languages,
            frameworks=normalized.frameworks,
            tools=normalized.tools,
            domains=normalized.domains,
            experience_level=normalized.experience_level or "beginner",
            interests=normalized.interests,
        )
        session.add(db_profile)
    else:
        db_profile.programming_languages = normalized.programming_languages
        db_profile.frameworks = normalized.frameworks
        db_profile.tools = normalized.tools
        db_profile.domains = normalized.domains
        db_profile.experience_level = normalized.experience_level or "beginner"
        db_profile.interests = normalized.interests

    await session.flush()
    return normalized


@router.get(
    "/skills",
    response_model=DeveloperSkillProfile,
    summary="Get current developer skill profile",
    description="Returns the currently active developer skill profile. If authenticated, loads from persistent storage.",
    responses={
        200: {"description": "Current developer skill profile."},
    },
)
async def get_developer_skill_profile(
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_db),
) -> DeveloperSkillProfile:
    """Retrieve the developer skill profile (DB-backed if authenticated, in-memory otherwise)."""
    if current_user is not None:
        return await _load_db_profile(session, current_user)
    return profile_service.get_profile()


@router.post(
    "/skills",
    response_model=DeveloperSkillProfile,
    status_code=status.HTTP_200_OK,
    summary="Set current developer skill profile",
    description="Updates and normalizes the active developer skill profile. If authenticated, persists to PostgreSQL.",
    responses={
        200: {"description": "Updated normalized developer skill profile."},
        422: {"description": "Invalid profile payload format."},
    },
)
async def update_developer_skill_profile(
    profile: DeveloperSkillProfile,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_db),
) -> DeveloperSkillProfile:
    """Update and normalize the active developer skill profile (DB-backed if authenticated)."""
    if current_user is not None:
        return await _save_db_profile(session, current_user, profile)
    return profile_service.set_profile(profile)
