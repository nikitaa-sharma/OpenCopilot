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
    assert 'a["User"] --> b["Backend"]' in cleaned

    # Component list fallback
    comp_fallback = generate_fallback_mermaid(["Frontend", "API Gateway", "Database"])
    assert "flowchart TD" in comp_fallback
    assert 'node_1["Frontend"]' in comp_fallback
    assert 'node_2["API Gateway"]' in comp_fallback
    assert "node_1 --> node_2" in comp_fallback


def test_mermaid_problem_case_spaces_in_node_identifiers():
    """Verify fixing the exact problem case: GitHub Actions["GitHub Actions"] --> Git["Git"]."""
    problem_diagram = """flowchart TD
    GitHub Actions["GitHub Actions"] --> Git["Git"]
    Git --> Pacman["Pacman"]"""

    cleaned = clean_mermaid_diagram(problem_diagram)
    assert "flowchart TD" in cleaned
    assert 'github_actions["GitHub Actions"] --> git["Git"]' in cleaned
    assert 'git["Git"] --> pacman["Pacman"]' in cleaned
    # Ensure no invalid node identifiers with spaces exist before brackets
    assert 'GitHub Actions[' not in cleaned


def test_mermaid_special_characters_in_labels():
    """Verify labels with colons, quotes, parentheses, brackets, and edge descriptions."""
    raw = """flowchart TD
    Client["Client (Browser v1.0) & UI: Web"] -->|HTTP / JSON (REST)| Server["API Server: FastAPI [v0.110]"]
    Server -->|"DB Query: SELECT * FROM 'users'"| DB[("PostgreSQL DB: 5432")]"""

    cleaned = clean_mermaid_diagram(raw)
    assert "flowchart TD" in cleaned
    assert 'client["Client (Browser v1.0) & UI: Web"]' in cleaned
    assert 'server["API Server: FastAPI [v0.110]"]' in cleaned
    assert 'db[("PostgreSQL DB: 5432")]' in cleaned
    assert '-->|"HTTP / JSON (REST)"|' in cleaned
    assert "-->" in cleaned


def test_mermaid_subgraphs_and_multihop_chains():
    """Verify subgraphs and multi-hop node connection chains."""
    raw = """flowchart TD
    subgraph CI/CD Pipeline ["CI/CD Automation"]
        gh_actions["GitHub Actions"] --> test_runner["Test Runner"]
    end
    A --> B --> C"""

    cleaned = clean_mermaid_diagram(raw)
    assert "flowchart TD" in cleaned
    assert 'subgraph ci_cd_pipeline ["CI/CD Automation"]' in cleaned
    assert 'gh_actions["GitHub Actions"] --> test_runner["Test Runner"]' in cleaned
    assert "end" in cleaned
    assert 'a["A"] --> b["B"] --> c["C"]' in cleaned


def test_mermaid_markdown_code_fences_stripping():
    """Verify markdown fences (```mermaid ... ```) are stripped and cleaned properly."""
    raw = "```mermaid\nflowchart TD\n    Frontend[\"Frontend App\"] --> Backend[\"Backend API\"]\n```"
    cleaned = clean_mermaid_diagram(raw)
    assert "```" not in cleaned
    assert "flowchart TD" in cleaned
    assert 'frontend["Frontend App"] --> backend["Backend API"]' in cleaned


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


def test_clean_prose_from_markdown_strips_badges_and_extracts_sentences():
    """Verify clean_prose_from_markdown strips badge links and extracts real sentences."""
    from app.services.structure_explainer_service import clean_prose_from_markdown

    badge_heavy_readme = """# Effect

[![npm version](https://badge.fury.io/js/effect.svg)](https://badge.fury.io/js/effect)
[![Discord](https://img.shields.io/discord/780826978583478302)](https://discord.gg/effect-ts)

Effect is a powerful functional programming library for TypeScript designed to build robust and type-safe systems.

## Getting Started
Install via npm.
"""
    cleaned = clean_prose_from_markdown(badge_heavy_readme)
    assert "[![npm version]" not in cleaned
    assert "Effect is a powerful functional programming library" in cleaned


@pytest.mark.asyncio
async def test_structure_explainer_heuristic_no_badges_in_what_it_does():
    """Verify that heuristic fallback does not put badge links into what_it_does."""
    from app.schemas.repository import RepositoryInfo, ReadmeInfo, TreeItem
    from app.services.structure_explainer_service import structure_explainer_service

    repo = RepositoryInfo(
        owner="Effect-TS",
        name="effect",
        full_name="Effect-TS/effect",
        default_branch="main",
        description="An ecosystem of tools to build robust applications in TypeScript.",
    )
    readme = ReadmeInfo(
        name="README.md",
        content="""# Effect\n\n[![npm version](https://badge.fury.io/js/effect.svg)](https://badge.fury.io/js/effect)\n\nEffect provides standard library primitives for functional TypeScript applications.""",
    )

    analysis = structure_explainer_service._build_heuristic_explainer(
        repository=repo,
        languages={"TypeScript": 50000},
        readme=readme,
        tree_items=[TreeItem(path="package.json", type="file", category="configuration")],
        top_level_dirs={"src/": ["src/index.ts"]},
        key_files=[TreeItem(path="package.json", type="file", category="configuration")],
    )

    assert "[![" not in analysis.overview.what_it_does
    assert "Effect provides standard library primitives" in analysis.overview.what_it_does or "An ecosystem of tools" in analysis.overview.what_it_does

