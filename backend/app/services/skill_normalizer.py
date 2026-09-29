"""
Deterministic skill normalization service for Phase 10.
Normalizes technical skills, tools, languages, and frameworks conservatively without requiring an LLM.
"""

import re
from typing import Dict, List, Optional
from app.schemas.profile import DeveloperSkillProfile

# Canonical alias mapping (all keys lowercase, stripped)
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # Programming Languages
    "python": "Python",
    "py": "Python",
    "python3": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "rs": "Rust",
    "c++": "C++",
    "cpp": "C++",
    "c": "C",
    "c#": "C#",
    "csharp": "C#",
    "c sharp": "C#",
    "java": "Java",
    "ruby": "Ruby",
    "rb": "Ruby",
    "php": "PHP",
    "html": "HTML",
    "html5": "HTML",
    "css": "CSS",
    "css3": "CSS",
    "sql": "SQL",
    "bash": "Bash",
    "shell": "Bash",
    "sh": "Bash",
    "zsh": "Bash",
    "powershell": "PowerShell",
    "ps1": "PowerShell",
    "kotlin": "Kotlin",
    "kt": "Kotlin",
    "swift": "Swift",
    "scala": "Scala",
    "dart": "Dart",
    "r": "R",
    "lua": "Lua",
    "elixir": "Elixir",

    # Frameworks & Libraries
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "pydantic": "Pydantic",
    "sqlalchemy": "SQLAlchemy",
    "alembic": "Alembic",
    "celery": "Celery",
    "asyncio": "Asyncio",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "svelte": "Svelte",
    "sveltekit": "SvelteKit",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express",
    "expressjs": "Express",
    "express.js": "Express",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scipy": "SciPy",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "keras": "Keras",
    "ollama": "Ollama",
    "pgvector": "pgvector",

    # Testing Frameworks
    "pytest": "Pytest",
    "unittest": "Unittest",
    "jest": "Jest",
    "mocha": "Mocha",
    "playwright": "Playwright",
    "cypress": "Cypress",
    "vitest": "Vitest",

    # Databases & Storage
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "sqlite3": "SQLite",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",

    # Tools, Infrastructure & Cloud
    "git": "Git",
    "github": "GitHub",
    "github actions": "GitHub Actions",
    "gh actions": "GitHub Actions",
    "docker": "Docker",
    "docker-compose": "Docker Compose",
    "docker compose": "Docker Compose",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "helm": "Helm",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "linux": "Linux",
    "graphql": "GraphQL",
    "rest": "REST API",
    "restful": "REST API",
    "rest api": "REST API",
    "aws": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",

    # Domains & Concepts
    "ai": "AI",
    "artificial intelligence": "AI",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "rag": "RAG",
    "web development": "Web Development",
    "web dev": "Web Development",
    "backend": "Backend Development",
    "backend development": "Backend Development",
    "frontend": "Frontend Development",
    "frontend development": "Frontend Development",
    "full stack": "Full Stack",
    "fullstack": "Full Stack",
    "devops": "DevOps",
    "open source": "Open Source",
    "opensource": "Open Source",
    "documentation": "Documentation",
    "docs": "Documentation",
    "security": "Security",
    "testing": "Testing",
}

# Common GitHub issue labels and workflow tags that are NOT developer technical skills
NON_TECHNICAL_LABELS = {
    "enhancement",
    "feature",
    "feature request",
    "feat",
    "bug",
    "bugfix",
    "fix",
    "defect",
    "issue",
    "wontfix",
    "invalid",
    "duplicate",
    "question",
    "discussion",
    "help wanted",
    "good first issue",
    "good-first-issue",
    "beginner friendly",
    "first timers only",
    "needs review",
    "needs triage",
    "needs info",
    "needs reproduction",
    "triage",
    "stale",
    "pinned",
    "status",
    "priority",
    "critical",
    "high priority",
    "low priority",
    "medium priority",
    "severity",
    "chore",
    "refactor",
    "refactoring",
    "dependencies",
    "dependency",
    "automated",
    "release",
    "sub-task",
    "epic",
}


def clean_label_text(label: str) -> str:
    """Strips emojis, prefixes, and punctuation from label strings."""
    if not label or not isinstance(label, str):
        return ""
    # Strip common prefixes like 'type:', 'kind:', 'area:', 'status:', 'priority:'
    cleaned = re.sub(r"^(?:type|kind|area|status|priority|severity|cat)\s*:\s*", "", label, flags=re.IGNORECASE)
    # Strip emojis and punctuation except + and #
    cleaned = re.sub(r"[^\w\s\+\#\.\-]", "", cleaned).strip().lower()
    return cleaned


def is_non_technical_label(label: str) -> bool:
    """Checks whether a label represents an issue workflow/type rather than a developer skill."""
    cleaned = clean_label_text(label)
    if not cleaned:
        return True
    if cleaned in NON_TECHNICAL_LABELS:
        return True
    for non_tech in NON_TECHNICAL_LABELS:
        if non_tech in cleaned.split():
            return True
    return False


def is_technical_skill(skill: str) -> bool:
    """Returns True if the string corresponds to a known technical skill or language/tool."""
    if not skill or not isinstance(skill, str):
        return False
    if is_non_technical_label(skill):
        return False
    cleaned = skill.strip().lower()
    return cleaned in CANONICAL_SKILL_MAP


def filter_technical_skills(skills: Optional[List[str]]) -> List[str]:
    """Filters out issue labels, workflow types, and non-technical tags."""
    if not skills:
        return []
    filtered = []
    for s in skills:
        if s and not is_non_technical_label(s):
            filtered.append(s)
    return filtered


def normalize_skill(skill: str) -> str:
    """
    Deterministically normalizes a single skill string.
    - Matches against canonical aliases (case-insensitively).
    - Preserves unknown skills without discarding them.
    - Formats unknown skills cleanly.
    """
    if not skill or not isinstance(skill, str):
        return ""

    cleaned = skill.strip()
    if not cleaned:
        return ""

    # If this is clearly a non-technical issue label, do not treat as skill
    if is_non_technical_label(cleaned):
        return ""

    lookup_key = cleaned.lower()
    # Direct alias lookup
    if lookup_key in CANONICAL_SKILL_MAP:
        return CANONICAL_SKILL_MAP[lookup_key]

    # Special handling for trailing version numbers, e.g. "python 3.10" -> "Python"
    base_match = re.match(r"^([a-zA-Z#+]+)[\s_-]*\d+(?:\.\d+)*$", lookup_key)
    if base_match:
        candidate_base = base_match.group(1)
        if candidate_base in CANONICAL_SKILL_MAP:
            return CANONICAL_SKILL_MAP[candidate_base]

    # Preserve unknown skills cleanly:
    # If entirely lowercase or all uppercase (and > 3 chars), format title case
    if cleaned.islower():
        # Title case words separated by spaces or hyphens
        return " ".join(word.capitalize() for word in cleaned.split())
    elif cleaned.isupper() and len(cleaned) > 3:
        return " ".join(word.capitalize() for word in cleaned.split())

    return cleaned


def normalize_skill_list(skills: Optional[List[str]]) -> List[str]:
    """
    Normalizes a list of skill strings:
    - Normalizes each skill name.
    - Drops empty entries.
    - Deduplicates case-insensitively while preserving original order.
    """
    if not skills:
        return []

    normalized_list: List[str] = []
    seen_keys = set()

    for item in skills:
        norm = normalize_skill(item)
        if not norm:
            continue
        key = norm.lower()
        if key not in seen_keys:
            seen_keys.add(key)
            normalized_list.append(norm)

    return normalized_list


def normalize_profile(profile: Optional[DeveloperSkillProfile]) -> DeveloperSkillProfile:
    """
    Normalizes all fields of a DeveloperSkillProfile deterministically.
    """
    if not profile:
        return DeveloperSkillProfile()

    # Validate experience level
    exp = (profile.experience_level or "beginner").strip().lower()
    if exp not in ("beginner", "intermediate", "advanced"):
        exp = "beginner"

    return DeveloperSkillProfile(
        programming_languages=normalize_skill_list(profile.programming_languages),
        frameworks=normalize_skill_list(profile.frameworks),
        tools=normalize_skill_list(profile.tools),
        domains=normalize_skill_list(profile.domains),
        experience_level=exp,
        interests=normalize_skill_list(profile.interests),
    )
