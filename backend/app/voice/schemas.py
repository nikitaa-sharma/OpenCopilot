"""
Pydantic schemas for the Voice Assistant feature (LiveKit + Sarvam AI).
"""

from typing import Optional
from pydantic import BaseModel, Field


class VoiceTokenRequest(BaseModel):
    """Request payload to initiate a room-scoped LiveKit voice session."""
    repository_owner: Optional[str] = Field(None, max_length=100, description="Owner of the GitHub repository")
    repository_name: Optional[str] = Field(None, max_length=100, description="Name of the GitHub repository")
    branch: Optional[str] = Field(None, max_length=100, description="Repository branch being inspected")
    room_name: Optional[str] = Field(None, max_length=128, description="Optional custom room name")


class VoiceTokenResponse(BaseModel):
    """Response payload containing temporary room-scoped credentials."""
    server_url: str = Field(..., description="LiveKit WebSocket URL to connect to")
    room_name: str = Field(..., description="Room identifier scoped to this session")
    participant_token: str = Field(..., description="Short-lived, room-scoped LiveKit access token")
    participant_identity: str = Field(..., description="Unique participant identity")
    repository_owner: Optional[str] = Field(None, description="Active repository owner context")
    repository_name: Optional[str] = Field(None, description="Active repository name context")
    branch: Optional[str] = Field(None, description="Active branch context")
    expires_in: int = Field(..., description="Token validity in seconds")


class VoiceStatusResponse(BaseModel):
    """Voice assistant backend configuration and readiness status."""
    configured: bool = Field(..., description="Whether both LiveKit and Sarvam AI are configured")
    livekit_configured: bool = Field(..., description="Whether LiveKit credentials and URL are present")
    sarvam_configured: bool = Field(..., description="Whether SARVAM_API_KEY is present")
    livekit_url: Optional[str] = Field(None, description="Configured LiveKit URL (masked/host only)")
    chat_model: str = Field(..., description="Active Sarvam chat model")
    stt_model: str = Field(..., description="Active Sarvam STT model")
    tts_model: str = Field(..., description="Active Sarvam TTS model")
