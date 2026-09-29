"""
Service for 'Repository Structure Explainer' / 'Understand This Repository'.
Provides beginner-friendly, grounded explanations of repository purpose, architecture,
directories, important files, execution flows, and onboarding guides.
Reuses existing GitHub ingestion and RAG infrastructure without executing repository code.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.core.config import settings
from app.prompts.structure_explainer import (
    STRUCTURE_EXPLAINER_SYSTEM_PROMPT,
    format_structure_explainer_user_prompt,
)
from app.rag.service import repository_rag_service
from app.schemas.repository import (
    ContextStats,
    ReadmeInfo,
    RepositoryInfo,
    RepositoryRef,
    TreeItem,
)
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
from app.services.github_service import github_service, parse_github_url
from app.services.llm_factory import get_llm_provider
from app.services.llm_provider import LLMProvider
from app.services.repository_analysis_service import sanitize_json_response
from app.services.repository_file_filter import classify_file, detect_language
from app.services.repository_ingestion_service import repository_ingestion_service

logger = logging.getLogger(__name__)

# Known manifest filenames
MANIFEST_FILENAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "pipfile",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "gemfile",
    "composer.json",
    "mix.exs",
}

# Known configuration filenames
CONFIG_FILENAMES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "dockerfile",
    ".env.example",
    "tsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "webpack.config.js",
    "next.config.js",
    "next.config.mjs",
    "tailwind.config.js",
    "tailwind.config.ts",
    "pytest.ini",
    "jest.config.js",
    "vitest.config.ts",
}

# Known entrypoint naming patterns
ENTRYPOINT_PATTERNS = [
    re.compile(r"^(src/|app/)?(main|app|index|server|manage|cli)\.(py|ts|js|go|rs|rb)$", re.IGNORECASE),
    re.compile(r"^(cmd|bin)/.*", re.IGNORECASE),
]


def clean_mermaid_diagram(raw_mermaid: str, fallback_components: Optional[List[str]] = None) -> str:
    """
    Ensures the Mermaid diagram is valid, clean, and GitHub-compatible.
    Normalizes to 'flowchart TD' and sanitizes node syntax.
    """
    if not raw_mermaid or not raw_mermaid.strip():
        return generate_fallback_mermaid(fallback_components)

    text = raw_mermaid.strip()
    # Strip markdown code fences if present
    match = re.search(r"```(?:mermaid)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    # Ensure header exists
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return generate_fallback_mermaid(fallback_components)

    first_line = lines[0].lower()
    if not (first_line.startswith("flowchart") or first_line.startswith("graph")):
        lines.insert(0, "flowchart TD")
    elif first_line.startswith("graph"):
        # Normalize graph TD to flowchart TD
        lines[0] = "flowchart TD"

    cleaned_lines = [lines[0]]
    for line in lines[1:]:
        # Remove any stray backticks or html comments
        cleaned = re.sub(r"<!--.*?-->", "", line)
        cleaned = cleaned.replace("`", "").strip()
        if not cleaned:
            continue
        cleaned_lines.append(f"    {cleaned}")

    result = "\n".join(cleaned_lines)
    # Check if there are valid connections (-->)
    if "-->" not in result and "---" not in result:
        return generate_fallback_mermaid(fallback_components)

    return result


def generate_fallback_mermaid(components: Optional[List[str]] = None) -> str:
    """
    Generates a clean, valid GitHub-compatible Mermaid flowchart TD based on identified components.
    """
    if not components or len(components) < 2:
        return (
            "flowchart TD\n"
            '    User["User / Client"] --> Entry["Entry Point"]\n'
            '    Entry --> Core["Core Application Logic"]\n'
            '    Core --> Services["Services & Modules"]\n'
            '    Services --> Storage["Data / Storage Layer"]'
        )

    # Build sequential or layered connections from components
    nodes = []
    edges = []
    for idx, comp in enumerate(components[:6]):
        node_id = f"Node{idx+1}"
        safe_label = comp.replace('"', "'")
        nodes.append(f'    {node_id}["{safe_label}"]')
        if idx > 0:
            edges.append(f"    Node{idx} --> Node{idx+1}")

    return "flowchart TD\n" + "\n".join(nodes) + "\n" + "\n".join(edges)


class StructureExplainerService:
    """
    Orchestration service for 'Repository Structure Explainer' / 'Understand This Repository'.
    Extracts structure, inspects manifests, invokes RAG retrieval for deep context,
    and prompts the LLM to deliver a beginner-friendly architectural walkthrough.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._custom_llm_provider = llm_provider

    def _get_provider(self) -> LLMProvider:
        if self._custom_llm_provider:
            return self._custom_llm_provider
        return get_llm_provider()

    async def explain_repository_structure(
        self,
        url: str,
        branch: Optional[str] = None,
    ) -> StructureExplainerResponse:
        """
        Main entry point for repository structure explanation.
        """
        owner, repo = parse_github_url(url)
        logger.info(f"Initiating Repository Structure Explainer for {owner}/{repo}")

        # 1. Fetch metadata, languages, and README
        repo_data = await github_service.fetch_repository(owner, repo)
        repository_info = RepositoryInfo(**repo_data)
        effective_branch = branch or repository_info.default_branch

        languages = await github_service.fetch_languages(owner, repo)
        readme_data = await github_service.fetch_readme(owner, repo)
        readme = ReadmeInfo(**readme_data) if readme_data else None

        # 2. Fetch full repository tree
        tree_resp = await repository_ingestion_service.get_repository_tree(
            owner=owner, repo=repo, branch=effective_branch
        )
        tree_items = [TreeItem(**item) for item in tree_resp.get("tree", [])]

        # 3. Analyze top-level directories and find key files
        top_level_dirs, key_files = self._extract_directory_and_file_candidates(tree_items)

        # 4. Fetch content for high-priority files (manifests, configs, entry points)
        file_contents = await self._fetch_candidate_contents(
            owner=owner,
            repo=repo,
            branch=effective_branch,
            key_files=key_files,
            readme=readme,
        )

        # 5. Query RAG infrastructure for grounded architecture insights
        rag_context_snippets = await self._retrieve_rag_context(
            url=url,
            branch=effective_branch,
        )

        # 6. Format context string
        context_str = self._build_explainer_context(
            repository=repository_info,
            languages=languages,
            readme=readme,
            tree_items=tree_items,
            top_level_dirs=top_level_dirs,
            file_contents=file_contents,
            rag_snippets=rag_context_snippets,
        )

        # 7. Prompt LLM provider
        user_prompt = format_structure_explainer_user_prompt(context_str)
        provider = self._get_provider()

        logger.info(f"Calling LLM provider ({settings.LLM_PROVIDER}) for structure explainer on {owner}/{repo}")
        try:
            raw_response = await provider.generate(
                prompt=user_prompt,
                system_prompt=STRUCTURE_EXPLAINER_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
                json_mode=True,
            )
            sanitized = sanitize_json_response(raw_response)
            parsed_dict = json.loads(sanitized)
            explainer_analysis = StructureExplainerAnalysis.model_validate(parsed_dict)
            # Ensure valid mermaid diagram
            explainer_analysis.architecture.diagram_mermaid = clean_mermaid_diagram(
                explainer_analysis.architecture.diagram_mermaid,
                explainer_analysis.architecture.layers,
            )
        except Exception as exc:
            logger.warning(
                f"LLM generation/validation failed for structure explainer ({exc}). Building grounded heuristic fallback."
            )
            explainer_analysis = self._build_heuristic_explainer(
                repository=repository_info,
                languages=languages,
                readme=readme,
                tree_items=tree_items,
                top_level_dirs=top_level_dirs,
                key_files=key_files,
            )

        return StructureExplainerResponse(
            repository=RepositoryRef(
                owner=owner,
                name=repo,
                branch=effective_branch,
            ),
            explainer=explainer_analysis,
            provider=settings.LLM_PROVIDER,
            model=getattr(provider, "model", settings.OLLAMA_MODEL),
            context_stats=ContextStats(
                files_included=len(file_contents) + (1 if readme and readme.content else 0),
                total_context_chars=len(context_str),
            ),
        )

    def _extract_directory_and_file_candidates(
        self, tree_items: List[TreeItem]
    ) -> Tuple[Dict[str, List[str]], List[TreeItem]]:
        """
        Group files by top-level directory and identify architecturally significant files.
        """
        top_level_dirs: Dict[str, List[str]] = {}
        key_files: List[TreeItem] = []

        for item in tree_items:
            path = item.path
            parts = path.split("/")
            if len(parts) > 1:
                top_dir = parts[0] + "/"
                if top_dir not in top_level_dirs:
                    top_level_dirs[top_dir] = []
                top_level_dirs[top_dir].append(path)

            filename = parts[-1].lower()

            # Priority 1: Manifests
            if filename in MANIFEST_FILENAMES:
                key_files.append(item)
            # Priority 2: Config files
            elif filename in CONFIG_FILENAMES or path.startswith(".github/workflows/"):
                key_files.append(item)
            # Priority 3: Entry points
            elif any(pattern.match(path) for pattern in ENTRYPOINT_PATTERNS):
                key_files.append(item)
            # Priority 4: Key routing / db / test files
            elif any(k in path.lower() for k in ["route", "router", "models", "schema", "database", "service"]):
                if item.type == "file" and not item.path.endswith(".png") and not item.path.endswith(".svg"):
                    key_files.append(item)

        # Deduplicate key files
        unique_key_files: List[TreeItem] = []
        seen = set()
        for kf in key_files:
            if kf.path not in seen:
                seen.add(kf.path)
                unique_key_files.append(kf)

        return top_level_dirs, unique_key_files[:15]

    async def _fetch_candidate_contents(
        self,
        owner: str,
        repo: str,
        branch: str,
        key_files: List[TreeItem],
        readme: Optional[ReadmeInfo],
    ) -> Dict[str, str]:
        """
        Safely fetch file contents for top priority candidate files.
        """
        file_contents: Dict[str, str] = {}
        for item in key_files:
            if readme and item.path.lower() == readme.name.lower():
                continue
            try:
                content_resp = await repository_ingestion_service.get_file_content(
                    owner=owner,
                    repo=repo,
                    path=item.path,
                    branch=branch,
                )
                if not content_resp.get("is_binary") and content_resp.get("content"):
                    raw = content_resp["content"]
                    # Cap single file content to avoid budget overflow
                    file_contents[item.path] = raw[:4000]
            except Exception as exc:
                logger.debug(f"Could not fetch content for candidate '{item.path}': {exc}")

        return file_contents

    async def _retrieve_rag_context(self, url: str, branch: str) -> List[str]:
        """
        Queries the existing RAG service to pull relevant architectural snippets.
        """
        rag_snippets = []
        try:
            # Query for entry points and architecture
            res = await repository_rag_service.retrieve_for_query(
                url=url,
                query="application entry point architecture routes services database communication flow",
                branch=branch,
                top_k=4,
            )
            for chunk in res.results:
                rag_snippets.append(
                    f"[{chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})]:\n{chunk.content[:600]}"
                )
        except Exception as exc:
            logger.debug(f"RAG retrieval skipped or unavailable for structure explainer: {exc}")

        return rag_snippets

    def _build_explainer_context(
        self,
        repository: RepositoryInfo,
        languages: Dict[str, int],
        readme: Optional[ReadmeInfo],
        tree_items: List[TreeItem],
        top_level_dirs: Dict[str, List[str]],
        file_contents: Dict[str, str],
        rag_snippets: List[str],
    ) -> str:
        """
        Builds a comprehensive, bounded context prompt string.
        """
        sections = []

        # 1. Repository metadata
        sections.append(
            f"REPOSITORY METADATA:\n"
            f"- Full Name: {repository.full_name}\n"
            f"- Description: {repository.description or 'No description provided'}\n"
            f"- Primary Language: {repository.language or 'Not specified'}\n"
            f"- Default Branch: {repository.default_branch}\n"
            f"- Stargazers: {repository.stars}\n"
            f"- Open Issues: {repository.open_issues_count}"
        )

        # 2. Languages
        total_bytes = sum(languages.values()) or 1
        lang_str = ", ".join(
            f"{lang} ({bytes_cnt * 100 // total_bytes}%)"
            for lang, bytes_cnt in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:6]
        )
        sections.append(f"DETECTED LANGUAGES:\n{lang_str or 'None detected'}")

        # 3. Top-level directories breakdown
        dir_breakdown = []
        for dname, fpaths in sorted(top_level_dirs.items()):
            subdirs = set()
            for p in fpaths:
                parts = p.split("/")
                if len(parts) > 2:
                    subdirs.add(f"{parts[0]}/{parts[1]}")
            sample_subdirs = ", ".join(sorted(subdirs)[:3]) if subdirs else "No subdirectories"
            dir_breakdown.append(f"- {dname}: {len(fpaths)} files (sample subdirs: {sample_subdirs})")
        sections.append("TOP-LEVEL DIRECTORIES:\n" + "\n".join(dir_breakdown))

        # 4. Filtered file tree summary
        tree_summary = "\n".join(f"- {item.path} ({item.type})" for item in tree_items[:80])
        if len(tree_items) > 80:
            tree_summary += f"\n... [{len(tree_items) - 80} more files omitted for length]"
        sections.append(f"REPOSITORY FILE TREE (SAMPLE):\n{tree_summary}")

        # 5. README Excerpt
        if readme and readme.content:
            sections.append(f"README ({readme.name}) EXCERPT:\n{readme.content[:3500]}")

        # 6. Priority file excerpts
        if file_contents:
            file_excerpts = []
            for path, content in file_contents.items():
                file_excerpts.append(f"=== File: {path} ===\n{content[:1500]}\n")
            sections.append("KEY FILE EXCERPTS:\n" + "\n".join(file_excerpts))

        # 7. RAG Chunks
        if rag_snippets:
            sections.append("RAG-RETRIEVED ARCHITECTURAL CHUNKS:\n" + "\n---\n".join(rag_snippets))

        return "\n\n".join(sections)

    def _build_heuristic_explainer(
        self,
        repository: RepositoryInfo,
        languages: Dict[str, int],
        readme: Optional[ReadmeInfo],
        tree_items: List[TreeItem],
        top_level_dirs: Dict[str, List[str]],
        key_files: List[TreeItem],
    ) -> StructureExplainerAnalysis:
        """
        Builds a high-quality deterministic fallback analysis when the LLM is offline or output is malformed.
        """
        primary_lang = repository.language or (list(languages.keys())[0] if languages else "Code")

        # Determine app type
        manifest_names = {item.path.split("/")[-1].lower() for item in key_files}
        tree_paths = {item.path.lower() for item in tree_items}

        app_type = "Software Library / Application"
        if "package.json" in manifest_names and ("next.config.js" in tree_paths or "next.config.mjs" in tree_paths):
            app_type = "Full-stack Next.js Web Application"
        elif "package.json" in manifest_names and "vite.config.ts" in tree_paths:
            app_type = "Frontend Web Application (Vite / React)"
        elif "pyproject.toml" in manifest_names or "setup.py" in manifest_names or "requirements.txt" in manifest_names:
            if any("fastapi" in p or "flask" in p or "django" in p for p in tree_paths):
                app_type = "Backend Web API / Service"
            else:
                app_type = "Python Package / CLI Utility"
        elif "cargo.toml" in manifest_names:
            app_type = "Rust Binary / Library"
        elif "go.mod" in manifest_names:
            app_type = "Go Service / Module"

        # Overview
        what_it_does = repository.description or f"{repository.full_name} is an open-source project written primarily in {primary_lang}."
        if readme and readme.content and len(readme.content) > 40:
            first_para = readme.content.strip().split("\n\n")[0].replace("#", "").strip()
            if len(first_para) > 30:
                what_it_does = first_para[:250]

        # Directory Explorer
        dir_details: List[DirectoryExplanationDetail] = []
        for dname, fpaths in top_level_dirs.items():
            clean_name = dname.rstrip("/")
            subdirs = list(set("/".join(p.split("/")[:2]) for p in fpaths if len(p.split("/")) > 2))[:3]
            purpose = "Core project module."
            contains = f"Contains {len(fpaths)} files implementing project functionality."
            rel = "Relates to the overall application codebase."
            evidence = f"Observed {len(fpaths)} files within {dname}"
            confidence = "high"

            if clean_name in ["src", "app", "lib"]:
                purpose = "Main application source code."
                contains = "Core components, business logic, and operational modules."
                rel = "Connected to tests/ and top-level manifests."
            elif clean_name in ["tests", "test", "__tests__"]:
                purpose = "Automated test suites."
                contains = "Unit, integration, and functional tests verifying code correctness."
                rel = "Validates the implementation in source code directories."
            elif clean_name in ["docs", "documentation"]:
                purpose = "Project documentation."
                contains = "Guides, API references, architecture notes, and contributor docs."
                rel = "Documents features and modules in the codebase."
            elif clean_name in [".github"]:
                purpose = "GitHub automation and CI/CD."
                contains = "GitHub Actions workflows, issue templates, and pull request configuration."
                rel = "Orchestrates testing, builds, and CI pipelines for the repository."
            elif clean_name in ["scripts", "tools", "bin"]:
                purpose = "Development and automation scripts."
                contains = "Utility scripts for local environment setup, linting, building, and data migration."
                rel = "Supports development and deployment processes."
            elif clean_name in ["components", "ui"]:
                purpose = "User interface components."
                contains = "Reusable UI widgets, layouts, and display elements."
                rel = "Rendered by page views and application routes."
            elif clean_name in ["api", "routes", "endpoints"]:
                purpose = "API endpoint definitions and routing."
                contains = "Request handlers, route schemas, controllers, and input validation."
                rel = "Exposes application capabilities to clients and consumers."
            else:
                purpose = f"Specialized module: {clean_name}"
                confidence = "medium"

            dir_details.append(
                DirectoryExplanationDetail(
                    name=dname,
                    purpose=purpose,
                    contains=contains,
                    important_subdirectories=subdirs,
                    relationship=rel,
                    evidence=evidence,
                    confidence=confidence,
                )
            )

        # Important Files
        file_details: List[ImportantFileDetail] = []
        if readme:
            file_details.append(
                ImportantFileDetail(
                    path=readme.name,
                    category="documentation",
                    description="Primary repository introduction, installation guidelines, and usage documentation.",
                    evidence="Root documentation file",
                )
            )

        for kf in key_files:
            fname = kf.path.split("/")[-1].lower()
            cat = "core_logic"
            desc = "Important repository file."
            if fname in MANIFEST_FILENAMES:
                cat = "manifest"
                desc = "Defines project dependencies, package metadata, and run scripts."
            elif fname in CONFIG_FILENAMES:
                cat = "config"
                desc = "Controls environment settings, build configuration, or container orchestration."
            elif "docker" in fname or ".github" in kf.path:
                cat = "devops"
                desc = "Automates containerized execution or CI/CD test workflows."
            elif any(pat.match(kf.path) for pat in ENTRYPOINT_PATTERNS):
                cat = "entry_point"
                desc = "Primary bootstrap entry point where execution starts."
            elif "test" in kf.path:
                cat = "test"
                desc = "Configuration or execution suite for automated testing."

            file_details.append(
                ImportantFileDetail(
                    path=kf.path,
                    category=cat,
                    description=desc,
                    evidence=f"File detected in repository tree ({kf.size or 0} bytes)",
                )
            )

        # Technology Map
        tech_map = TechnologyMap(
            frontend=[],
            backend=[],
            database=[],
            apis=[],
            ai_ml=[],
            testing=[],
            devops=[],
            build_tools=[],
        )

        for lang in languages.keys():
            if lang in ["TypeScript", "JavaScript", "HTML", "CSS"]:
                tech_map.frontend.append(lang)
            elif lang in ["Python", "Go", "Rust", "Java", "C++", "C#", "PHP", "Ruby"]:
                tech_map.backend.append(lang)

        for item in tree_items:
            path_l = item.path.lower()
            if "docker" in path_l and "Docker" not in tech_map.devops:
                tech_map.devops.append("Docker")
            if ".github/workflows" in path_l and "GitHub Actions" not in tech_map.devops:
                tech_map.devops.append("GitHub Actions")
            if "pytest" in path_l and "pytest" not in tech_map.testing:
                tech_map.testing.append("pytest")
            if "jest" in path_l and "Jest" not in tech_map.testing:
                tech_map.testing.append("Jest")
            if "postgres" in path_l or "sql" in path_l:
                if "SQL / Relational DB" not in tech_map.database:
                    tech_map.database.append("SQL / Relational DB")
            if "package.json" in path_l and "npm" not in tech_map.build_tools:
                tech_map.build_tools.append("npm")
            if "requirements.txt" in path_l and "pip" not in tech_map.build_tools:
                tech_map.build_tools.append("pip")

        # Entry points
        entry_points = [kf.path for kf in key_files if any(p.match(kf.path) for p in ENTRYPOINT_PATTERNS)]
        if not entry_points and key_files:
            entry_points = [key_files[0].path]

        # Mermaid
        diagram = (
            "flowchart TD\n"
            '    User["User / Client"] --> Entry["Entry Point (' + (entry_points[0] if entry_points else "Bootstrap") + ')"]\n'
            '    Entry --> Logic["Core Logic / Modules"]\n'
            '    Logic --> Services["Services & Utilities"]\n'
            '    Services --> Storage["Configuration & State"]'
        )

        # Where to start steps
        steps = [
            WhereToStartStep(
                step_number=1,
                title="1. Read Documentation & Architecture Vision",
                target_path=readme.name if readme else "README.md",
                guidance="Start with the README to understand what problem the project solves, its core terminology, and installation instructions.",
                why="Provides essential project orientation before reading any implementation code.",
            ),
            WhereToStartStep(
                step_number=2,
                title="2. Inspect Dependency & Package Manifests",
                target_path=key_files[0].path if key_files else "package.json / pyproject.toml",
                guidance="Look at the declared dependencies, build tools, and scripts to understand what external libraries power the system.",
                why="Gives an instant map of the technology stack and third-party integrations.",
            ),
            WhereToStartStep(
                step_number=3,
                title="3. Examine the Main Entry Point",
                target_path=entry_points[0] if entry_points else "main application file",
                guidance="Trace how the application is initialized, what configuration is loaded, and how routes/commands are registered.",
                why="Shows the exact sequence of events when the application starts up.",
            ),
            WhereToStartStep(
                step_number=4,
                title="4. Explore Core Source Code Directories",
                target_path=list(top_level_dirs.keys())[0] if top_level_dirs else "src/",
                guidance="Browse the primary business logic directories and study the main data structures and interfaces.",
                why="This is where the actual functionality and features live.",
            ),
            WhereToStartStep(
                step_number=5,
                title="5. Review Automated Test Suites",
                target_path="tests/",
                guidance="Inspect existing tests to see how modules are exercised and what expected inputs and outputs look like.",
                why="Tests are executable documentation showing how the code was designed to be consumed.",
            ),
            WhereToStartStep(
                step_number=6,
                title="6. Check Configuration & Deployment",
                target_path="docker-compose.yml / CI workflows",
                guidance="Review environment variables and build pipelines to see how the system runs in production environments.",
                why="Connects local development to production runtime realities.",
            ),
        ]

        return StructureExplainerAnalysis(
            overview=RepositoryOverviewDetail(
                what_it_does=what_it_does,
                main_purpose=repository.description or f"Open-source {app_type} solving domain-specific challenges.",
                primary_technologies=list(languages.keys())[:4],
                application_type=app_type,
                entry_points=entry_points,
                high_level_architecture=f"Modular architecture structured around {primary_lang} and key project directories.",
            ),
            directories=dir_details[:8],
            important_files=file_details[:10],
            architecture=ArchitectureExplanation(
                overview=f"The application is organized into distinct directories separating source code, tests, documentation, and configuration.",
                pattern=app_type,
                layers=["Entry / Bootstrap", "Core Implementation", "Services & Helpers", "Configuration & Tests"],
                diagram_mermaid=diagram,
            ),
            flow=RepositoryFlow(
                execution_start=f"Execution starts via '{entry_points[0] if entry_points else 'main file'}' or package invocation.",
                component_communication="Internal modules communicate through structured function calls and service abstractions.",
                data_entry="Input enters through CLI flags, configuration parameters, or HTTP request payloads.",
                data_processing="Data is processed and transformed through primary domain modules in the source directories.",
                data_storage="State and output are maintained in memory, configuration files, or external databases.",
                result_delivery="Final results are presented to the user via terminal output, HTTP responses, or user interface.",
            ),
            technology_map=tech_map,
            where_to_start=steps,
            confidence_evidence=(
                f"Grounded analysis based on {len(tree_items)} tree items, {len(languages)} detected languages, "
                f"and {len(file_details)} identified configuration and manifest files."
            ),
        )


structure_explainer_service = StructureExplainerService()
