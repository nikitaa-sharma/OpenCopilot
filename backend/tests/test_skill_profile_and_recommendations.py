"""
Comprehensive test suite for Phase 10: Developer Skill Profile & Personalized Issue Recommendations.
Covers profile creation, retrieval, skill normalization, deterministic matching,
match reasons, skill gaps, learning opportunities, endpoint behavior, and sorting.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.profile import (
    DeveloperSkillProfile,
    IssueRecommendationRequest,
    IssueRecommendationResponse,
    SkillMatchResult,
)
from app.schemas.repository import (
    CandidateFile,
    IssueAIAnalysis,
    IssueAIAnalysisResponse,
    IssueItem,
    RepositoryRef,
)
from app.services.profile_service import profile_service
from app.services.skill_matching_service import skill_matching_service
from app.services.skill_normalizer import (
    normalize_profile,
    normalize_skill,
    normalize_skill_list,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset in-memory profile and analysis cache before each test."""
    profile_service.reset_profile()
    skill_matching_service.clear_cache()
    yield
    profile_service.reset_profile()
    skill_matching_service.clear_cache()


# ==============================================================================
# 1. Skill Normalization Unit Tests
# ==============================================================================

def test_skill_normalization_canonical_aliases():
    """Verify common tech aliases normalize to canonical display names."""
    assert normalize_skill("python") == "Python"
    assert normalize_skill("PYTHON") == "Python"
    assert normalize_skill("js") == "JavaScript"
    assert normalize_skill("javascript") == "JavaScript"
    assert normalize_skill("ts") == "TypeScript"
    assert normalize_skill("typescript") == "TypeScript"
    assert normalize_skill("postgres") == "PostgreSQL"
    assert normalize_skill("postgresql") == "PostgreSQL"
    assert normalize_skill("docker") == "Docker"
    assert normalize_skill("k8s") == "Kubernetes"
    assert normalize_skill("kubernetes") == "Kubernetes"
    assert normalize_skill("fastapi") == "FastAPI"
    assert normalize_skill("react") == "React"
    assert normalize_skill("reactjs") == "React"
    assert normalize_skill("nextjs") == "Next.js"
    assert normalize_skill("next.js") == "Next.js"
    assert normalize_skill("vue.js") == "Vue.js"
    assert normalize_skill("golang") == "Go"
    assert normalize_skill("rust") == "Rust"
    assert normalize_skill("cpp") == "C++"
    assert normalize_skill("csharp") == "C#"


def test_skill_normalization_preserves_unknown_skills():
    """Verify unknown or niche skills are preserved cleanly rather than dropped."""
    assert normalize_skill("Zig") == "Zig"
    assert normalize_skill("zig") == "Zig"
    assert normalize_skill("polars") == "Polars"
    assert normalize_skill("WebAssembly") == "WebAssembly"
    assert normalize_skill("some-custom-tool") == "Some-custom-tool"
    assert normalize_skill("   ") == ""


def test_skill_list_normalization_deduplication():
    """Verify skill list normalization strips duplicates case-insensitively while preserving order."""
    raw = ["python", "Python", "PYTHON", "FastAPI", "fastapi", "docker", "Git", "git"]
    normalized = normalize_skill_list(raw)
    assert normalized == ["Python", "FastAPI", "Docker", "Git"]


def test_profile_normalization():
    """Verify DeveloperSkillProfile fields are cleanly normalized and deduplicated."""
    raw_profile = DeveloperSkillProfile(
        programming_languages=["python", "JS", "typescript", "python"],
        frameworks=["fastapi", "REACT", "django"],
        tools=["git", "docker", "k8s"],
        domains=["web dev", "ai"],
        experience_level="BEGINNER",
        interests=["open source", "BACKEND"],
    )
    norm = normalize_profile(raw_profile)

    assert norm.programming_languages == ["Python", "JavaScript", "TypeScript"]
    assert norm.frameworks == ["FastAPI", "React", "Django"]
    assert norm.tools == ["Git", "Docker", "Kubernetes"]
    assert norm.domains == ["Web Development", "AI"]
    assert norm.experience_level == "beginner"
    assert norm.interests == ["Open Source", "Backend Development"]


# ==============================================================================
# 2. Profile Service & Endpoints Tests
# ==============================================================================

def test_profile_service_get_and_set():
    """Verify ProfileService stores and returns normalized profile in-memory."""
    profile = DeveloperSkillProfile(
        programming_languages=["python"],
        frameworks=["fastapi"],
        tools=["git"],
        experience_level="intermediate",
    )
    saved = profile_service.set_profile(profile)
    assert saved.programming_languages == ["Python"]
    assert saved.frameworks == ["FastAPI"]

    current = profile_service.get_profile()
    assert current.programming_languages == ["Python"]
    assert current.experience_level == "intermediate"


def test_get_profile_endpoint():
    """Verify GET /api/v1/profile/skills returns current profile."""
    response = client.get("/api/v1/profile/skills")
    assert response.status_code == 200
    data = response.json()
    assert "programming_languages" in data
    assert "experience_level" in data


def test_post_profile_endpoint():
    """Verify POST /api/v1/profile/skills updates and normalizes active profile."""
    payload = {
        "programming_languages": ["python", "js"],
        "frameworks": ["fastapi", "react"],
        "tools": ["git", "docker"],
        "domains": ["ai"],
        "experience_level": "beginner",
        "interests": ["open source"],
    }
    response = client.post("/api/v1/profile/skills", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["programming_languages"] == ["Python", "JavaScript"]
    assert data["frameworks"] == ["FastAPI", "React"]
    assert data["tools"] == ["Git", "Docker"]
    assert data["domains"] == ["AI"]
    assert data["interests"] == ["Open Source"]

    # Verify subsequent GET returns the saved profile
    get_resp = client.get("/api/v1/profile/skills")
    assert get_resp.status_code == 200
    assert get_resp.json()["programming_languages"] == ["Python", "JavaScript"]


# ==============================================================================
# 3. Deterministic Skill Matching Logic Tests
# ==============================================================================

def test_matching_with_full_overlap():
    """Verify full skill match produces score 1.0 (100%), no missing skills, and clear match reasons."""
    profile = DeveloperSkillProfile(
        programming_languages=["Python"],
        frameworks=["FastAPI"],
        tools=["Git"],
    )
    issue = IssueItem(
        number=101,
        title="Add validation endpoint",
        body="Requires Python and FastAPI",
        html_url="https://github.com/fastapi/fastapi/issues/101",
        labels=["enhancement"],
    )
    analysis = IssueAIAnalysis(
        issue_type="feature",
        difficulty="beginner",
        difficulty_rationale="Small focused endpoint.",
        required_skills=["Python", "FastAPI"],
        skills_rationale="Web service routing and validation.",
        prerequisites="Python 3.10+",
        ai_explanation="Adding a new validation endpoint.",
        confidence="high",
    )

    rec = skill_matching_service.match_issue(issue, profile, analysis)
    assert rec.skill_match.score == 1.0
    assert set(rec.skill_match.matched_skills) == {"Python", "FastAPI"}
    assert rec.skill_match.missing_skills == []
    assert len(rec.skill_match.match_reasons) >= 2
    assert rec.difficulty == "beginner"
    assert rec.match_label == "Highest skill-match score"


def test_matching_with_partial_overlap():
    """Verify partial match identifies matched skills, skill gaps, and learning opportunities."""
    profile = DeveloperSkillProfile(
        programming_languages=["Python"],
        frameworks=["FastAPI"],
        tools=["Git"],
    )
    issue = IssueItem(
        number=102,
        title="Implement Redis caching layer",
        body="Requires Python and Redis",
        html_url="https://github.com/fastapi/fastapi/issues/102",
        labels=["enhancement"],
    )
    analysis = IssueAIAnalysis(
        issue_type="feature",
        difficulty="intermediate",
        difficulty_rationale="Caching integration across routes.",
        required_skills=["Python", "Redis"],
        skills_rationale="Python backend logic and Redis caching.",
        prerequisites="Redis server",
        ai_explanation="Adding Redis cache middleware.",
        confidence="high",
    )

    rec = skill_matching_service.match_issue(issue, profile, analysis)
    assert rec.skill_match.score == 0.5
    assert "Python" in rec.skill_match.matched_skills
    assert "Redis" in rec.skill_match.missing_skills
    assert any("Redis" in opp for opp in rec.skill_match.learning_opportunities)
    assert rec.difficulty == "intermediate"


def test_matching_with_zero_overlap():
    """Verify zero overlap returns 0.0 match score and marks missing skills as learning opportunities."""
    profile = DeveloperSkillProfile(
        programming_languages=["Rust"],
        frameworks=[],
        tools=[],
    )
    issue = IssueItem(
        number=103,
        title="Fix JavaScript CSS animation glitch",
        body="UI fix in frontend",
        html_url="https://github.com/test/repo/issues/103",
        labels=["frontend"],
    )
    analysis = IssueAIAnalysis(
        issue_type="bug",
        difficulty="beginner",
        difficulty_rationale="Simple CSS animation fix.",
        required_skills=["JavaScript", "CSS"],
        skills_rationale="Frontend scripting and styling.",
        prerequisites="Node.js",
        ai_explanation="Animation flicker on hover.",
        confidence="medium",
    )

    rec = skill_matching_service.match_issue(issue, profile, analysis)
    assert rec.skill_match.score == 0.0
    assert rec.skill_match.matched_skills == []
    assert set(rec.skill_match.missing_skills) == {"JavaScript", "CSS"}
    assert rec.match_label == "Learning opportunity"
    assert rec.difficulty == "beginner"  # Difficulty remains separate!


def test_difficulty_remains_separate_from_skill_match():
    """Verify that difficulty (AI estimate) is independent of user's skill match score."""
    profile = DeveloperSkillProfile(
        programming_languages=["Python", "C++"],
        frameworks=["PyTorch"],
    )
    issue = IssueItem(
        number=104,
        title="Optimize tensor serialization in C++ kernel",
        body="Heavy computational kernel optimization",
        html_url="https://github.com/test/repo/issues/104",
        labels=["performance"],
    )
    analysis = IssueAIAnalysis(
        issue_type="refactor",
        difficulty="advanced",
        difficulty_rationale="Requires low-level memory layout and SIMD vectorization knowledge.",
        required_skills=["C++", "Python"],
        skills_rationale="Kernel binding and C++ routines.",
        prerequisites="C++ compiler, CUDA toolkit",
        ai_explanation="Optimizing tensor serialization bottlenecks.",
        confidence="high",
    )

    rec = skill_matching_service.match_issue(issue, profile, analysis)
    # The developer has 100% skill overlap, but the issue remains intrinsically 'advanced'!
    assert rec.skill_match.score == 1.0
    assert rec.difficulty == "advanced"
    assert rec.difficulty_rationale == "Requires low-level memory layout and SIMD vectorization knowledge."


def test_candidate_files_bonus_reasoning():
    """Verify candidate files matching developer skills add concrete match reasons."""
    profile = DeveloperSkillProfile(programming_languages=["Python"])
    issue = IssueItem(
        number=105,
        title="Fix routing parameter bug",
        body="Bug report",
        html_url="https://github.com/test/repo/issues/105",
        labels=["bug"],
    )
    analysis = IssueAIAnalysis(
        issue_type="bug",
        difficulty="intermediate",
        difficulty_rationale="Routing logic bug.",
        required_skills=["Python", "FastAPI"],
        skills_rationale="Routing code.",
        candidate_files=[
            CandidateFile(
                path="src/app/routing.py",
                reason="Handles route registration",
                confidence="likely",
            )
        ],
        prerequisites="Python 3.10+",
        ai_explanation="Routing error.",
        confidence="high",
    )

    rec = skill_matching_service.match_issue(issue, profile, analysis)
    assert any("routing.py" in r and "Python" in r for r in rec.skill_match.match_reasons)


# ==============================================================================
# 4. Recommendation Service & Sorting Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_deterministic_recommendation_ordering():
    """Verify recommendations are sorted by match score descending, then issue number ascending."""
    profile = DeveloperSkillProfile(
        programming_languages=["Python"],
        frameworks=["FastAPI"],
    )

    # Mock issues from GitHub
    mock_issues = [
        {"number": 200, "title": "TypeScript frontend bug", "labels": [], "html_url": "https://github.com/test/repo/issues/200", "state": "open"},
        {"number": 100, "title": "Python FastAPI core bug", "labels": [], "html_url": "https://github.com/test/repo/issues/100", "state": "open"},
        {"number": 150, "title": "Python only documentation", "labels": [], "html_url": "https://github.com/test/repo/issues/150", "state": "open"},
        {"number": 50, "title": "Another Python FastAPI feature", "labels": [], "html_url": "https://github.com/test/repo/issues/50", "state": "open"},
    ]

    # Pre-cache AI analyses
    skill_matching_service.cache_analysis(
        "test", "repo", 200,
        IssueAIAnalysisResponse(
            repository=RepositoryRef(owner="test", name="repo", branch="main"),
            issue_number=200, issue_title="", issue_url="",
            analysis=IssueAIAnalysis(
                issue_type="bug", difficulty="intermediate", difficulty_rationale="",
                required_skills=["TypeScript", "React"], skills_rationale="", prerequisites="", ai_explanation="", confidence="high"
            )
        )
    )
    skill_matching_service.cache_analysis(
        "test", "repo", 100,
        IssueAIAnalysisResponse(
            repository=RepositoryRef(owner="test", name="repo", branch="main"),
            issue_number=100, issue_title="", issue_url="",
            analysis=IssueAIAnalysis(
                issue_type="bug", difficulty="beginner", difficulty_rationale="",
                required_skills=["Python", "FastAPI"], skills_rationale="", prerequisites="", ai_explanation="", confidence="high"
            )
        )
    )
    skill_matching_service.cache_analysis(
        "test", "repo", 50,
        IssueAIAnalysisResponse(
            repository=RepositoryRef(owner="test", name="repo", branch="main"),
            issue_number=50, issue_title="", issue_url="",
            analysis=IssueAIAnalysis(
                issue_type="feature", difficulty="intermediate", difficulty_rationale="",
                required_skills=["Python", "FastAPI"], skills_rationale="", prerequisites="", ai_explanation="", confidence="high"
            )
        )
    )
    skill_matching_service.cache_analysis(
        "test", "repo", 150,
        IssueAIAnalysisResponse(
            repository=RepositoryRef(owner="test", name="repo", branch="main"),
            issue_number=150, issue_title="", issue_url="",
            analysis=IssueAIAnalysis(
                issue_type="documentation", difficulty="beginner", difficulty_rationale="",
                required_skills=["Python", "Documentation"], skills_rationale="", prerequisites="", ai_explanation="", confidence="high"
            )
        )
    )

    with patch("app.services.github_service.github_service.fetch_issues", new=AsyncMock(return_value=mock_issues)), \
         patch("app.services.github_service.github_service.fetch_languages", new=AsyncMock(return_value={"Python": 1000})):

        res = await skill_matching_service.get_recommendations_for_repository("test", "repo", profile)

        # Ties between 100% score (issue #50 and #100) must be broken by issue.number ascending:
        # Issue 50 (score 1.0) -> Issue 100 (score 1.0) -> Issue 150 (score 0.5) -> Issue 200 (score 0.0)
        assert len(res.recommendations) == 4
        assert res.recommendations[0].issue.number == 50
        assert res.recommendations[0].skill_match.score == 1.0
        assert res.recommendations[1].issue.number == 100
        assert res.recommendations[1].skill_match.score == 1.0
        assert res.recommendations[2].issue.number == 150
        assert res.recommendations[2].skill_match.score == 0.5
        assert res.recommendations[3].issue.number == 200
        assert res.recommendations[3].skill_match.score == 0.0


@pytest.mark.asyncio
async def test_empty_repository_issues_handled_cleanly():
    """Verify empty issue list returns 200 with empty recommendations list."""
    with patch("app.services.github_service.github_service.fetch_issues", new=AsyncMock(return_value=[])), \
         patch("app.services.github_service.github_service.fetch_languages", new=AsyncMock(return_value={})):

        res = await skill_matching_service.get_recommendations_for_repository("test", "empty-repo")
        assert res.recommendations == []
        assert res.total_issues_considered == 0


# ==============================================================================
# 5. Recommendation API Endpoint Tests
# ==============================================================================

def test_recommend_endpoint_success():
    """Verify POST /api/v1/repositories/issues/recommend returns structured response."""
    mock_issues = [
        {
            "number": 42,
            "title": "Add helper method for CORS",
            "body": "Small helper function in Python",
            "state": "open",
            "html_url": "https://github.com/pallets/flask/issues/42",
            "labels": ["good first issue"],
        }
    ]

    with patch("app.services.github_service.github_service.fetch_issues", new=AsyncMock(return_value=mock_issues)), \
         patch("app.services.github_service.github_service.fetch_languages", new=AsyncMock(return_value={"Python": 50000})):

        response = client.post(
            "/api/v1/repositories/issues/recommend",
            json={
                "owner": "pallets",
                "repo": "flask",
                "profile": {
                    "programming_languages": ["Python"],
                    "frameworks": ["Flask"],
                    "tools": ["Git"],
                    "experience_level": "beginner",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "pallets/flask"
        assert data["total_issues_considered"] == 1
        assert len(data["recommendations"]) == 1
        rec = data["recommendations"][0]
        assert rec["issue"]["number"] == 42
        assert rec["skill_match"]["score"] > 0
        assert "Python" in rec["skill_match"]["matched_skills"]
        assert len(rec["skill_match"]["match_reasons"]) > 0


def test_recommend_endpoint_reuses_cached_ai_analysis():
    """Verify recommendation endpoint reuses existing AI issue analysis when present."""
    cached_analysis = IssueAIAnalysisResponse(
        repository=RepositoryRef(owner="pallets", name="flask", branch="main"),
        issue_number=88,
        issue_title="Bug in route dispatcher",
        issue_url="https://github.com/pallets/flask/issues/88",
        analysis=IssueAIAnalysis(
            issue_type="bug",
            difficulty="intermediate",
            difficulty_rationale="Deep dispatch logic inspection.",
            required_skills=["Python", "Werkzeug"],
            skills_rationale="Requires Werkzeug routing knowledge.",
            candidate_files=[CandidateFile(path="src/flask/app.py", reason="Dispatcher", confidence="likely")],
            prerequisites="Python 3.10+",
            ai_explanation="Dispatcher bug.",
            confidence="high",
        ),
    )
    skill_matching_service.cache_analysis("pallets", "flask", 88, cached_analysis)

    mock_issues = [
        {
            "number": 88,
            "title": "Bug in route dispatcher",
            "body": "Bug report",
            "state": "open",
            "html_url": "https://github.com/pallets/flask/issues/88",
            "labels": ["bug"],
        }
    ]

    with patch("app.services.github_service.github_service.fetch_issues", new=AsyncMock(return_value=mock_issues)), \
         patch("app.services.github_service.github_service.fetch_languages", new=AsyncMock(return_value={"Python": 10000})):

        response = client.post(
            "/api/v1/repositories/issues/recommend",
            json={
                "owner": "pallets",
                "repo": "flask",
                "profile": {"programming_languages": ["Python"]},
            },
        )

        assert response.status_code == 200
        data = response.json()
        rec = data["recommendations"][0]
        # Verified that the cached analysis was reused:
        assert rec["analysis"] is not None
        assert rec["difficulty"] == "intermediate"
        assert "Werkzeug" in rec["skill_match"]["missing_skills"]
        assert "Python" in rec["skill_match"]["matched_skills"]


def test_recommend_endpoint_missing_owner_or_repo():
    """Verify validation error when owner or repo is missing or empty."""
    response = client.post(
        "/api/v1/repositories/issues/recommend",
        json={"owner": "", "repo": "flask"},
    )
    assert response.status_code == 400

    response2 = client.post(
        "/api/v1/repositories/issues/recommend",
        json={"owner": "pallets", "repo": ""},
    )
    assert response2.status_code == 400


# ==============================================================================
# 5. Targeted Tests: Repo Language, Issue Requirements, Overlap & Skill Gaps
# ==============================================================================

def test_issue_labels_not_becoming_skill_gaps():
    """
    Verify that non-technical issue labels such as 'enhancement', 'bug', 'help wanted',
    'good first issue', etc., are NOT classified as developer skill gaps.
    """
    issue = IssueItem(
        number=42,
        title="Add feature for streaming responses",
        body="Feature request for streaming support.",
        state="open",
        html_url="https://github.com/example/repo/issues/42",
        labels=["enhancement", "enhancement 🚀", "help wanted", "good first issue", "triage", "bug"],
    )
    profile = DeveloperSkillProfile(programming_languages=["Python"])
    repo_languages = {"Python": 20000}

    rec = skill_matching_service.match_issue(
        issue=issue,
        profile=profile,
        analysis=None,
        repo_languages=repo_languages,
    )

    # None of the workflow labels should appear in missing_skills (Skill Gaps)
    missing = [s.lower() for s in rec.skill_match.missing_skills]
    for non_tech in ["enhancement", "enhancement 🚀", "help wanted", "good first issue", "triage", "bug"]:
        assert non_tech.lower() not in missing, f"Label '{non_tech}' incorrectly classified as skill gap!"

    # Issue metadata labels must still be preserved on the issue item itself
    assert "enhancement" in issue.labels
    assert "enhancement 🚀" in issue.labels


def test_repository_language_match_with_zero_requirement_overlap():
    """
    Verify scenario where developer knows repository language (JavaScript),
    but the issue specifically requires TypeScript and HTML.
    Score must be 0% (0.0) for requirement overlap, while preserving:
    a) repository-language match (JavaScript in matched_repo_skills)
    b) issue-requirement match (0% score)
    c) learning opportunity clearly reported
    """
    issue = IssueItem(
        number=101,
        title="Migrate component to TypeScript",
        body="Convert the component to TypeScript and rewrite markup with HTML5 semantic tags.",
        state="open",
        html_url="https://github.com/example/repo/issues/101",
        labels=["enhancement"],
    )
    analysis = IssueAIAnalysis(
        issue_type="enhancement",
        difficulty="intermediate",
        difficulty_rationale="Component typing migration.",
        required_skills=["TypeScript", "HTML"],
        skills_rationale="Requires TypeScript type definitions and HTML markup.",
        candidate_files=[],
        prerequisites="TypeScript 5+",
        ai_explanation="Migration task.",
        confidence="high",
    )
    # Developer knows JavaScript, repo is primarily JavaScript
    profile = DeveloperSkillProfile(programming_languages=["JavaScript"])
    repo_languages = {"JavaScript": 50000}

    rec = skill_matching_service.match_issue(
        issue=issue,
        profile=profile,
        analysis=analysis,
        repo_languages=repo_languages,
    )

    # 1. Score is 0.0 (0% of issue requirements overlap)
    assert rec.skill_match.score == 0.0

    # 2. Issue requirement match is empty
    assert rec.skill_match.matched_required_skills == []

    # 3. Repository language match is captured
    assert "JavaScript" in rec.skill_match.matched_repo_skills
    assert "JavaScript" in rec.skill_match.matched_skills

    # 4. Missing skills only contains true requirements
    assert "TypeScript" in rec.skill_match.missing_skills
    assert "HTML" in rec.skill_match.missing_skills
    assert "Enhancement" not in rec.skill_match.missing_skills

    # 5. Match reasons clearly explain the distinction
    assert any("Repository primary language (JavaScript)" in r for r in rec.skill_match.match_reasons)
    assert any("learning opportunity" in r.lower() for r in rec.skill_match.match_reasons)


def test_partial_requirement_overlap():
    """
    Verify partial requirement match: issue requires Python, Docker, and Redis.
    Developer has Python and Git. Score should be 1/3 (approx 0.33).
    """
    issue = IssueItem(
        number=55,
        title="Add Redis caching and containerize",
        body="Set up Redis cache backend with Docker compose.",
        state="open",
        html_url="https://github.com/example/repo/issues/55",
        labels=["feature"],
    )
    analysis = IssueAIAnalysis(
        issue_type="feature",
        difficulty="intermediate",
        difficulty_rationale="Multi-service setup.",
        required_skills=["Python", "Docker", "Redis"],
        skills_rationale="Requires Python, Docker containerization, and Redis caching.",
        candidate_files=[],
        prerequisites="Docker installed",
        ai_explanation="Caching feature.",
        confidence="high",
    )
    profile = DeveloperSkillProfile(
        programming_languages=["Python"],
        tools=["Git"],
    )
    repo_languages = {"Python": 10000}

    rec = skill_matching_service.match_issue(
        issue=issue,
        profile=profile,
        analysis=analysis,
        repo_languages=repo_languages,
    )

    # 1 out of 3 required skills matched = 0.33
    assert rec.skill_match.score == 0.33
    assert rec.skill_match.matched_required_skills == ["Python"]
    assert "Docker" in rec.skill_match.missing_skills
    assert "Redis" in rec.skill_match.missing_skills
    assert "feature" not in [s.lower() for s in rec.skill_match.missing_skills]


def test_full_requirement_match():
    """
    Verify complete requirement match: issue requires Python and Pytest.
    Developer has both. Score should be 1.0 (100%).
    """
    issue = IssueItem(
        number=77,
        title="Add unit tests",
        body="Write pytest test cases.",
        state="open",
        html_url="https://github.com/example/repo/issues/77",
        labels=["testing"],
    )
    analysis = IssueAIAnalysis(
        issue_type="testing",
        difficulty="beginner",
        difficulty_rationale="Standard test suite expansion.",
        required_skills=["Python", "Pytest"],
        skills_rationale="Requires pytest test framework.",
        candidate_files=[],
        prerequisites="pytest",
        ai_explanation="Test writing.",
        confidence="high",
    )
    profile = DeveloperSkillProfile(
        programming_languages=["Python"],
        tools=["Pytest"],
    )
    repo_languages = {"Python": 10000}

    rec = skill_matching_service.match_issue(
        issue=issue,
        profile=profile,
        analysis=analysis,
        repo_languages=repo_languages,
    )

    assert rec.skill_match.score == 1.0
    assert "Python" in rec.skill_match.matched_required_skills
    assert "Pytest" in rec.skill_match.matched_required_skills
    assert rec.skill_match.missing_skills == []

