from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Schema for health check endpoint response.
    """
    status: str = Field(default="ok", description="Current service health status")
    service: str = Field(default="OpenSource Copilot API", description="Service identifier")
