import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.repository import (
    ContextStats,
    RepositoryAIAnalysis,
    RepositoryAIAnalysisResponse,
    RepositoryRef,
    TestingOverview,
)
from app.services.llm_provider import (
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.services.repository_analysis_service import AIAnalysisValidationError

client = TestClient(app)

MOCK_RESPONSE = RepositoryAIAnalysisResponse(
    repository=RepositoryRef(owner="pallets", name="flask", branch="main"),
    analysis=RepositoryAIAnalysis(
        summary="Flask is a lightweight WSGI web application framework.",
        purpose="Provides a simple, extensible foundation for building web applications.",
        architecture="WSGI-based microframework delegating to Werkzeug and Jinja.",
        technology_stack=[],
        important_directories=[],
        important_files=[],
        entry_points=[],
        testing=TestingOverview(framework="pytest", structure="tests/"),
        beginner_explanation="Start by checking examples/ and src/flask/app.py.",
        confidence_assessment="High confidence based on repository context.",
    ),
    provider="ollama",
    model="llama3",
    context_stats=ContextStats(files_included=5, total_context_chars=12000),
)


def test_analyze_ai_endpoint_success():
    """Verify POST /api/v1/repositories/analyze-ai returns 200 with schema."""
    with patch(
        "app.api.v1.endpoints.repositories.repository_analysis_service.analyze_repository_with_ai",
        new=AsyncMock(return_value=MOCK_RESPONSE),
    ):
        response = client.post(
            "/api/v1/repositories/analyze-ai",
            json={"url": "https://github.com/pallets/flask"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["repository"]["owner"] == "pallets"
        assert data["repository"]["name"] == "flask"
        assert data["analysis"]["summary"] == MOCK_RESPONSE.analysis.summary
        assert data["provider"] == "ollama"


def test_analyze_ai_endpoint_invalid_url():
    """Verify invalid repository URL returns 400 Bad Request."""
    response = client.post(
        "/api/v1/repositories/analyze-ai",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Unsupported domain" in detail or "GitHub" in detail



def test_analyze_ai_endpoint_ollama_unavailable():
    """Verify 503 is returned when Ollama is offline."""
    with patch(
        "app.api.v1.endpoints.repositories.repository_analysis_service.analyze_repository_with_ai",
        new=AsyncMock(side_effect=LLMProviderUnavailableError(
            "AI provider is unavailable. Make sure Ollama is running at http://localhost:11434 and 'llama3' is installed."
        )),
    ):
        response = client.post(
            "/api/v1/repositories/analyze-ai",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 503
        assert "Make sure Ollama is running" in response.json()["detail"]


def test_analyze_ai_endpoint_model_not_found():
    """Verify 404 is returned when the model is not installed."""
    with patch(
        "app.api.v1.endpoints.repositories.repository_analysis_service.analyze_repository_with_ai",
        new=AsyncMock(side_effect=LLMModelNotFoundError(
            "Model 'llama3' was not found in Ollama. Run `ollama pull llama3` in your terminal."
        )),
    ):
        response = client.post(
            "/api/v1/repositories/analyze-ai",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 404
        assert "ollama pull llama3" in response.json()["detail"]


def test_analyze_ai_endpoint_timeout():
    """Verify 504 Gateway Timeout is returned on LLM timeout."""
    with patch(
        "app.api.v1.endpoints.repositories.repository_analysis_service.analyze_repository_with_ai",
        new=AsyncMock(side_effect=LLMTimeoutError("AI provider request timed out after 120s.")),
    ):
        response = client.post(
            "/api/v1/repositories/analyze-ai",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]


def test_analyze_ai_endpoint_validation_error():
    """Verify 502 Bad Gateway is returned on model schema validation error."""
    with patch(
        "app.api.v1.endpoints.repositories.repository_analysis_service.analyze_repository_with_ai",
        new=AsyncMock(side_effect=AIAnalysisValidationError("Model returned invalid schema")),
    ):
        response = client.post(
            "/api/v1/repositories/analyze-ai",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 502
        assert "Model returned invalid schema" in response.json()["detail"]
