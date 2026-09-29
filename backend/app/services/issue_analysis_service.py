import json
import logging
from typing import Dict, List, Optional
from pydantic import ValidationError

from app.core.config import settings
from app.prompts.issue_analysis import (
    ISSUE_ANALYSIS_SYSTEM_PROMPT,
    format_issue_analysis_user_prompt,
)
from app.schemas.repository import (
    ContextStats,
    IssueAIAnalysis,
    IssueAIAnalysisResponse,
    RepositoryInfo,
    RepositoryRef,
    TreeItem,
)
from app.services.github_service import github_service, parse_github_url
from app.services.issue_context_builder import IssueContextBuilder, issue_context_builder
from app.services.llm_factory import get_llm_provider
from app.services.llm_provider import LLMProvider
from app.services.repository_analysis_service import (
    AIAnalysisValidationError,
    sanitize_json_response,
)
from app.services.repository_ingestion_service import repository_ingestion_service

logger = logging.getLogger(__name__)


class IssueAnalysisService:
    """
    Orchestrates end-to-end AI issue analysis and recommendations:
    GitHub Issue & Repo Context -> Targeted Context Builder -> LLM Provider -> Validated Pydantic Analysis.
    """

    def __init__(
        self,
        context_builder: Optional[IssueContextBuilder] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.context_builder = context_builder or issue_context_builder
        self._custom_llm_provider = llm_provider

    def _get_provider(self) -> LLMProvider:
        if self._custom_llm_provider:
            return self._custom_llm_provider
        return get_llm_provider()

    async def analyze_issue_with_ai(
        self,
        url: str,
        issue_number: int,
        branch: Optional[str] = None,
    ) -> IssueAIAnalysisResponse:
        """
        Runs comprehensive, grounded AI analysis for a specific GitHub issue.

        Args:
            url: Public GitHub repository URL.
            issue_number: The issue number to analyze.
            branch: Optional branch override.

        Returns:
            IssueAIAnalysisResponse with validated structured issue analysis.
        """
        # 1. Parse repository coordinates
        owner, repo = parse_github_url(url)
        logger.info(f"Initiating AI issue analysis for {owner}/{repo}#{issue_number}")

        # 2. Fetch repository metadata and target issue
        repo_data = await github_service.fetch_repository(owner, repo)
        repository_info = RepositoryInfo(**repo_data)
        effective_branch = branch or repository_info.default_branch

        languages = await github_service.fetch_languages(owner, repo)
        readme_data = await github_service.fetch_readme(owner, repo)
        readme_content = readme_data.get("content") if readme_data else None

        issue_data = await github_service.fetch_single_issue(owner, repo, issue_number)

        # 3. Fetch recursive tree
        tree_resp = await repository_ingestion_service.get_repository_tree(
            owner=owner, repo=repo, branch=effective_branch
        )
        tree_items = [TreeItem(**item) for item in tree_resp.get("tree", [])]

        # 4. Extract keywords from issue and rank candidate files
        keywords = self.context_builder.extract_keywords_from_issue(
            title=issue_data.get("title", ""),
            body=issue_data.get("body", "") or "",
            labels=issue_data.get("labels", []),
        )
        ranked_candidates = self.context_builder.rank_candidate_files(tree_items, keywords)

        # 5. Fetch content of top candidate files (up to 3 unique files) to ground investigation
        file_contents: Dict[str, str] = {}
        seen_paths = set()
        unique_candidates = []
        for item, _ in ranked_candidates:
            if item.path not in seen_paths and getattr(item, "type", "file") == "file":
                seen_paths.add(item.path)
                unique_candidates.append(item)
            if len(unique_candidates) >= 3:
                break

        for item in unique_candidates:
            if item.path in file_contents:
                continue
            try:
                content_resp = await repository_ingestion_service.get_file_content(
                    owner=owner,
                    repo=repo,
                    path=item.path,
                    branch=effective_branch,
                )
                if not content_resp.get("is_binary") and content_resp.get("content"):
                    file_contents[item.path] = content_resp["content"]
            except Exception as exc:
                logger.warning(
                    f"Could not retrieve candidate file content for '{item.path}': {exc}"
                )

        # 6. Build structured prompt context
        context_str, stats = self.context_builder.build_context(
            issue=issue_data,
            repository=repository_info,
            languages=languages,
            tree=tree_items,
            readme_content=readme_content,
            file_contents=file_contents,
        )

        # 7. Formulate prompt
        user_prompt = format_issue_analysis_user_prompt(context_str)
        provider = self._get_provider()

        # 8. Call LLM provider
        logger.info(
            f"Calling LLM provider ({settings.LLM_PROVIDER}) for issue #{issue_number} in {owner}/{repo}"
        )
        raw_response = await provider.generate(
            prompt=user_prompt,
            system_prompt=ISSUE_ANALYSIS_SYSTEM_PROMPT,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            json_mode=True,
        )

        # 9. Safely parse and validate structured JSON
        sanitized = sanitize_json_response(raw_response)
        try:
            parsed_dict = json.loads(sanitized)
        except json.JSONDecodeError as exc:
            logger.error(
                f"Malformed JSON from LLM for issue #{issue_number}: {exc}\nRaw output excerpt: {raw_response[:300]}"
            )
            raise AIAnalysisValidationError(
                f"The AI model returned malformed output that could not be parsed as JSON: {exc}"
            ) from exc

        try:
            analysis = IssueAIAnalysis.model_validate(parsed_dict)
        except ValidationError as exc:
            logger.error(f"Pydantic validation error on issue LLM output: {exc}")
            raise AIAnalysisValidationError(
                f"The AI model output did not match the expected issue analysis schema: {exc}"
            ) from exc

        # 10. Assemble and return typed response
        response = IssueAIAnalysisResponse(
            repository=RepositoryRef(
                owner=owner,
                name=repo,
                branch=effective_branch,
            ),
            issue_number=issue_number,
            issue_title=issue_data.get("title", ""),
            issue_url=issue_data.get("html_url", ""),
            analysis=analysis,
            provider=settings.LLM_PROVIDER,
            model=getattr(provider, "model", settings.OLLAMA_MODEL),
            context_stats=ContextStats(
                files_included=stats["files_included"],
                total_context_chars=stats["total_context_chars"],
            ),
        )

        # Cache analysis for personalized recommendations
        try:
            from app.services.skill_matching_service import skill_matching_service
            skill_matching_service.cache_analysis(owner, repo, issue_number, response)
        except Exception as exc:
            logger.debug(f"Could not cache issue analysis: {exc}")

        return response


issue_analysis_service = IssueAnalysisService()
