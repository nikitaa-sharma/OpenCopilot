"""
CLI entrypoint to run the LiveKit Voice Agent worker.

Usage:
    python -m app.voice.worker start
    python -m app.voice.worker dev
"""

import logging
import sys
from livekit.agents import WorkerOptions, cli

from app.core.config import settings
from app.voice.agent import prewarm_vad, voice_agent_entrypoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_worker")


def main():
    """Starts the LiveKit voice agent worker process."""
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        logger.error(
            "LiveKit credentials missing. Ensure LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET are set."
        )
        sys.exit(1)

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=voice_agent_entrypoint,
            prewarm_fnc=prewarm_vad,
            ws_url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
    )


if __name__ == "__main__":
    main()
