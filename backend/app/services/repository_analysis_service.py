import json
import logging
import re
from typing import Dict, Optional
from pydantic import ValidationError

from app.core.config import settings
from app.prompts.repository_analysis import (
    REPOSITORY_ANALYSIS_SYSTEM_PROMPT,
    format_analysis_user_prompt,
)
from app.schemas.repository import (
    ContextStats,
    ReadmeInfo,
    RepositoryAIAnalysis,
    RepositoryAIAnalysisResponse,
    RepositoryInfo,
    RepositoryRef,
    TreeItem,
)
from app.services.github_service import github_service, parse_github_url
from app.services.llm_factory import get_llm_provider
from app.services.llm_provider import LLMProvider, LLMProviderError
from app.services.repository_context_builder import (
    RepositoryContextBuilder,
    repository_context_builder,
)
from app.services.repository_ingestion_service import repository_ingestion_service

logger = logging.getLogger(__name__)


class AIAnalysisError(Exception):
    """Base exception for AI repository analysis errors."""
    pass


class AIAnalysisValidationError(AIAnalysisError):
    """Raised when the LLM response cannot be parsed or validated against the schema."""
    pass


def sanitize_json_response(raw_text: str) -> str:
    """
    Cleans up LLM text output by removing markdown code fences or conversational preamble.
    """
    text = raw_text.strip()

    # If wrapped in markdown code fence ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    # If text still contains non-JSON prefix, extract between first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]

    return text


class RepositoryAnalysisService:
    """
    Orchestrates end-to-end AI repository architecture analysis:
    GitHub Data -> Prioritized Context -> LLM Provider -> Validated Pydantic Analysis.
    """

    def __init__(
        self,
        context_builder: Optional[RepositoryContextBuilder] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.context_builder = context_builder or repository_context_builder
        self._custom_llm_provider = llm_provider

    def _get_provider(self) -> LLMProvider:
        if self._custom_llm_provider:
            return self._custom_llm_provider
        return get_llm_provider()

    async def analyze_repository_with_ai(
        self,
        url: str,
        branch: Optional[str] = None,
    ) -> RepositoryAIAnalysisResponse:
        """
        Runs comprehensive, grounded AI analysis for a GitHub repository.

        Args:
            url: Public GitHub repository URL.
            branch: Optional branch override.

        Returns:
            RepositoryAIAnalysisResponse with validated structured analysis.
        """
        # 1. Parse repository coordinates
        owner, repo = parse_github_url(url)
        logger.info(f"Initiating AI repository analysis for {owner}/{repo}")

        # 2. Fetch repository metadata, languages, and README in parallel
        repo_data = await github_service.fetch_repository(owner, repo)
        repository_info = RepositoryInfo(**repo_data)
        effective_branch = branch or repository_info.default_branch

        languages = await github_service.fetch_languages(owner, repo)
        readme_data = await github_service.fetch_readme(owner, repo)
        readme = ReadmeInfo(**readme_data) if readme_data else None

        # 3. Fetch recursive tree
        tree_resp = await repository_ingestion_service.get_repository_tree(
            owner=owner, repo=repo, branch=effective_branch
        )
        tree_items = [TreeItem(**item) for item in tree_resp.get("tree", [])]

        # 4. Select prioritized files for context
        candidate_files = self.context_builder.select_files_for_context(tree_items)
        logger.info(
            f"Selected {len(candidate_files)} prioritized files for context building in {owner}/{repo}"
        )

        # 5. Fetch content of selected files (excluding README if already fetched)
        file_contents: Dict[str, str] = {}
        for item in candidate_files:
            # Skip if this is the primary README already present in readme_data
            if readme and item.path.lower() == readme.name.lower():
                continue

            try:
                content_resp = await repository_ingestion_service.get_file_content(
                    owner=owner,
                    repo=repo,
                    path=item.path,
                    branch=effective_branch,
                )
                # Only include non-binary, non-skipped text content
                if not content_resp.get("is_binary") and content_resp.get("content"):
                    file_contents[item.path] = content_resp["content"]
            except Exception as exc:
                logger.warning(f"Could not retrieve file content for '{item.path}': {exc}")

        # 6. Build controlled context
        context_str = self.context_builder.build_context(
            repository=repository_info,
            languages=languages,
            readme=readme,
            tree=tree_items,
            file_contents=file_contents,
        )

        # 7. Formulate prompt
        user_prompt = format_analysis_user_prompt(context_str)
        provider = self._get_provider()

        # 8. Call LLM provider
        logger.info(f"Calling LLM provider ({settings.LLM_PROVIDER}) for {owner}/{repo}")
        raw_response = await provider.generate(
            prompt=user_prompt,
            system_prompt=REPOSITORY_ANALYSIS_SYSTEM_PROMPT,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            json_mode=True,
        )

        # 9. Safely parse and validate structured JSON
        sanitized = sanitize_json_response(raw_response)
        try:
            parsed_dict = json.loads(sanitized)
        except json.JSONDecodeError as exc:
            logger.error(f"Malformed JSON from LLM: {exc}\nRaw output excerpt: {raw_response[:300]}")
            raise AIAnalysisValidationError(
                f"The AI model returned malformed output that could not be parsed as JSON: {exc}"
            ) from exc

        try:
            analysis = RepositoryAIAnalysis.model_validate(parsed_dict)
        except ValidationError as exc:
            logger.error(f"Pydantic validation error on LLM output: {exc}")
            raise AIAnalysisValidationError(
                f"The AI model output did not match the expected repository analysis schema: {exc}"
            ) from exc

        # 10. Assemble and return typed response
        return RepositoryAIAnalysisResponse(
            repository=RepositoryRef(
                owner=owner,
                name=repo,
                branch=effective_branch,
            ),
            analysis=analysis,
            provider=settings.LLM_PROVIDER,
            model=getattr(provider, "model", settings.OLLAMA_MODEL),
            context_stats=ContextStats(
                files_included=len(file_contents) + (1 if readme and readme.content else 0),
                total_context_chars=len(context_str),
            ),
        )


repository_analysis_service = RepositoryAnalysisService()
