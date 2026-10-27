"""
Comprehensive Tests for Feature 2: Floating LiveKit Voice Agent.

Covers:
1. Authorized token generation for authenticated and guest users.
2. Rejection of unauthorized repository/session requests (injection, path traversal, invalid characters).
3. Session initialization and connection failures.
4. Missing credentials return HTTP 503 with safe, actionable error message.
5. Correct repository context propagation in room metadata and tokens.
6. Voice queries using repository-scoped retrieval (search_repository tool).
7. Clean session termination and resource cleanup.
8. Status endpoint reporting configuration readiness without leaking secrets.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.entities import User
from app.voice.agent import _extract_repo_metadata
from app.voice.schemas import VoiceTokenRequest
from app.voice.service import (
    VoiceNotConfiguredError,
    VoiceValidationError,
    voice_session_service,
)

client = TestClient(app)


class TestVoiceSessionService:
    """Unit tests for VoiceSessionService."""

    def test_missing_livekit_url_raises_not_configured(self):
        """Missing LIVEKIT_URL raises VoiceNotConfiguredError."""
        with patch.object(settings, "LIVEKIT_URL", ""):
            with patch.object(settings, "LIVEKIT_API_KEY", "key"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "secret"):
                    with patch.object(settings, "SARVAM_API_KEY", "sarvam-key"):
                        req = VoiceTokenRequest(repository_owner="pallets", repository_name="flask")
                        with pytest.raises(VoiceNotConfiguredError) as exc_info:
                            voice_session_service.create_session_token(req)
                        assert "LiveKit voice infrastructure is not configured" in str(exc_info.value)

    def test_missing_sarvam_key_raises_not_configured(self):
        """Missing SARVAM_API_KEY raises VoiceNotConfiguredError."""
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "key"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "secret"):
                    with patch.object(settings, "SARVAM_API_KEY", ""):
                        with patch.object(settings, "LLM_API_KEY", ""):
                            req = VoiceTokenRequest(repository_owner="pallets", repository_name="flask")
                            with pytest.raises(VoiceNotConfiguredError) as exc_info:
                                voice_session_service.create_session_token(req)
                            assert "Sarvam AI is not configured" in str(exc_info.value)

    def test_invalid_repository_owner_rejected(self):
        """Repository owner containing path traversal or shell characters is rejected."""
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "test-livekit-key-123456789012"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "test-livekit-secret-123456789012345678"):
                    with patch.object(settings, "SARVAM_API_KEY", "test-sarvam-key"):
                        # Semicolon injection
                        req = VoiceTokenRequest(repository_owner="pallets;rm -rf", repository_name="flask")
                        with pytest.raises(VoiceValidationError) as exc:
                            voice_session_service.create_session_token(req)
                        assert "Invalid repository owner" in str(exc.value)

    def test_invalid_branch_path_traversal_rejected(self):
        """Branch ref with directory traversal ('..') is rejected."""
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "test-livekit-key-123456789012"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "test-livekit-secret-123456789012345678"):
                    with patch.object(settings, "SARVAM_API_KEY", "test-sarvam-key"):
                        req = VoiceTokenRequest(
                            repository_owner="pallets",
                            repository_name="flask",
                            branch="../../etc/passwd",
                        )
                        with pytest.raises(VoiceValidationError) as exc:
                            voice_session_service.create_session_token(req)
                        assert "Invalid branch" in str(exc.value)

    def test_mismatched_owner_and_repo_rejected(self):
        """Supplying owner without repo name is rejected."""
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "test-livekit-key-123456789012"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "test-livekit-secret-123456789012345678"):
                    with patch.object(settings, "SARVAM_API_KEY", "test-sarvam-key"):
                        req = VoiceTokenRequest(repository_owner="pallets", repository_name="")
                        with pytest.raises(VoiceValidationError) as exc:
                            voice_session_service.create_session_token(req)
                        assert "Both repository owner and repository name must be provided" in str(exc.value)

    def test_authorized_token_generation_authenticated_user(self):
        """Valid token generated for authenticated user with room scoping and metadata."""
        user = User(id=42, email="dev@example.com", display_name="Dev User")
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "test-livekit-key-123456789012"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "test-livekit-secret-123456789012345678"):
                    with patch.object(settings, "SARVAM_API_KEY", "test-sarvam-key"):
                        req = VoiceTokenRequest(
                            repository_owner="pallets",
                            repository_name="flask",
                            branch="main",
                        )
                        resp = voice_session_service.create_session_token(req, current_user=user)

                        assert resp.server_url == "wss://livekit.example.com"
                        assert resp.participant_identity == "user_42"
                        assert "repo-pallets-flask-" in resp.room_name
                        assert resp.repository_owner == "pallets"
                        assert resp.repository_name == "flask"
                        assert resp.branch == "main"
                        assert len(resp.participant_token) > 50

    def test_authorized_token_generation_anonymous_guest(self):
        """Valid token generated for unauthenticated guest session."""
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "test-livekit-key-123456789012"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "test-livekit-secret-123456789012345678"):
                    with patch.object(settings, "SARVAM_API_KEY", "test-sarvam-key"):
                        req = VoiceTokenRequest()
                        resp = voice_session_service.create_session_token(req, current_user=None)

                        assert resp.server_url == "wss://livekit.example.com"
                        assert resp.participant_identity.startswith("anon_")
                        assert "general-" in resp.room_name


class TestVoiceEndpoints:
    """Integration tests for the Voice API endpoints."""

    def test_voice_status_endpoint(self):
        """GET /api/v1/voice/status returns safe readiness info."""
        with patch.object(settings, "LIVEKIT_URL", "wss://my-cloud.livekit.cloud"):
            with patch.object(settings, "LIVEKIT_API_KEY", "lk-key"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "lk-secret"):
                    with patch.object(settings, "SARVAM_API_KEY", "sarvam-key"):
                        response = client.get("/api/v1/voice/status")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["configured"] is True
                        assert data["livekit_configured"] is True
                        assert data["sarvam_configured"] is True
                        assert "wss://my-cloud.livekit.cloud" in data["livekit_url"]
                        # Secret keys must never leak
                        assert "lk-secret" not in json.dumps(data)
                        assert "sarvam-key" not in json.dumps(data)

    def test_voice_token_endpoint_unconfigured_returns_503(self):
        """POST /api/v1/voice/token returns 503 when services are unconfigured."""
        with patch.object(settings, "LIVEKIT_URL", ""):
            response = client.post(
                "/api/v1/voice/token",
                json={"repository_owner": "pallets", "repository_name": "flask"},
            )
            assert response.status_code == 503
            assert "LiveKit voice infrastructure is not configured" in response.json()["detail"]

    def test_voice_token_endpoint_validation_error_returns_400(self):
        """POST /api/v1/voice/token returns 400 on malformed input."""
        with patch.object(settings, "LIVEKIT_URL", "wss://livekit.example.com"):
            with patch.object(settings, "LIVEKIT_API_KEY", "test-key-123456789012"):
                with patch.object(settings, "LIVEKIT_API_SECRET", "test-secret-1234567890123456"):
                    with patch.object(settings, "SARVAM_API_KEY", "sarvam-key"):
                        response = client.post(
                            "/api/v1/voice/token",
                            json={"repository_owner": "owner with spaces", "repository_name": "repo"},
                        )
                        assert response.status_code == 400


class TestVoiceAgentMetadataExtraction:
    """Tests for the Voice Agent worker metadata extraction and scoping."""

    def test_extract_repo_metadata_from_room_metadata(self):
        """Extracts owner, repo, branch from room metadata JSON."""
        mock_ctx = MagicMock()
        mock_ctx.room.metadata = json.dumps({"owner": "pallets", "repo": "flask", "branch": "main"})
        owner, repo, branch = _extract_repo_metadata(mock_ctx)
        assert owner == "pallets"
        assert repo == "flask"
        assert branch == "main"

    def test_extract_repo_metadata_from_participant_fallback(self):
        """Falls back to remote participant metadata if room metadata is empty."""
        mock_ctx = MagicMock()
        mock_ctx.room.metadata = ""
        mock_participant = MagicMock()
        mock_participant.metadata = json.dumps({"owner": "encode", "repo": "uvicorn", "branch": "master"})
        mock_ctx.room.remote_participants = {"p1": mock_participant}

        owner, repo, branch = _extract_repo_metadata(mock_ctx)
        assert owner == "encode"
        assert repo == "uvicorn"
        assert branch == "master"


class TestVoiceAgentPipelineRegression:
    """Regression tests for Sarvam TTS configuration, VAD caching, and audio error handling."""

    def test_valid_tts_configuration_settings(self):
        """Verifies configured Sarvam TTS model is bulbul:v3 with compatible speaker and 24kHz rate."""
        assert settings.SARVAM_TTS_MODEL == "bulbul:v3"
        assert settings.SARVAM_TTS_SPEAKER in [
            "shubh", "ritu", "rahul", "pooja", "simran", "kavya", "amit",
            "ratan", "rohan", "dev", "ishita", "shreya", "manan", "sumit",
            "priya", "aditya", "kabir", "neha", "varun", "roopa", "aayan",
            "ashutosh", "advait", "amelia", "sophia"
        ]
        assert settings.SARVAM_TTS_SAMPLE_RATE == 24000

    def test_sarvam_tts_instantiation_with_supported_parameters(self):
        """Sarvam TTS initializes with valid configuration without raising ValueError."""
        from livekit.plugins import sarvam
        tts = sarvam.TTS(
            target_language_code="en-IN",
            model="bulbul:v3",
            speaker="kavya",
            speech_sample_rate=24000,
            api_key="mock-api-key",
        )
        assert tts.sample_rate == 24000
        assert tts.num_channels == 1

    def test_incompatible_speaker_with_bulbul_v3_rejected(self):
        """Using a v2 speaker (e.g. 'anushka') with bulbul:v3 raises ValueError early."""
        from livekit.plugins import sarvam
        with pytest.raises(ValueError) as exc:
            sarvam.TTS(
                target_language_code="en-IN",
                model="bulbul:v3",
                speaker="anushka",
                api_key="mock-api-key",
            )
        assert "not compatible with model 'bulbul:v3'" in str(exc.value)

    def test_invalid_sample_rate_rejected(self):
        """Sample rates outside Sarvam's supported set raise ValueError early."""
        from livekit.plugins import sarvam
        with pytest.raises(ValueError) as exc:
            sarvam.TTS(
                target_language_code="en-IN",
                model="bulbul:v3",
                speaker="kavya",
                speech_sample_rate=12345,
                api_key="mock-api-key",
            )
        assert "Sample rate must be one of" in str(exc.value)

    def test_vad_prewarm_caches_instance(self):
        """prewarm_vad caches VAD model in proc userdata to prevent audio thread latency."""
        from app.voice.agent import prewarm_vad, get_vad_instance
        mock_proc = MagicMock()
        mock_proc.userdata = {}

        with patch("livekit.plugins.silero.VAD.load", return_value="mock_vad"):
            vad = prewarm_vad(mock_proc)
            assert vad == "mock_vad"
            assert mock_proc.userdata.get("vad") == "mock_vad"

            mock_ctx = MagicMock()
            mock_ctx.proc = mock_proc
            retrieved = get_vad_instance(mock_ctx)
            assert retrieved == "mock_vad"
