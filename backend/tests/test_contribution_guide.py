"""
Tests for Phase 11: AI Contribution Guide.

Covers:
1. Service-level response parsing (direct JSON, markdown code fence, unparseable text).
2. Strict source validation: hallucinated file paths stripped, verified paths preserved.
3. No-context fallback handling without invoking the LLM.
4. End-to-end service orchestration with mocked GitHub issue, RAG context, and LLM output.
5. Personalization with DeveloperSkillProfile.
6. API endpoint input validation (missing owner/repo, non-positive issue number).
7. API endpoint success and error handling (400, 404, 403, 503, 504, 500).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.contribution.context import ContributionContextData
from app.contribution.models import (
    ContributionGuide,
    ContributionGuideEvidence,
    ContributionGuideRequest,
    ContributionGuideResponse,
    ContributionGuideUnderstanding,
)
from app.contribution.service import ContributionGuideService
from app.main import app
from app.rag.models import RepositoryChunk, RetrievedChunk
from app.schemas.profile import DeveloperSkillProfile
from app.schemas.repository import IssueItem
from app.services.github_service import (
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubServiceError,
)
from app.services.llm_provider import (
    LLMProvider,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)

client = TestClient(app)


def _make_retrieved_chunk(
    file_path: str = "src/flask/app.py",
    content: str = "class Flask:\n    def wsgi_app(self, environ, start_response):\n        pass",
    score: float = 0.92,
    start_line: int = 10,
    end_line: int = 30,
) -> RetrievedChunk:
    chunk = RepositoryChunk(
        chunk_id=f"pallets/flask:{file_path}:0",
        repository="pallets/flask",
        file_path=file_path,
        language="Python",
        category="source",
        chunk_index=0,
        start_line=start_line,
        end_line=end_line,
        content=content,
        metadata={},
    )
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        matched_terms=["flask", "wsgi_app"],
        retrieval_reason=f"Vector semantic similarity: {score:.4f}",
    )


SAMPLE_LLM_GUIDE_OUTPUT = {
    "issue_understanding": {
        "summary": "Fix route handling regression in Flask dispatch",
        "problem": "Subdomain dispatching fails when route url contains trailing slashes.",
        "expected_outcome": "Trailing slashes should be preserved or redirected cleanly.",
    },
    "prerequisites": [
        "Python 3.10+ installed",
        "Poetry or pip with dev dependencies",
        "Familiarity with Werkzeug routing rules",
    ],
    "relevant_files": [
        {
            "path": "src/flask/app.py",
            "role": "source",
            "reason": "Contains main wsgi_app dispatch logic",
        },
        {
            "path": "fake/nonexistent/module.py",
            "role": "source",
            "reason": "Hallucinated file that should be stripped",
        },
    ],
    "implementation_plan": [
        {
            "step": 1,
            "title": "Inspect dispatch method",
            "description": "Examine wsgi_app trailing slash normalization in src/flask/app.py.",
            "files": ["src/flask/app.py"],
        },
        {
            "step": 2,
            "title": "Add test case",
            "description": "Write a regression test covering subdomain routing with trailing slashes.",
            "files": ["tests/test_routing.py"],
        },
    ],
    "code_areas": [
        {
            "path": "src/flask/app.py",
            "area": "Flask.wsgi_app",
            "guidance": "Verify environ handling before delegating to dispatcher.",
        }
    ],
    "testing_plan": [
        {
            "type": "unit",
            "description": "Run pytest tests/test_routing.py -k test_subdomain_slash",
            "files": ["tests/test_routing.py"],
        }
    ],
    "documentation_plan": [
        "Update docstring for wsgi_app noting the trailing slash handling."
    ],
    "pull_request_checklist": [
        "Run pytest to ensure all test suites pass",
        "Run ruff check / flake8 linting",
        "Reference issue #157 in the pull request description",
    ],
    "learning_opportunities": [
        "WSGI application protocols and environ dictionaries",
        "URL dispatch mechanics in Python web frameworks",
    ],
    "uncertainties": [
        "Check whether this affects blueprints or only root app routes."
    ],
    "evidence": [
        {
            "path": "src/flask/app.py",
            "start_line": 10,
            "end_line": 30,
            "reason": "Class Flask wsgi_app definition",
        },
        {
            "path": "fake/hallucinated.py",
            "start_line": 1,
            "end_line": 10,
            "reason": "Hallucinated chunk",
        },
    ],
}


class TestContributionGuideServiceDomain:
    """Unit tests for the ContributionGuideService internal methods and domain logic."""

    def test_safe_parse_response_direct_json(self):
        service = ContributionGuideService()
        raw = json.dumps({"test_key": "test_value"})
        parsed = service._safe_parse_response(raw)
        assert parsed == {"test_key": "test_value"}

    def test_safe_parse_response_markdown_fence(self):
        service = ContributionGuideService()
        raw = "```json\n" + json.dumps({"key": "val"}) + "\n```"
        parsed = service._safe_parse_response(raw)
        assert parsed == {"key": "val"}

    def test_safe_parse_response_unparseable_returns_fallback(self):
        service = ContributionGuideService()
        raw = "This is a plain text response from the model without any json."
        parsed = service._safe_parse_response(raw)
        assert isinstance(parsed, dict)
        assert "issue_understanding" in parsed
        assert parsed["issue_understanding"]["summary"] == "Unable to parse structured guide."

    def test_source_validation_strips_hallucinations(self):
        service = ContributionGuideService()
        evidence_item = ContributionGuideEvidence(
            path="src/flask/app.py",
            start_line=10,
            end_line=30,
            category="source",
            score=0.92,
        )

        cited_evidence = [
            {"path": "src/flask/app.py", "start_line": 10, "end_line": 30},
            {"path": "fake/unretrieved/file.py", "start_line": 1, "end_line": 10},
        ]

        validated = service._validate_sources(cited_evidence, [evidence_item])
        paths = [s.path for s in validated]
        assert "src/flask/app.py" in paths
        assert "fake/unretrieved/file.py" not in paths

    def test_source_validation_fallback_when_all_hallucinated(self):
        service = ContributionGuideService()
        retrieved_evidence = [
            ContributionGuideEvidence(
                path="src/flask/app.py",
                start_line=10,
                end_line=30,
                category="source",
                score=0.92,
            )
        ]
        cited_evidence = [
            {"path": "fake/one.py"},
            {"path": "fake/two.py"},
        ]
        validated = service._validate_sources(cited_evidence, retrieved_evidence)
        # When all cited sources are hallucinated, falls back to actual retrieved evidence
        assert len(validated) == 1
        assert validated[0].path == "src/flask/app.py"

    def test_build_guide_filters_hallucinated_relevant_files(self):
        service = ContributionGuideService()
        retrieved_evidence = [
            ContributionGuideEvidence(
                path="src/flask/app.py",
                start_line=10,
                end_line=30,
                category="source",
                score=0.92,
            )
        ]
        guide = service._build_guide(
            parsed=SAMPLE_LLM_GUIDE_OUTPUT,
            validated_evidence=retrieved_evidence,
        )
        assert isinstance(guide, ContributionGuide)
        assert guide.issue_understanding.summary == "Fix route handling regression in Flask dispatch"
        # Only src/flask/app.py should survive; fake/nonexistent/module.py should be stripped
        file_paths = [f.path for f in guide.relevant_files]
        assert "src/flask/app.py" in file_paths
        assert "fake/nonexistent/module.py" not in file_paths
        # Validated evidence should not contain fake paths
        evidence_paths = [e.path for e in guide.evidence]
        assert "fake/hallucinated.py" not in evidence_paths

    @pytest.mark.asyncio
    async def test_no_context_returns_safe_controlled_guide(self):
        mock_context_service = MagicMock()
        mock_context_service.get_context_for_issue = AsyncMock(
            return_value=ContributionContextData(
                context_text="",
                evidence=[],
                retrieved_chunks=[],
                retrieval_mode="none",
                chunks_count=0,
            )
        )
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.generate = AsyncMock()

        service = ContributionGuideService(
            context_service=mock_context_service,
            llm_provider=mock_llm,
        )

        with patch("app.contribution.service.github_service.fetch_single_issue") as mock_fetch:
            mock_fetch.return_value = {
                "id": 100,
                "number": 42,
                "title": "Bug in query param parsing",
                "body": "When URL contains multiple params...",
                "state": "open",
                "html_url": "https://github.com/pallets/flask/issues/42",
                "labels": ["bug"],
                "user": "contributor1",
                "comments_count": 2,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            }

            request = ContributionGuideRequest(
                owner="pallets",
                repo="flask",
                issue_number=42,
            )
            response = await service.generate_guide(request)

            assert response.retrieval_mode == "none"
            assert len(response.sources) == 0
            assert "No repository context could be retrieved" in response.guide.uncertainties[0]
            # LLM must not be called when context is empty
            mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_guide_end_to_end_success(self):
        sample_chunk = _make_retrieved_chunk()
        evidence_item = ContributionGuideEvidence(
            path=sample_chunk.chunk.file_path,
            chunk_id=sample_chunk.chunk.chunk_id,
            start_line=10,
            end_line=30,
            category="source",
            score=0.92,
        )

        mock_context_service = MagicMock()
        mock_context_service.get_context_for_issue = AsyncMock(
            return_value=ContributionContextData(
                context_text=f"### Excerpt from src/flask/app.py\n```python\n{sample_chunk.chunk.content}\n```",
                evidence=[evidence_item],
                retrieved_chunks=[sample_chunk],
                retrieval_mode="vector",
                chunks_count=1,
            )
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.generate = AsyncMock(return_value=json.dumps(SAMPLE_LLM_GUIDE_OUTPUT))

        service = ContributionGuideService(
            context_service=mock_context_service,
            llm_provider=mock_llm,
        )

        with patch("app.contribution.service.github_service.fetch_single_issue") as mock_fetch:
            mock_fetch.return_value = {
                "id": 101,
                "number": 157,
                "title": "Fix route handling regression in Flask dispatch",
                "body": "Subdomain dispatching fails when route url contains trailing slashes.",
                "state": "open",
                "html_url": "https://github.com/pallets/flask/issues/157",
                "labels": ["bug", "routing"],
                "user": "reporter",
                "comments_count": 3,
                "created_at": "2026-02-01T00:00:00Z",
                "updated_at": "2026-02-02T00:00:00Z",
            }

            request = ContributionGuideRequest(
                owner="pallets",
                repo="flask",
                issue_number=157,
                profile=DeveloperSkillProfile(
                    programming_languages=["Python"],
                    frameworks=["Flask"],
                    tools=["Pytest"],
                    experience_level="intermediate",
                ),
            )
            response = await service.generate_guide(request)

            assert response.issue.number == 157
            assert response.retrieval_mode == "vector"
            assert len(response.sources) >= 1
            assert response.guide.issue_understanding.summary == "Fix route handling regression in Flask dispatch"
            assert len(response.guide.implementation_plan) == 2
            assert len(response.guide.pull_request_checklist) == 3

            # Check that LLM was called with profile skills mentioned in the prompt
            mock_llm.generate.assert_called_once()
            call_kwargs = mock_llm.generate.call_args.kwargs
            assert "Python" in call_kwargs["prompt"]
            assert call_kwargs["json_mode"] is True


class TestContributionGuideAPIEndpoint:
    """API integration tests for POST /api/v1/repositories/issues/contribution-guide."""

    def test_missing_owner_or_repo_returns_400(self):
        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={"owner": "", "repo": "flask", "issue_number": 157},
        )
        assert resp.status_code == 400
        assert "owner and repo" in resp.json()["detail"].lower()

    def test_invalid_issue_number_returns_422_or_400(self):
        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={"owner": "pallets", "repo": "flask", "issue_number": 0},
        )
        # Pydantic ge=1 triggers 422 or endpoint check triggers 400
        assert resp.status_code in (400, 422)

    @patch("app.api.v1.endpoints.repositories.contribution_guide_service.generate_guide")
    def test_valid_contribution_guide_success(self, mock_generate):
        mock_generate.return_value = ContributionGuideResponse(
            issue=IssueItem(
                id=101,
                number=157,
                title="Fix route handling regression in Flask dispatch",
                body="Subdomain dispatching fails...",
                state="open",
                html_url="https://github.com/pallets/flask/issues/157",
            ),
            guide=ContributionGuide(
                issue_understanding=ContributionGuideUnderstanding(
                    summary="Fix route handling regression in Flask dispatch",
                    problem="Subdomain dispatching fails when route url contains trailing slashes.",
                    expected_outcome="Trailing slashes should be preserved or redirected cleanly.",
                ),
                prerequisites=["Python 3.10+"],
                implementation_plan=[],
                pull_request_checklist=["Run pytest"],
            ),
            retrieval_mode="vector",
            sources=[
                ContributionGuideEvidence(
                    path="src/flask/app.py",
                    start_line=10,
                    end_line=30,
                    category="source",
                    score=0.92,
                )
            ],
            uncertainties=[],
        )

        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={
                "owner": "pallets",
                "repo": "flask",
                "issue_number": 157,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["issue"]["number"] == 157
        assert data["guide"]["issue_understanding"]["summary"] == "Fix route handling regression in Flask dispatch"
        assert data["retrieval_mode"] == "vector"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["path"] == "src/flask/app.py"

    @patch("app.api.v1.endpoints.repositories.contribution_guide_service.generate_guide")
    def test_issue_not_found_returns_404(self, mock_generate):
        mock_generate.side_effect = GitHubNotFoundError("Issue 99999 not found")

        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={
                "owner": "pallets",
                "repo": "flask",
                "issue_number": 99999,
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.contribution_guide_service.generate_guide")
    def test_rate_limit_returns_403(self, mock_generate):
        mock_generate.side_effect = GitHubRateLimitError("Rate limit exceeded")

        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={
                "owner": "pallets",
                "repo": "flask",
                "issue_number": 157,
            },
        )
        assert resp.status_code == 403
        assert "rate limit" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.contribution_guide_service.generate_guide")
    def test_llm_provider_unavailable_returns_503(self, mock_generate):
        mock_generate.side_effect = LLMProviderUnavailableError("AI provider is unavailable. Ollama is offline")

        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={
                "owner": "pallets",
                "repo": "flask",
                "issue_number": 157,
            },
        )
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.contribution_guide_service.generate_guide")
    def test_llm_timeout_returns_504(self, mock_generate):
        mock_generate.side_effect = LLMTimeoutError("Model timed out")

        resp = client.post(
            "/api/v1/repositories/issues/contribution-guide",
            json={
                "owner": "pallets",
                "repo": "flask",
                "issue_number": 157,
            },
        )
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"].lower()
