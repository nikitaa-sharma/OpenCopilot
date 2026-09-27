"""
Entrypoint module for Vercel and serverless runners.
Exports the FastAPI application instance from app.main.
"""

from app.main import app

__all__ = ["app"]
