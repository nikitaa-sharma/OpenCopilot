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


class MultiResponseLLMProvider(LLMProvider):
    """Mock provider that returns a sequence of responses across multiple generate calls."""

    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0
        self.model = "multi-mock-model"

    async def generate(self, prompt: str, system_prompt=None, temperature=None, max_tokens=None, json_mode=False) -> str:
        resp = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1
        return resp

    async def generate_embeddings(self, texts):
        return [[0.0] * 128 for _ in texts]


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
async def test_service_successful_corrective_retry():
    """Verify service performs single corrective retry when first response is invalid metadata."""
    invalid_metadata_response = json.dumps({
        "name": "effect",
        "owner": "Effect-TS",
        "stars": 9000,
        "description": "An ecosystem of tools to build robust applications in TypeScript.",
    })
    valid_retry_response = json.dumps(VALID_ANALYSIS_DICT)

    provider = MultiResponseLLMProvider([invalid_metadata_response, valid_retry_response])
    service = RepositoryAnalysisService(llm_provider=provider)

    with patch("app.services.repository_analysis_service.github_service") as mock_gh, \
         patch("app.services.repository_analysis_service.repository_ingestion_service") as mock_ingest:

        mock_gh.fetch_repository = AsyncMock(return_value={
            "owner": "Effect-TS", "name": "effect", "full_name": "Effect-TS/effect", "default_branch": "main"
        })
        mock_gh.fetch_languages = AsyncMock(return_value={"TypeScript": 500000})
        mock_gh.fetch_readme = AsyncMock(return_value={"name": "README.md", "content": "# Effect"})
        mock_ingest.get_repository_tree = AsyncMock(return_value={"tree": []})

        result = await service.analyze_repository_with_ai("https://github.com/Effect-TS/effect")

        assert isinstance(result, RepositoryAIAnalysisResponse)
        assert provider.call_count == 2
        assert result.analysis.summary == VALID_ANALYSIS_DICT["summary"]


@pytest.mark.asyncio
async def test_service_failed_corrective_retry_raises_validation_error():
    """Verify service raises AIAnalysisValidationError when corrective retry also fails."""
    invalid_resp_1 = "Non-JSON gibberish"
    invalid_resp_2 = json.dumps({"only_field": "still_missing_required"})

    provider = MultiResponseLLMProvider([invalid_resp_1, invalid_resp_2])
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

        assert provider.call_count == 2
        assert "after corrective retry" in str(exc_info.value) or "Missing required fields" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_missing_file_graceful_continuation():
    """Verify that a 404/failure retrieving a single file does not break the entire analysis."""
    provider = FakeLLMProvider(json.dumps(VALID_ANALYSIS_DICT))
    service = RepositoryAnalysisService(llm_provider=provider)

    with patch("app.services.repository_analysis_service.github_service") as mock_gh, \
         patch("app.services.repository_analysis_service.repository_ingestion_service") as mock_ingest:

        mock_gh.fetch_repository = AsyncMock(return_value={
            "owner": "Effect-TS", "name": "effect", "full_name": "Effect-TS/effect", "default_branch": "main"
        })
        mock_gh.fetch_languages = AsyncMock(return_value={"TypeScript": 20000})
        mock_gh.fetch_readme = AsyncMock(return_value=None)

        mock_ingest.get_repository_tree = AsyncMock(return_value={
            "tree": [
                {"path": "package.json", "type": "file", "category": "configuration"},
                {"path": "src/index.ts", "type": "file", "category": "source"},
            ]
        })
        # Simulate package.json succeeding, src/index.ts raising 404
        async def mock_get_content(owner, repo, path, branch):
            if path == "package.json":
                return {"path": "package.json", "name": "package.json", "is_binary": False, "content": "{\"name\": \"effect\"}"}
            raise Exception("File not found 404")

        mock_ingest.get_file_content = AsyncMock(side_effect=mock_get_content)

        result = await service.analyze_repository_with_ai("https://github.com/Effect-TS/effect")
        assert isinstance(result, RepositoryAIAnalysisResponse)
        assert result.repository.name == "effect"
        assert result.analysis.summary == VALID_ANALYSIS_DICT["summary"]


@pytest.mark.asyncio
async def test_service_typescript_repository_analysis():
    """Verify analysis of a TypeScript repository like Effect-TS/effect."""
    ts_analysis_dict = {
        "summary": "Effect is a comprehensive standard library for TypeScript providing functional primitives.",
        "purpose": "Provides type-safe concurrency, error management, and dependency injection in TypeScript.",
        "architecture": "Modular package architecture built around functional effects and streaming fibers.",
        "technology_stack": [
            {"name": "TypeScript", "category": "language", "evidence": "tsconfig.json, package.json"},
            {"name": "Effect", "category": "library", "evidence": "src/index.ts"},
            {"name": "Vitest", "category": "testing", "evidence": "vitest.config.ts"},
        ],
        "important_directories": [
            {"path": "src", "explanation": "Core effect runtime and type combinators", "evidence": "Observed 50+ ts modules"},
            {"path": "test", "explanation": "Unit and property tests", "evidence": "Vitest test suites"},
        ],
        "important_files": [
            {"path": "package.json", "reason": "Defines package scripts and exports", "evidence": "Manifest file"},
            {"path": "tsconfig.json", "reason": "TypeScript compiler options", "evidence": "TS configuration"},
        ],
        "entry_points": [
            {"path": "src/index.ts", "description": "Main library export entry point", "confidence": "high"},
        ],
        "testing": {
            "framework": "Vitest",
            "structure": "test/ directory with *.test.ts files",
            "evidence": "vitest.config.ts",
        },
        "beginner_explanation": "Read the README and explore src/Effect.ts to understand the core type.",
        "confidence_assessment": "High confidence grounded in package manifests and TypeScript sources.",
    }

    provider = FakeLLMProvider(json.dumps(ts_analysis_dict))
    service = RepositoryAnalysisService(llm_provider=provider)

    with patch("app.services.repository_analysis_service.github_service") as mock_gh, \
         patch("app.services.repository_analysis_service.repository_ingestion_service") as mock_ingest:

        mock_gh.fetch_repository = AsyncMock(return_value={
            "owner": "Effect-TS", "name": "effect", "full_name": "Effect-TS/effect", "default_branch": "main"
        })
        mock_gh.fetch_languages = AsyncMock(return_value={"TypeScript": 100000})
        mock_gh.fetch_readme = AsyncMock(return_value={"name": "README.md", "content": "# Effect"})
        mock_ingest.get_repository_tree = AsyncMock(return_value={
            "tree": [
                {"path": "package.json", "type": "file", "category": "configuration"},
                {"path": "tsconfig.json", "type": "file", "category": "configuration"},
                {"path": "src/index.ts", "type": "file", "category": "source"},
            ]
        })
        mock_ingest.get_file_content = AsyncMock(return_value={
            "path": "src/index.ts", "name": "index.ts", "is_binary": False, "content": "export * from './Effect';"
        })

        result = await service.analyze_repository_with_ai("https://github.com/Effect-TS/effect")
        assert isinstance(result, RepositoryAIAnalysisResponse)
        assert result.repository.owner == "Effect-TS"
        assert result.repository.name == "effect"
        assert "Effect is a comprehensive" in result.analysis.summary
        assert result.analysis.testing.framework == "Vitest"
