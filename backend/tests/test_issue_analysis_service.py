import json
import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.repository import (
    IssueAIAnalysisResponse,
    RepositoryInfo,
    TreeItem,
)
from app.services.llm_provider import LLMProvider
from app.services.issue_context_builder import IssueContextBuilder
from app.services.issue_analysis_service import (
    IssueAnalysisService,
    AIAnalysisValidationError,
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


VALID_ISSUE_ANALYSIS_DICT = {
    "issue_type": "bug",
    "difficulty": "intermediate",
    "difficulty_rationale": "Requires understanding request parsing edge cases and updating tests.",
    "required_skills": ["Python", "FastAPI", "pytest"],
    "skills_rationale": "The issue involves query parameter handling and pytest test suites.",
    "candidate_files": [
        {
            "path": "fastapi/routing.py",
            "reason": "Handles request parameter binding and routing execution",
            "confidence": "likely",
        },
        {
            "path": "tests/test_query.py",
            "reason": "Tests query parameter parsing edge cases",
            "confidence": "likely",
        },
    ],
    "affected_areas": ["routing", "parameter validation"],
    "investigation_steps": [
        "1. Reproduce the unexpected alias behavior using the provided code snippet.",
        "2. Inspect fastapi/routing.py where query params are extracted.",
        "3. Add a regression test in tests/test_query.py to verify the fix.",
    ],
    "prerequisites": "Python 3.10+, poetry or venv with pytest installed.",
    "ai_explanation": "When an alias with special characters is used in query parameters, validation fails with an unexpected status code.",
    "observed_evidence": [
        "Issue description reports 422 Unprocessable Entity for query param with alias.",
        "Reproduction script provided in issue description.",
    ],
    "inferences": [
        "The alias mapping lookup in routing logic likely does not normalize special characters.",
    ],
    "unknowns": [
        "Whether this behavior is intentional for backwards compatibility with starlette.",
    ],
    "confidence": "high",
}


def test_issue_context_builder_keywords():
    """Verify keywords are extracted from backticks, filenames, and descriptions."""
    builder = IssueContextBuilder()
    keywords = builder.extract_keywords_from_issue(
        title="Fix bug in `fastapi/routing.py` with alias",
        body="Getting error when using Query param alias in `test_query.py`. Check params.py.",
        labels=["bug", "routing"],
    )
    assert "fastapi/routing.py" in keywords
    assert "routing.py" in keywords
    assert "test_query.py" in keywords
    assert "params.py" in keywords
    assert "routing" in keywords


def test_issue_context_builder_ranking():
    """Verify candidate files matching keywords are ranked with positive scores."""
    builder = IssueContextBuilder()
    tree = [
        TreeItem(path="fastapi/routing.py", type="file", category="source"),
        TreeItem(path="fastapi/applications.py", type="file", category="source"),
        TreeItem(path="tests/test_query.py", type="file", category="test"),
        TreeItem(path="docs/index.md", type="file", category="documentation"),
    ]
    keywords = {"routing.py", "routing", "test_query.py"}
    ranked = builder.rank_candidate_files(tree, keywords)

    assert len(ranked) >= 2
    paths = [item.path for item, score in ranked]
    assert "fastapi/routing.py" in paths
    assert "tests/test_query.py" in paths
    # Top ranked should be fastapi/routing.py or tests/test_query.py
    assert ranked[0][1] > 0


def test_issue_context_builder_budget():
    """Verify context building enforces character limits."""
    builder = IssueContextBuilder(max_context_chars=1000)
    issue = {
        "number": 42,
        "title": "A very large issue title",
        "body": "X" * 5000,
        "labels": ["bug"],
        "user": "contributor",
        "state": "open",
    }
    repo = RepositoryInfo(
        owner="pallets",
        name="flask",
        full_name="pallets/flask",
        default_branch="main",
        visibility="public",
        stars=1000,
        forks=200,
        watchers=1000,
        open_issues_count=10,
    )
    tree = [TreeItem(path="src/flask/app.py", type="file", category="source")]

    context_str, stats = builder.build_context(
        issue=issue,
        repository=repo,
        languages={"Python": 100000},
        tree=tree,
    )

    assert len(context_str) <= 1200
    assert stats["total_context_chars"] <= 1200


@pytest.mark.asyncio
async def test_issue_analysis_service_orchestration_success():
    """Verify full issue analysis flow with fake provider returns IssueAIAnalysisResponse."""
    fake_provider = FakeLLMProvider(json.dumps(VALID_ISSUE_ANALYSIS_DICT))
    service = IssueAnalysisService(llm_provider=fake_provider)

    mock_repo = {
        "owner": "fastapi",
        "name": "fastapi",
        "full_name": "fastapi/fastapi",
        "default_branch": "master",
        "visibility": "public",
        "stars": 70000,
        "forks": 6000,
        "watchers": 70000,
        "open_issues_count": 50,
    }
    mock_issue = {
        "id": 1001,
        "number": 123,
        "title": "Bug in parameter alias",
        "body": "Alias does not work in fastapi/routing.py",
        "state": "open",
        "html_url": "https://github.com/fastapi/fastapi/issues/123",
        "labels": ["bug"],
        "user": "alice",
        "comments_count": 2,
    }
    mock_tree = {
        "tree": [
            {"path": "fastapi/routing.py", "type": "file", "category": "source"},
            {"path": "tests/test_query.py", "type": "file", "category": "test"},
        ],
        "truncated": False,
    }

    with patch("app.services.issue_analysis_service.github_service.fetch_repository", new=AsyncMock(return_value=mock_repo)), \
         patch("app.services.issue_analysis_service.github_service.fetch_languages", new=AsyncMock(return_value={"Python": 90000})), \
         patch("app.services.issue_analysis_service.github_service.fetch_readme", new=AsyncMock(return_value=None)), \
         patch("app.services.issue_analysis_service.github_service.fetch_single_issue", new=AsyncMock(return_value=mock_issue)), \
         patch("app.services.issue_analysis_service.repository_ingestion_service.get_repository_tree", new=AsyncMock(return_value=mock_tree)), \
         patch("app.services.issue_analysis_service.repository_ingestion_service.get_file_content", new=AsyncMock(return_value={"content": "def get_param(): pass", "is_binary": False})):

        response = await service.analyze_issue_with_ai(
            url="https://github.com/fastapi/fastapi",
            issue_number=123,
        )

        assert isinstance(response, IssueAIAnalysisResponse)
        assert response.issue_number == 123
        assert response.repository.owner == "fastapi"
        assert response.analysis.issue_type == "bug"
        assert response.analysis.difficulty == "intermediate"
        assert len(response.analysis.candidate_files) == 2
        assert response.analysis.candidate_files[0].path == "fastapi/routing.py"
        assert len(response.analysis.observed_evidence) > 0
        assert len(response.analysis.inferences) > 0


@pytest.mark.asyncio
async def test_issue_analysis_service_malformed_json():
    """Verify malformed JSON raises AIAnalysisValidationError."""
    fake_provider = FakeLLMProvider("Not JSON at all! Just text.")
    service = IssueAnalysisService(llm_provider=fake_provider)

    with patch("app.services.issue_analysis_service.github_service.fetch_repository", new=AsyncMock(return_value={"owner": "a", "name": "b", "full_name": "a/b", "default_branch": "main"})), \
         patch("app.services.issue_analysis_service.github_service.fetch_languages", new=AsyncMock(return_value={})), \
         patch("app.services.issue_analysis_service.github_service.fetch_readme", new=AsyncMock(return_value=None)), \
         patch("app.services.issue_analysis_service.github_service.fetch_single_issue", new=AsyncMock(return_value={"number": 1, "title": "t", "body": "b", "labels": []})), \
         patch("app.services.issue_analysis_service.repository_ingestion_service.get_repository_tree", new=AsyncMock(return_value={"tree": []})):

        with pytest.raises(AIAnalysisValidationError):
            await service.analyze_issue_with_ai(
                url="https://github.com/a/b",
                issue_number=1,
            )
