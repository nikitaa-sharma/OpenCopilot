"""
Tests for Repository Structure Explainer / Understand This Repository feature.
Validates schemas, heuristic fallbacks, Mermaid sanitization, service orchestration,
and the REST API endpoint.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.structure_explainer import (
    ArchitectureExplanation,
    DirectoryExplanationDetail,
    ImportantFileDetail,
    RepositoryFlow,
    RepositoryOverviewDetail,
    StructureExplainerAnalysis,
    StructureExplainerResponse,
    TechnologyMap,
    WhereToStartStep,
)
from app.schemas.repository import RepositoryRef, ContextStats
from app.services.structure_explainer_service import (
    clean_mermaid_diagram,
    generate_fallback_mermaid,
    structure_explainer_service,
)
from app.services.github_service import (
    GitHubNotFoundError,
    GitHubRateLimitError,
    InvalidGitHubURLError,
)
from app.services.llm_provider import LLMProviderUnavailableError

client = TestClient(app)

MOCK_EXPLAINER_ANALYSIS = StructureExplainerAnalysis(
    overview=RepositoryOverviewDetail(
        what_it_does="Flask is a lightweight WSGI web application framework in Python.",
        main_purpose="Allows developers to build robust web applications and APIs quickly.",
        primary_technologies=["Python", "Werkzeug", "Jinja"],
        application_type="Web Framework",
        entry_points=["src/flask/__init__.py", "src/flask/app.py"],
        high_level_architecture="Layered microframework routing requests through WSGI and dispatching to view functions.",
    ),
    directories=[
        DirectoryExplanationDetail(
            name="src/",
            purpose="Main application source code.",
            contains="Core routing, request handling, and application lifecycle.",
            important_subdirectories=["src/flask"],
            relationship="Contains primary code tested by tests/ and built with pyproject.toml.",
            evidence="Observed 15 source files",
            confidence="high",
        ),
        DirectoryExplanationDetail(
            name="tests/",
            purpose="Automated test suites.",
            contains="Comprehensive unit and integration tests.",
            important_subdirectories=[],
            relationship="Verifies behavior of modules in src/.",
            evidence="Observed 20 test files",
            confidence="high",
        ),
    ],
    important_files=[
        ImportantFileDetail(
            path="pyproject.toml",
            category="manifest",
            description="Project build system configuration and dependency specifications.",
            evidence="Defines dependencies and packaging metadata",
        ),
        ImportantFileDetail(
            path="src/flask/app.py",
            category="entry_point",
            description="Core Flask application class implementing the WSGI interface.",
            evidence="Defines class Flask",
        ),
    ],
    architecture=ArchitectureExplanation(
        overview="Clients send HTTP requests to the WSGI application, which routes them to view functions.",
        pattern="Microframework",
        layers=["WSGI Interface", "Routing & Dispatch", "View Functions", "Template Rendering"],
        diagram_mermaid='flowchart TD\n    Client["HTTP Client"] --> WSGI["WSGI Server"]\n    WSGI --> App["Flask App"]\n    App --> Views["View Handlers"]',
    ),
    flow=RepositoryFlow(
        execution_start="Application is instantiated from src/flask/app.py and run via WSGI server.",
        component_communication="Internal modules pass Request and Context objects synchronously.",
        data_entry="HTTP requests enter through the WSGI callable.",
        data_processing="Routes match URLs, extract parameters, and execute matched view functions.",
        data_storage="Relies on application-provided database adapters or in-memory session storage.",
        result_delivery="Returns HTTP Response object with status, headers, and body payload.",
    ),
    technology_map=TechnologyMap(
        frontend=[],
        backend=["Python", "Flask", "Werkzeug"],
        database=[],
        apis=["WSGI", "REST"],
        ai_ml=[],
        testing=["pytest"],
        devops=["GitHub Actions"],
        build_tools=["flit", "pip"],
    ),
    where_to_start=[
        WhereToStartStep(
            step_number=1,
            title="1. Read README & Vision",
            target_path="README.md",
            guidance="Start with the documentation to understand project scope.",
            why="High-level understanding.",
        ),
        WhereToStartStep(
            step_number=2,
            title="2. Dependencies in pyproject.toml",
            target_path="pyproject.toml",
            guidance="Inspect external dependencies.",
            why="Maps external dependencies.",
        ),
    ],
    confidence_evidence="High confidence grounded in pyproject.toml, src/ directory, and tests/ suite.",
)

MOCK_RESPONSE = StructureExplainerResponse(
    repository=RepositoryRef(owner="pallets", name="flask", branch="main"),
    explainer=MOCK_EXPLAINER_ANALYSIS,
    provider="ollama",
    model="llama3.2:3b",
    context_stats=ContextStats(files_included=5, total_context_chars=8500),
)


def test_mermaid_cleaner_and_fallback():
    """Verify clean_mermaid_diagram formats and cleans diagrams correctly."""
    # Empty input generates valid fallback
    fallback = clean_mermaid_diagram("")
    assert "flowchart TD" in fallback
    assert "-->" in fallback

    # Valid input is preserved
    valid_raw = 'graph TD\n  A["User"] --> B["Backend"]'
    cleaned = clean_mermaid_diagram(valid_raw)
    assert "flowchart TD" in cleaned
    assert 'A["User"] --> B["Backend"]' in cleaned

    # Component list fallback
    comp_fallback = generate_fallback_mermaid(["Frontend", "API Gateway", "Database"])
    assert "flowchart TD" in comp_fallback
    assert 'Node1["Frontend"]' in comp_fallback
    assert 'Node2["API Gateway"]' in comp_fallback
    assert "Node1 --> Node2" in comp_fallback


def test_structure_explainer_endpoint_success():
    """Verify POST /api/v1/repositories/structure-explainer returns 200 with schema."""
    with patch(
        "app.api.v1.endpoints.repositories.structure_explainer_service.explain_repository_structure",
        new=AsyncMock(return_value=MOCK_RESPONSE),
    ):
        response = client.post(
            "/api/v1/repositories/structure-explainer",
            json={"url": "https://github.com/pallets/flask"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["repository"]["owner"] == "pallets"
        assert data["repository"]["name"] == "flask"
        assert data["explainer"]["overview"]["application_type"] == "Web Framework"
        assert len(data["explainer"]["directories"]) == 2
        assert len(data["explainer"]["important_files"]) == 2
        assert "flowchart TD" in data["explainer"]["architecture"]["diagram_mermaid"]
        assert len(data["explainer"]["where_to_start"]) == 2
        assert data["provider"] == "ollama"


def test_structure_explainer_invalid_url_400():
    """Verify endpoint rejects invalid repository URLs with 400."""
    with patch(
        "app.api.v1.endpoints.repositories.structure_explainer_service.explain_repository_structure",
        side_effect=InvalidGitHubURLError("Invalid URL format"),
    ):
        response = client.post(
            "/api/v1/repositories/structure-explainer",
            json={"url": "not-a-valid-url"},
        )
        assert response.status_code == 400
        assert "Invalid URL" in response.json()["detail"]


def test_structure_explainer_not_found_404():
    """Verify endpoint returns 404 when repository is not found."""
    with patch(
        "app.api.v1.endpoints.repositories.structure_explainer_service.explain_repository_structure",
        side_effect=GitHubNotFoundError("Repository not found"),
    ):
        response = client.post(
            "/api/v1/repositories/structure-explainer",
            json={"url": "https://github.com/nonexistent/missing-repo"},
        )
        assert response.status_code == 404


def test_structure_explainer_rate_limit_403():
    """Verify endpoint returns 403 on GitHub rate limit."""
    with patch(
        "app.api.v1.endpoints.repositories.structure_explainer_service.explain_repository_structure",
        side_effect=GitHubRateLimitError("Rate limit exceeded"),
    ):
        response = client.post(
            "/api/v1/repositories/structure-explainer",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 403


def test_structure_explainer_provider_unavailable_503():
    """Verify endpoint returns 503 when LLM provider is unavailable."""
    with patch(
        "app.api.v1.endpoints.repositories.structure_explainer_service.explain_repository_structure",
        side_effect=LLMProviderUnavailableError("Ollama connection refused"),
    ):
        response = client.post(
            "/api/v1/repositories/structure-explainer",
            json={"url": "https://github.com/pallets/flask"},
        )
        assert response.status_code == 503


@pytest.mark.asyncio
async def test_service_explains_repository_structure_with_llm():
    """Verify StructureExplainerService orchestrates metadata, tree, RAG, and LLM correctly."""
    mock_llm = AsyncMock()
    mock_llm.model = "llama3.2:3b"
    mock_llm.generate.return_value = json.dumps(MOCK_EXPLAINER_ANALYSIS.model_dump())

    service = structure_explainer_service
    service._custom_llm_provider = mock_llm

    with patch.object(service, "_fetch_candidate_contents", new=AsyncMock(return_value={"pyproject.toml": "[project]\nname='flask'"})), \
         patch.object(service, "_retrieve_rag_context", new=AsyncMock(return_value=["[app.py]: Flask app initialization"])), \
         patch("app.services.structure_explainer_service.github_service.fetch_repository", new=AsyncMock(return_value={
             "id": 1,
             "owner": "pallets",
             "name": "flask",
             "full_name": "pallets/flask",
             "default_branch": "main",
             "description": "A microframework for Python.",
             "language": "Python",
             "stargazers_count": 65000,
             "open_issues_count": 42,
             "html_url": "https://github.com/pallets/flask",
         })), \
         patch("app.services.structure_explainer_service.github_service.fetch_languages", new=AsyncMock(return_value={"Python": 100000})), \
         patch("app.services.structure_explainer_service.github_service.fetch_readme", new=AsyncMock(return_value={"name": "README.md", "content": "Flask documentation"})), \
         patch("app.services.structure_explainer_service.repository_ingestion_service.get_repository_tree", new=AsyncMock(return_value={
             "tree": [
                 {"path": "src/flask/app.py", "type": "file", "size": 4500},
                 {"path": "tests/test_app.py", "type": "file", "size": 1200},
                 {"path": "pyproject.toml", "type": "file", "size": 500},
             ]
         })):
        result = await service.explain_repository_structure("https://github.com/pallets/flask")

        assert result.repository.owner == "pallets"
        assert result.repository.name == "flask"
        assert result.explainer.overview.application_type == "Web Framework"
        assert len(result.explainer.directories) == 2
        assert "flowchart TD" in result.explainer.architecture.diagram_mermaid


@pytest.mark.asyncio
async def test_service_fallback_on_llm_malformed_output():
    """Verify fallback explainer is generated when LLM output is malformed or offline."""
    mock_llm = AsyncMock()
    mock_llm.model = "llama3.2:3b"
    mock_llm.generate.return_value = "Non-JSON garbage output"

    service = structure_explainer_service
    service._custom_llm_provider = mock_llm

    with patch.object(service, "_fetch_candidate_contents", new=AsyncMock(return_value={})), \
         patch.object(service, "_retrieve_rag_context", new=AsyncMock(return_value=[])), \
         patch("app.services.structure_explainer_service.github_service.fetch_repository", new=AsyncMock(return_value={
             "id": 1,
             "owner": "pallets",
             "name": "flask",
             "full_name": "pallets/flask",
             "default_branch": "main",
             "description": "A microframework for Python.",
             "language": "Python",
             "stargazers_count": 65000,
             "open_issues_count": 42,
             "html_url": "https://github.com/pallets/flask",
         })), \
         patch("app.services.structure_explainer_service.github_service.fetch_languages", new=AsyncMock(return_value={"Python": 100000})), \
         patch("app.services.structure_explainer_service.github_service.fetch_readme", new=AsyncMock(return_value={"name": "README.md", "content": "Flask documentation"})), \
         patch("app.services.structure_explainer_service.repository_ingestion_service.get_repository_tree", new=AsyncMock(return_value={
             "tree": [
                 {"path": "src/flask/app.py", "type": "file", "size": 4500},
                 {"path": "tests/test_app.py", "type": "file", "size": 1200},
                 {"path": "pyproject.toml", "type": "file", "size": 500},
             ]
         })):
        result = await service.explain_repository_structure("https://github.com/pallets/flask")

        assert result.repository.owner == "pallets"
        assert result.explainer.overview.application_type != ""
        assert len(result.explainer.directories) >= 1
        assert "flowchart TD" in result.explainer.architecture.diagram_mermaid
        assert len(result.explainer.where_to_start) >= 4
