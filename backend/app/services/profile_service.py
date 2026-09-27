"""
Profile service managing current in-memory developer skill profile for Phase 10.
Does not require authentication or persistent user database accounts.
"""

import threading
from typing import Optional
from app.schemas.profile import DeveloperSkillProfile
from app.services.skill_normalizer import normalize_profile


class ProfileService:
    """
    Manages current developer skill profile in memory.
    Thread-safe storage supporting GET and POST operations.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Default empty profile
        self._current_profile: DeveloperSkillProfile = DeveloperSkillProfile(
            programming_languages=[],
            frameworks=[],
            tools=[],
            domains=[],
            experience_level="beginner",
            interests=[],
        )

    def get_profile(self) -> DeveloperSkillProfile:
        """Returns the current normalized developer skill profile."""
        with self._lock:
            return self._current_profile.model_copy()

    def set_profile(self, profile: DeveloperSkillProfile) -> DeveloperSkillProfile:
        """Normalizes and updates the current developer skill profile."""
        normalized = normalize_profile(profile)
        with self._lock:
            self._current_profile = normalized
            return self._current_profile.model_copy()

    def reset_profile(self) -> None:
        """Resets the profile to an empty state."""
        with self._lock:
            self._current_profile = DeveloperSkillProfile(
                programming_languages=[],
                frameworks=[],
                tools=[],
                domains=[],
                experience_level="beginner",
                interests=[],
            )


profile_service = ProfileService()
