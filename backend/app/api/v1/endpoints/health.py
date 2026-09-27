from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="API Health Check")
async def health_check() -> HealthResponse:
    """
    Returns the operational health status of the backend API service.
    """
    return HealthResponse(
        status="ok",
        service="OpenSource Copilot API",
    )
