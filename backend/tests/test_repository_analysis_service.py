import json
import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.repository import RepositoryAIAnalysisResponse
from app.services.llm_provider import LLMProvider
from app.services.repository_analysis_service import (
    RepositoryAnalysisService,
    AIAnalysisValidationError,
    sanitize_json_response,
)


class FakeLLMProvider(LLMProvider):
    """Mock provider for unit testing without network or Ollama calls."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.model = "fake-model"

    async def generate(self, prompt: str, system_prompt=None, temperature=None, max_tokens=None, json_mode=False) -> str:
        return self.response_text

    async def generate_embeddings(self, texts):
        return [[0.0] * 128 for _ in texts]


VALID_ANALYSIS_DICT = {
    "summary": "A high-performance web framework for Python.",
    "purpose": "Simplifies building REST APIs with automatic OpenAPI docs.",
    "architecture": "Layered architecture with routing, dependency injection, and data validation.",
    "technology_stack": [
        {"name": "Python", "category": "language", "evidence": "Language statistics"},
        {"name": "FastAPI", "category": "framework", "evidence": "pyproject.toml"},
    ],
    "important_directories": [
        {"path": "fastapi", "explanation": "Core framework code", "evidence": "Contains main framework logic"},
    ],
    "important_files": [
        {"path": "fastapi/applications.py", "reason": "Defines FastAPI app class", "evidence": "Class FastAPI"},
    ],
    "entry_points": [
        {"path": "fastapi/__init__.py", "description": "Package public exports", "confidence": "high"},
    ],
    "testing": {
        "framework": "pytest",
        "structure": "tests/ directory",
        "evidence": "tests/test_main.py",
    },
    "beginner_explanation": "Start by exploring tutorial docs in docs/ and looking at basic examples.",
    "confidence_assessment": "High confidence based on pyproject.toml and source tree.",
}


def test_sanitize_json_response():
    """Verify markdown fences and whitespace are stripped cleanly."""
    raw = "```json\n{\"summary\": \"Clean\"}\n```"
    assert sanitize_json_response(raw) == '{"summary": "Clean"}'

    with_preamble = "Here is the response:\n{\"summary\": \"Clean\"}\nHope this helps!"
    assert sanitize_json_response(with_preamble) == '{"summary": "Clean"}'


@pytest.mark.asyncio
async def test_service_successful_analysis():
    """Verify repository analysis service coordinates context and returns validated response."""
    provider = FakeLLMProvider(json.dumps(VALID_ANALYSIS_DICT))
    service = RepositoryAnalysisService(llm_provider=provider)

    with patch("app.services.repository_analysis_service.github_service") as mock_gh, \
         patch("app.services.repository_analysis_service.repository_ingestion_service") as mock_ingest:

        mock_gh.fetch_repository = AsyncMock(return_value={
            "owner": "test-owner",
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
            "default_branch": "main",
            "stars": 100,
            "forks": 10,
            "open_issues_count": 5,
        })
        mock_gh.fetch_languages = AsyncMock(return_value={"Python": 5000})
        mock_gh.fetch_readme = AsyncMock(return_value={"name": "README.md", "content": "# Test Repo"})

        mock_ingest.get_repository_tree = AsyncMock(return_value={
            "tree": [
                {"path": "README.md", "type": "file", "category": "documentation"},
                {"path": "app.py", "type": "file", "category": "source"},
            ]
        })
        mock_ingest.get_file_content = AsyncMock(return_value={
            "path": "app.py",
            "name": "app.py",
            "is_binary": False,
            "content": "from fastapi import FastAPI\napp = FastAPI()",
        })

        result = await service.analyze_repository_with_ai("https://github.com/test-owner/test-repo")

        assert isinstance(result, RepositoryAIAnalysisResponse)
        assert result.repository.owner == "test-owner"
        assert result.repository.name == "test-repo"
        assert result.analysis.summary == VALID_ANALYSIS_DICT["summary"]
        assert len(result.analysis.technology_stack) == 2
        assert result.analysis.testing.framework == "pytest"


@pytest.mark.asyncio
async def test_service_malformed_json_error():
    """Verify invalid JSON raises AIAnalysisValidationError."""
    provider = FakeLLMProvider("Not valid JSON at all")
    service = RepositoryAnalysisService(llm_provider=provider)

    with patch("app.services.repository_analysis_service.github_service") as mock_gh, \
         patch("app.services.repository_analysis_service.repository_ingestion_service") as mock_ingest:

        mock_gh.fetch_repository = AsyncMock(return_value={
            "owner": "test-owner", "name": "test-repo", "full_name": "test-owner/test-repo", "default_branch": "main"
        })
        mock_gh.fetch_languages = AsyncMock(return_value={})
        mock_gh.fetch_readme = AsyncMock(return_value=None)
        mock_ingest.get_repository_tree = AsyncMock(return_value={"tree": []})

        with pytest.raises(AIAnalysisValidationError) as exc_info:
            await service.analyze_repository_with_ai("https://github.com/test-owner/test-repo")

        assert "could not be parsed as JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_missing_fields_validation_error():
    """Verify missing required fields raises AIAnalysisValidationError."""
    incomplete = {"summary": "Only summary provided"}
    provider = FakeLLMProvider(json.dumps(incomplete))
    service = RepositoryAnalysisService(llm_provider=provider)

    with patch("app.services.repository_analysis_service.github_service") as mock_gh, \
         patch("app.services.repository_analysis_service.repository_ingestion_service") as mock_ingest:

        mock_gh.fetch_repository = AsyncMock(return_value={
            "owner": "test-owner", "name": "test-repo", "full_name": "test-owner/test-repo", "default_branch": "main"
        })
        mock_gh.fetch_languages = AsyncMock(return_value={})
        mock_gh.fetch_readme = AsyncMock(return_value=None)
        mock_ingest.get_repository_tree = AsyncMock(return_value={"tree": []})

        with pytest.raises(AIAnalysisValidationError) as exc_info:
            await service.analyze_repository_with_ai("https://github.com/test-owner/test-repo")

        assert "did not match the expected repository analysis schema" in str(exc_info.value)
