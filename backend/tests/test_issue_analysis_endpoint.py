import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.repository import (
    CandidateFile,
    ContextStats,
    IssueAIAnalysis,
    IssueAIAnalysisResponse,
    RepositoryRef,
)
from app.services.github_service import GitHubNotFoundError
from app.services.llm_provider import (
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.services.repository_analysis_service import AIAnalysisValidationError

client = TestClient(app)

MOCK_ISSUE_RESPONSE = IssueAIAnalysisResponse(
    repository=RepositoryRef(owner="pallets", name="flask", branch="main"),
    issue_number=123,
    issue_title="Typo in blueprint routing logic",
    issue_url="https://github.com/pallets/flask/issues/123",
    analysis=IssueAIAnalysis(
        issue_type="bug",
        difficulty="beginner",
        difficulty_rationale="Small routing bug with localized changes.",
        required_skills=["Python", "Flask"],
        skills_rationale="Requires familiarity with Flask blueprints.",
        candidate_files=[
            CandidateFile(
                path="src/flask/blueprints.py",
                reason="Defines blueprint routing registrations",
                confidence="likely",
            )
        ],
        affected_areas=["blueprints", "routing"],
        investigation_steps=["Check blueprints.py registration method."],
        prerequisites="Python 3.10+",
        ai_explanation="A blueprint method has an erroneous variable name.",
        observed_evidence=["Issue body points to blueprints.py line 45."],
        inferences=["Likely a simple variable rename."],
        unknowns=["Whether third-party extensions rely on the old name."],
        confidence="high",
    ),
    provider="ollama",
    model="llama3",
    context_stats=ContextStats(files_included=1, total_context_chars=4000),
)


def test_analyze_issue_endpoint_success():
    """Verify POST /api/v1/repositories/issues/analyze returns 200 with schema."""
    with patch(
        "app.api.v1.endpoints.repositories.issue_analysis_service.analyze_issue_with_ai",
        new=AsyncMock(return_value=MOCK_ISSUE_RESPONSE),
    ):
        response = client.post(
            "/api/v1/repositories/issues/analyze",
            json={"url": "https://github.com/pallets/flask", "issue_number": 123},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["issue_number"] == 123
        assert data["repository"]["owner"] == "pallets"
        assert data["analysis"]["issue_type"] == "bug"
        assert data["analysis"]["difficulty"] == "beginner"
        assert len(data["analysis"]["candidate_files"]) == 1
        assert data["analysis"]["candidate_files"][0]["path"] == "src/flask/blueprints.py"
        assert data["provider"] == "ollama"


def test_analyze_issue_endpoint_invalid_url():
    """Verify invalid repository URL returns 400 Bad Request."""
    response = client.post(
        "/api/v1/repositories/issues/analyze",
        json={"url": "invalid-url", "issue_number": 123},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Unsupported domain" in detail or "GitHub" in detail


def test_analyze_issue_endpoint_invalid_issue_number():
    """Verify issue_number < 1 returns 422 Unprocessable Entity."""
    response = client.post(
        "/api/v1/repositories/issues/analyze",
        json={"url": "https://github.com/pallets/flask", "issue_number": 0},
    )
    assert response.status_code == 422


def test_analyze_issue_endpoint_not_found():
    """Verify 404 is returned when issue does not exist."""
    with patch(
        "app.api.v1.endpoints.repositories.issue_analysis_service.analyze_issue_with_ai",
        new=AsyncMock(side_effect=GitHubNotFoundError("Issue #999 not found in repository pallets/flask.")),
    ):
        response = client.post(
            "/api/v1/repositories/issues/analyze",
            json={"url": "https://github.com/pallets/flask", "issue_number": 999},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_analyze_issue_endpoint_llm_unavailable():
    """Verify 503 is returned when LLM provider is offline."""
    with patch(
        "app.api.v1.endpoints.repositories.issue_analysis_service.analyze_issue_with_ai",
        new=AsyncMock(side_effect=LLMProviderUnavailableError("Ollama is offline.")),
    ):
        response = client.post(
            "/api/v1/repositories/issues/analyze",
            json={"url": "https://github.com/pallets/flask", "issue_number": 123},
        )
        assert response.status_code == 503
        assert "offline" in response.json()["detail"].lower()


def test_analyze_issue_endpoint_timeout():
    """Verify 504 is returned when LLM provider times out."""
    with patch(
        "app.api.v1.endpoints.repositories.issue_analysis_service.analyze_issue_with_ai",
        new=AsyncMock(side_effect=LLMTimeoutError("LLM timed out.")),
    ):
        response = client.post(
            "/api/v1/repositories/issues/analyze",
            json={"url": "https://github.com/pallets/flask", "issue_number": 123},
        )
        assert response.status_code == 504


def test_analyze_issue_endpoint_validation_error():
    """Verify 502 is returned when LLM output cannot be validated."""
    with patch(
        "app.api.v1.endpoints.repositories.issue_analysis_service.analyze_issue_with_ai",
        new=AsyncMock(side_effect=AIAnalysisValidationError("Malformed JSON")),
    ):
        response = client.post(
            "/api/v1/repositories/issues/analyze",
            json={"url": "https://github.com/pallets/flask", "issue_number": 123},
        )
        assert response.status_code == 502
