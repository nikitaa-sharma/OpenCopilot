"""
AI Contribution Guide Service for OpenSource Copilot (Phase 11).

Orchestrates:
1. GitHub issue metadata retrieval.
2. RAG context retrieval via ContributionGuideContextService.
3. LLM invocation with structured contribution guide prompts.
4. Safe JSON parsing with fallback normalization.
5. Strict source validation: eliminates hallucinated file paths not present
   in actual retrieved chunks (mirrors RepositoryChatService._validate_sources).
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.contribution.context import (
    ContributionContextData,
    ContributionGuideContextService,
    contribution_guide_context_service,
)
from app.contribution.models import (
    ContributionGuide,
    ContributionGuideCodeArea,
    ContributionGuideEvidence,
    ContributionGuideFile,
    ContributionGuideRequest,
    ContributionGuideResponse,
    ContributionGuideStep,
    ContributionGuideTestItem,
    ContributionGuideUnderstanding,
)
from app.core.config import settings
from app.prompts.contribution_guide import (
    CONTRIBUTION_GUIDE_SYSTEM_PROMPT,
    build_contribution_guide_user_prompt,
)
from app.schemas.repository import IssueItem
from app.services.github_service import github_service, parse_github_url
from app.services.llm_factory import get_llm_provider
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ContributionGuideService:
    """
    Main domain service for AI Contribution Guide generation.
    Decoupled from specific LLM providers and database models.
    """

    def __init__(
        self,
        context_service: Optional[ContributionGuideContextService] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.context_service = context_service or contribution_guide_context_service
        self._llm_provider = llm_provider

    @property
    def llm_provider(self) -> LLMProvider:
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    async def generate_guide(
        self,
        request: ContributionGuideRequest,
        session: Optional[AsyncSession] = None,
    ) -> ContributionGuideResponse:
        """
        Generate a grounded AI contribution guide for a specific GitHub issue.

        Flow:
        1. Fetch issue metadata from GitHub.
        2. Retrieve repository context via RAG.
        3. Build LLM prompt and invoke provider.
        4. Parse structured output, validate sources, and return response.
        """
        owner = request.owner.strip()
        repo = request.repo.strip()
        issue_number = request.issue_number

        # Step 1: Fetch issue metadata from GitHub
        issue_data = await github_service.fetch_single_issue(owner, repo, issue_number)
        issue = IssueItem(
            id=issue_data.get("id"),
            number=issue_data.get("number", issue_number),
            title=issue_data.get("title", f"Issue #{issue_number}"),
            body=issue_data.get("body", ""),
            state=issue_data.get("state", "open"),
            html_url=issue_data.get("html_url", f"https://github.com/{owner}/{repo}/issues/{issue_number}"),
            labels=issue_data.get("labels", []),
            user=issue_data.get("user"),
            comments_count=issue_data.get("comments_count", 0),
            created_at=issue_data.get("created_at"),
            updated_at=issue_data.get("updated_at"),
        )

        # Step 2: Retrieve repository context using RAG
        context_data: ContributionContextData = await self.context_service.get_context_for_issue(
            owner=owner,
            repo=repo,
            issue_title=issue.title,
            issue_body=issue.body,
            branch=request.branch,
            top_k=request.top_k,
            session=session,
        )

        # Step 3: Handle no-context scenario safely
        if context_data.chunks_count == 0 or not context_data.context_text.strip():
            logger.info(
                f"No context found for contribution guide: {owner}/{repo}#{issue_number}"
            )
            return ContributionGuideResponse(
                issue=issue,
                guide=ContributionGuide(
                    issue_understanding=ContributionGuideUnderstanding(
                        summary=issue.title,
                        problem="Unable to determine — no repository context was retrieved.",
                        expected_outcome="Unable to determine — repository needs to be indexed first.",
                    ),
                    uncertainties=[
                        "No repository context could be retrieved. Please ensure the repository "
                        "is indexed using the RAG indexing endpoint before generating a contribution guide."
                    ],
                ),
                retrieval_mode="none",
                sources=[],
                uncertainties=[
                    "Repository context for this issue was not found in the indexed files."
                ],
            )

        # Step 4: Collect developer skills for prompt personalization
        developer_skills: Optional[List[str]] = None
        if request.profile:
            skills = []
            skills.extend(request.profile.programming_languages or [])
            skills.extend(request.profile.frameworks or [])
            skills.extend(request.profile.tools or [])
            skills.extend(request.profile.domains or [])
            if skills:
                developer_skills = skills

        # Step 5: Build prompts
        user_prompt = build_contribution_guide_user_prompt(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            issue_title=issue.title,
            issue_body=issue.body or "",
            issue_labels=issue.labels,
            context=context_data.context_text,
            branch=request.branch,
            developer_skills=developer_skills,
        )

        # Step 6: Invoke LLM provider
        logger.info(
            f"Invoking LLM for contribution guide: {owner}/{repo}#{issue_number} | "
            f"chunks={context_data.chunks_count} | mode={context_data.retrieval_mode}"
        )
        raw_output = await self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=CONTRIBUTION_GUIDE_SYSTEM_PROMPT,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            json_mode=True,
        )

        # Step 7: Parse structured output
        parsed = self._safe_parse_response(raw_output)

        # Step 8: Validate sources against retrieved chunks
        validated_evidence = self._validate_sources(
            evidence=parsed.get("evidence", []),
            retrieved_evidence=context_data.evidence,
        )

        # Step 9: Build structured guide from parsed output
        guide = self._build_guide(parsed, validated_evidence)

        uncertainties = parsed.get("uncertainties", [])
        if not isinstance(uncertainties, list):
            uncertainties = [str(uncertainties)] if uncertainties else []

        return ContributionGuideResponse(
            issue=issue,
            guide=guide,
            retrieval_mode=context_data.retrieval_mode,
            sources=validated_evidence,
            uncertainties=[str(u) for u in uncertainties if u],
        )

    def _safe_parse_response(self, text: str) -> Dict[str, Any]:
        """
        Safely extracts and parses JSON output from the LLM.
        Mirrors RepositoryChatService._safe_parse_response with fallback heuristics.
        """
        cleaned = text.strip()

        # Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Attempt direct JSON parse
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # Attempt regex extraction of JSON object
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        # Safe fallback
        logger.warning("LLM output could not be parsed as JSON for contribution guide. Falling back.")
        return {
            "issue_understanding": {
                "summary": "Unable to parse structured guide.",
                "problem": text.strip()[:500],
                "expected_outcome": "Please retry or rephrase.",
            },
            "evidence": [],
            "uncertainties": ["Structured JSON parsing failed; raw LLM response could not be interpreted."],
        }

    def _validate_sources(
        self,
        evidence: List[Any],
        retrieved_evidence: List[ContributionGuideEvidence],
    ) -> List[ContributionGuideEvidence]:
        """
        Validates model citations against actual retrieved repository chunks.
        Mirrors RepositoryChatService._validate_sources logic.

        Rules:
        1. Never trust the LLM to invent source paths.
        2. Only files in retrieved_evidence can be exposed as verified evidence.
        3. If model provides no valid citations, fall back to top retrieved sources.
        """
        retrieved_by_path: Dict[str, List[ContributionGuideEvidence]] = {}
        for e in retrieved_evidence:
            retrieved_by_path.setdefault(e.path, []).append(e)

        validated: List[ContributionGuideEvidence] = []
        seen_paths: Set[str] = set()

        if isinstance(evidence, list):
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path", "")).strip()
                if not path:
                    continue

                # Check if path was retrieved
                matching = retrieved_by_path.get(path)
                if not matching:
                    # Also try suffix matching
                    matching = [
                        ev for p, evs in retrieved_by_path.items()
                        if p.endswith(path) or path.endswith(p)
                        for ev in evs
                    ]

                if matching and path not in seen_paths:
                    seen_paths.add(path)
                    primary = matching[0]

                    start_line = primary.start_line
                    end_line = primary.end_line
                    if item.get("start_line") is not None and isinstance(item.get("start_line"), int):
                        start_line = item.get("start_line")
                    if item.get("end_line") is not None and isinstance(item.get("end_line"), int):
                        end_line = item.get("end_line")

                    reason = str(item.get("reason", "")).strip() or primary.reason

                    validated.append(
                        ContributionGuideEvidence(
                            path=primary.path,
                            chunk_id=primary.chunk_id,
                            start_line=start_line,
                            end_line=end_line,
                            category=primary.category,
                            score=primary.score,
                            reason=reason,
                        )
                    )

        # Fallback: include top retrieved sources if no valid LLM citations
        if not validated:
            for e in retrieved_evidence[: settings.RAG_TOP_K]:
                if e.path not in seen_paths:
                    seen_paths.add(e.path)
                    validated.append(e)

        return validated

    def _build_guide(
        self,
        parsed: Dict[str, Any],
        validated_evidence: List[ContributionGuideEvidence],
    ) -> ContributionGuide:
        """
        Constructs a validated ContributionGuide from parsed LLM output.
        Uses safe extraction with defaults for missing or malformed fields.
        """
        # Issue understanding
        understanding_raw = parsed.get("issue_understanding", {})
        if not isinstance(understanding_raw, dict):
            understanding_raw = {}
        issue_understanding = ContributionGuideUnderstanding(
            summary=str(understanding_raw.get("summary", "")).strip() or "Not determined",
            problem=str(understanding_raw.get("problem", "")).strip() or "Not determined",
            expected_outcome=str(understanding_raw.get("expected_outcome", "")).strip() or "Not determined",
        )

        # Prerequisites
        prerequisites = self._safe_string_list(parsed.get("prerequisites", []))

        # Relevant files (validated against evidence)
        evidence_paths = {e.path for e in validated_evidence}
        relevant_files: List[ContributionGuideFile] = []
        for item in self._safe_dict_list(parsed.get("relevant_files", [])):
            path = str(item.get("path", "")).strip()
            if not path:
                continue
            # Only include files that appear in retrieved evidence
            is_verified = path in evidence_paths or any(
                p.endswith(path) or path.endswith(p) for p in evidence_paths
            )
            if is_verified:
                relevant_files.append(
                    ContributionGuideFile(
                        path=path,
                        role=str(item.get("role", "source")).strip(),
                        reason=str(item.get("reason", "")).strip() or "Referenced in repository context",
                    )
                )

        # Implementation plan
        implementation_plan: List[ContributionGuideStep] = []
        for item in self._safe_dict_list(parsed.get("implementation_plan", [])):
            step_num = item.get("step")
            if not isinstance(step_num, int):
                step_num = len(implementation_plan) + 1
            implementation_plan.append(
                ContributionGuideStep(
                    step=step_num,
                    title=str(item.get("title", "")).strip() or f"Step {step_num}",
                    description=str(item.get("description", "")).strip() or "No description provided.",
                    files=self._safe_string_list(item.get("files", [])),
                )
            )

        # Code areas (validated)
        code_areas: List[ContributionGuideCodeArea] = []
        for item in self._safe_dict_list(parsed.get("code_areas", [])):
            path = str(item.get("path", "")).strip()
            if not path:
                continue
            is_verified = path in evidence_paths or any(
                p.endswith(path) or path.endswith(p) for p in evidence_paths
            )
            if is_verified:
                code_areas.append(
                    ContributionGuideCodeArea(
                        path=path,
                        area=str(item.get("area", "")).strip() or "General",
                        guidance=str(item.get("guidance", "")).strip() or "Inspect this area.",
                    )
                )

        # Testing plan
        testing_plan: List[ContributionGuideTestItem] = []
        for item in self._safe_dict_list(parsed.get("testing_plan", [])):
            testing_plan.append(
                ContributionGuideTestItem(
                    type=str(item.get("type", "unit")).strip(),
                    description=str(item.get("description", "")).strip() or "Run tests.",
                    files=self._safe_string_list(item.get("files", [])),
                )
            )

        # Simple list fields
        documentation_plan = self._safe_string_list(parsed.get("documentation_plan", []))
        pull_request_checklist = self._safe_string_list(parsed.get("pull_request_checklist", []))
        learning_opportunities = self._safe_string_list(parsed.get("learning_opportunities", []))
        uncertainties = self._safe_string_list(parsed.get("uncertainties", []))

        return ContributionGuide(
            issue_understanding=issue_understanding,
            prerequisites=prerequisites,
            relevant_files=relevant_files,
            implementation_plan=implementation_plan,
            code_areas=code_areas,
            testing_plan=testing_plan,
            documentation_plan=documentation_plan,
            pull_request_checklist=pull_request_checklist,
            learning_opportunities=learning_opportunities,
            uncertainties=uncertainties,
            evidence=validated_evidence,
        )

    @staticmethod
    def _safe_string_list(items: Any) -> List[str]:
        """Safely convert to list of non-empty strings."""
        if not isinstance(items, list):
            return [str(items)] if items else []
        return [str(i).strip() for i in items if i and str(i).strip()]

    @staticmethod
    def _safe_dict_list(items: Any) -> List[Dict[str, Any]]:
        """Safely convert to list of dicts."""
        if not isinstance(items, list):
            return []
        return [i for i in items if isinstance(i, dict)]


contribution_guide_service = ContributionGuideService()
