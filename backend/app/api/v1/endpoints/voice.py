"""
Voice Agent API endpoints for OpenSource Copilot.

Provides:
- POST /token: Generate short-lived, room-scoped LiveKit access token with repository context.
- GET /status: Check readiness and configuration status of voice components.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user_optional
from app.models.entities import User
from app.voice.schemas import VoiceStatusResponse, VoiceTokenRequest, VoiceTokenResponse
from app.voice.service import (
    VoiceNotConfiguredError,
    VoiceValidationError,
    voice_session_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=VoiceStatusResponse,
    summary="Voice assistant readiness status",
    description="Returns whether LiveKit and Sarvam AI credentials are configured for real-time voice sessions.",
)
async def get_voice_status() -> VoiceStatusResponse:
    """Check whether voice services are configured."""
    return voice_session_service.get_status()


@router.post(
    "/token",
    response_model=VoiceTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate room-scoped LiveKit voice token",
    description=(
        "Authenticates the user and issues a short-lived, room-scoped LiveKit access token "
        "with active repository authorization and metadata."
    ),
    responses={
        200: {"description": "Access token generated successfully."},
        400: {"description": "Invalid repository specification or branch parameter."},
        503: {"description": "Voice services (LiveKit or Sarvam AI) are not configured."},
    },
)
async def create_voice_token(
    request: VoiceTokenRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> VoiceTokenResponse:
    """Generate a secure, short-lived LiveKit room token."""
    try:
        return voice_session_service.create_session_token(
            request=request,
            current_user=current_user,
        )
    except VoiceNotConfiguredError as exc:
        logger.warning("Voice token request rejected - service not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except VoiceValidationError as exc:
        logger.warning("Voice token request rejected - validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error generating voice token: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize voice session. Please try again.",
        )
