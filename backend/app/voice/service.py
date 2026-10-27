"""
Voice Session and Token Management Service for OpenSource Copilot.

Coordinates:
- Generation of short-lived, room-scoped LiveKit access tokens.
- Secure propagation of authorized repository context into room session metadata.
- Validation of repository identifiers and branch references.
- Readiness and configuration verification for LiveKit and Sarvam AI.
"""

from datetime import timedelta
import json
import logging
import re
from typing import Optional
import uuid

from livekit import api

from app.core.config import settings
from app.models.entities import User
from app.voice.schemas import VoiceStatusResponse, VoiceTokenRequest, VoiceTokenResponse

logger = logging.getLogger(__name__)

REPO_IDENTIFIER_REGEX = re.compile(r"^[A-Za-z0-9_.-]+$")
BRANCH_REGEX = re.compile(r"^[A-Za-z0-9_./-]+$")


class VoiceServiceError(Exception):
    """Base exception for Voice Service errors."""
    pass


class VoiceNotConfiguredError(VoiceServiceError):
    """Raised when LiveKit or Sarvam AI credentials are not configured."""
    pass


VoiceConfigurationError = VoiceNotConfiguredError


class VoiceValidationError(VoiceServiceError):
    """Raised when repository or session parameters fail validation."""
    pass


class VoiceSessionService:
    """
    Manages LiveKit voice sessions and short-lived token generation
    with repository-scoped authorization and metadata.
    """

    def is_configured(self) -> bool:
        """Checks whether all necessary voice credentials are set."""
        return bool(
            settings.LIVEKIT_URL
            and settings.LIVEKIT_API_KEY
            and settings.LIVEKIT_API_SECRET
            and (settings.SARVAM_API_KEY or settings.LLM_API_KEY)
        )

    def get_status(self) -> VoiceStatusResponse:
        """Returns the current readiness and configuration status without leaking secrets."""
        livekit_ok = bool(settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET)
        sarvam_ok = bool(settings.SARVAM_API_KEY or settings.LLM_API_KEY)
        
        # Mask LiveKit URL for safe public status display
        masked_url = None
        if settings.LIVEKIT_URL:
            # Only show host and scheme, e.g. wss://example.livekit.cloud
            try:
                from urllib.parse import urlparse
                parsed = urlparse(settings.LIVEKIT_URL)
                masked_url = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                masked_url = "configured"

        return VoiceStatusResponse(
            configured=livekit_ok and sarvam_ok,
            livekit_configured=livekit_ok,
            sarvam_configured=sarvam_ok,
            livekit_url=masked_url,
            chat_model=settings.SARVAM_CHAT_MODEL,
            stt_model=settings.SARVAM_STT_MODEL,
            tts_model=settings.SARVAM_TTS_MODEL,
        )

    def create_session_token(
        self,
        request: VoiceTokenRequest,
        current_user: Optional[User] = None,
    ) -> VoiceTokenResponse:
        """
        Validates the request and issues a short-lived, room-scoped LiveKit access token.

        Security constraints:
        - Never exposes LIVEKIT_API_SECRET or SARVAM_API_KEY.
        - Room grant is locked strictly to a unique room name for this conversation.
        - Validates owner, repo, and branch formats to prevent injection.
        - Attaches repository context in room metadata for the voice agent worker.
        """
        if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
            raise VoiceNotConfiguredError(
                "LiveKit voice infrastructure is not configured. "
                "Please configure LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in the backend environment."
            )

        if not (settings.SARVAM_API_KEY or settings.LLM_API_KEY):
            raise VoiceNotConfiguredError(
                "Sarvam AI is not configured for voice processing. "
                "Please set SARVAM_API_KEY in your backend environment."
            )

        # Validate repository parameters if supplied
        owner = request.repository_owner.strip() if request.repository_owner else None
        repo = request.repository_name.strip() if request.repository_name else None
        branch = request.branch.strip() if request.branch else None

        if (owner and not repo) or (repo and not owner):
            raise VoiceValidationError("Both repository owner and repository name must be provided together.")

        if owner:
            if not REPO_IDENTIFIER_REGEX.match(owner):
                raise VoiceValidationError(f"Invalid repository owner '{owner}'. Only alphanumeric, dashes, and underscores allowed.")
            if len(owner) > 100:
                raise VoiceValidationError("Repository owner exceeds maximum length of 100 characters.")

        if repo:
            if not REPO_IDENTIFIER_REGEX.match(repo):
                raise VoiceValidationError(f"Invalid repository name '{repo}'. Only alphanumeric, dashes, and underscores allowed.")
            if len(repo) > 100:
                raise VoiceValidationError("Repository name exceeds maximum length of 100 characters.")

        if branch:
            if not BRANCH_REGEX.match(branch) or ".." in branch:
                raise VoiceValidationError(f"Invalid branch specification '{branch}'.")
            if len(branch) > 100:
                raise VoiceValidationError("Branch specification exceeds maximum length of 100 characters.")

        # Determine participant identity securely
        if current_user is not None:
            identity = f"user_{current_user.id}"
            display_name = current_user.display_name or current_user.email
        else:
            anon_id = uuid.uuid4().hex[:8]
            identity = f"anon_{anon_id}"
            display_name = f"Guest {anon_id}"

        # Determine room name
        session_id = uuid.uuid4().hex[:10]
        if owner and repo:
            safe_owner = re.sub(r"[^A-Za-z0-9_-]", "_", owner)
            safe_repo = re.sub(r"[^A-Za-z0-9_-]", "_", repo)
            room_name = f"repo-{safe_owner}-{safe_repo}-{session_id}"
        else:
            room_name = f"general-{session_id}"

        # Build room-scoped participant metadata
        metadata_payload = {
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "user_id": current_user.id if current_user else None,
            "identity": identity,
        }
        metadata_str = json.dumps(metadata_payload)

        # Issue LiveKit token
        ttl_seconds = settings.VOICE_SESSION_TIMEOUT_SECONDS
        grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )

        token = (
            api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            .with_identity(identity)
            .with_name(display_name)
            .with_metadata(metadata_str)
            .with_grants(grants)
            .with_ttl(timedelta(seconds=ttl_seconds))
            .to_jwt()
        )

        logger.info(
            "Issued LiveKit voice token for participant=%s room=%s repo=%s/%s branch=%s",
            identity,
            room_name,
            owner,
            repo,
            branch,
        )

        return VoiceTokenResponse(
            server_url=settings.LIVEKIT_URL,
            room_name=room_name,
            participant_token=token,
            participant_identity=identity,
            repository_owner=owner,
            repository_name=repo,
            branch=branch,
            expires_in=ttl_seconds,
        )


voice_session_service = VoiceSessionService()
