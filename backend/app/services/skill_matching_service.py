"""
Skill Matching & Recommendation Service for Phase 10.
Computes transparent, deterministic skill match scores between developer profiles
and repository issues, generates grounded match reasons, identifies skill gaps,
and highlights learning opportunities while keeping AI difficulty estimates separate.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from app.schemas.profile import (
    DeveloperSkillProfile,
    IssueRecommendationItem,
    IssueRecommendationResponse,
    SkillMatchResult,
)
from app.schemas.repository import (
    CandidateFile,
    IssueAIAnalysis,
    IssueAIAnalysisResponse,
    IssueItem,
)
from app.services.github_service import github_service
from app.services.profile_service import profile_service
from app.services.skill_normalizer import (
    filter_technical_skills,
    is_non_technical_label,
    is_technical_skill,
    normalize_profile,
    normalize_skill,
    normalize_skill_list,
)

logger = logging.getLogger(__name__)

# File extension to programming language / skill map
EXTENSION_TO_SKILL: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "React",
    ".ts": "TypeScript",
    ".tsx": "React",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Bash",
    ".bash": "Bash",
    ".md": "Documentation",
    ".rst": "Documentation",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".dockerfile": "Docker",
}


class SkillMatchingService:
    """
    Orchestrates deterministic skill matching between developer profiles and repository issues.
    Maintains an in-memory cache of previously computed AI issue analyses to avoid redundant LLM calls.
    """

    def __init__(self):
        # Cache for computed AI issue analyses: key is (owner_lower, repo_lower, issue_number)
        self._analysis_cache: Dict[Tuple[str, str, int], IssueAIAnalysisResponse] = {}

    def cache_analysis(self, owner: str, repo: str, issue_number: int, analysis_resp: IssueAIAnalysisResponse) -> None:
        """Stores an AI issue analysis in the in-memory cache."""
        key = (owner.strip().lower(), repo.strip().lower(), issue_number)
        self._analysis_cache[key] = analysis_resp
        logger.debug(f"Cached AI analysis for {key}")

    def get_cached_analysis(self, owner: str, repo: str, issue_number: int) -> Optional[IssueAIAnalysisResponse]:
        """Retrieves a cached AI issue analysis if available."""
        key = (owner.strip().lower(), repo.strip().lower(), issue_number)
        return self._analysis_cache.get(key)

    def clear_cache(self) -> None:
        """Clears the in-memory analysis cache (useful for testing)."""
        self._analysis_cache.clear()

    def _extract_skills_from_issue_heuristic(
        self,
        issue: IssueItem,
        repo_languages: Dict[str, int],
    ) -> Tuple[List[str], str]:
        """
        Extracts candidate required skills and difficulty estimate deterministically
        when an LLM analysis has not yet been computed for the issue.
        Strictly excludes issue labels like 'enhancement', 'bug', 'good first issue' from skills.
        """
        skills: List[str] = []
        difficulty = "intermediate"

        # 1. Infer from repository primary languages
        for lang_name in sorted(repo_languages.keys(), key=lambda k: repo_languages[k], reverse=True)[:2]:
            norm_lang = normalize_skill(lang_name)
            if norm_lang and is_technical_skill(norm_lang) and norm_lang not in skills:
                skills.append(norm_lang)

        # 2. Extract technical skills and difficulty cues from labels
        labels_lower = [lbl.lower() for lbl in issue.labels]
        for label in labels_lower:
            # Check difficulty cues from workflow labels (do NOT add them as skills)
            if any(term in label for term in ("good first", "beginner", "easy", "starter")):
                difficulty = "beginner"
            elif any(term in label for term in ("performance", "benchmark", "kernel", "internals")):
                difficulty = "advanced"

            # Only add to skills if the label is an actual technical skill and NOT a workflow label
            if not is_non_technical_label(label) and is_technical_skill(label):
                norm_lbl = normalize_skill(label)
                if norm_lbl and norm_lbl not in skills:
                    skills.append(norm_lbl)

        # 3. Simple title keyword scan for technical terms
        title_lower = issue.title.lower()
        if "test" in title_lower or "pytest" in title_lower:
            if "Testing" not in skills:
                skills.append("Testing")

        return filter_technical_skills(normalize_skill_list(skills)), difficulty

    def match_issue(
        self,
        issue: IssueItem,
        profile: DeveloperSkillProfile,
        analysis: Optional[IssueAIAnalysis] = None,
        repo_languages: Optional[Dict[str, int]] = None,
    ) -> IssueRecommendationItem:
        """
        Calculates transparent skill match details between a single issue and developer profile.
        Preserves the clear distinction between:
          a) repository-language / profile match
          b) issue-requirement match
          c) learning opportunity
        """
        repo_languages = repo_languages or {}
        normalized_profile = normalize_profile(profile)

        # Developer's total known skills pool
        dev_skills_set: Set[str] = set()
        for cat in (
            normalized_profile.programming_languages,
            normalized_profile.frameworks,
            normalized_profile.tools,
            normalized_profile.domains,
            normalized_profile.interests,
        ):
            for s in cat:
                dev_skills_set.add(s.lower())

        # Determine required skills and difficulty
        if analysis:
            # Strictly filter out non-technical labels (like enhancement, bug) from requirements
            raw_reqs = analysis.required_skills or []
            required_skills = filter_technical_skills(normalize_skill_list(raw_reqs))
            difficulty = analysis.difficulty or "unknown"
            diff_rationale = analysis.difficulty_rationale
            candidate_files = analysis.candidate_files or []
        else:
            required_skills, difficulty = self._extract_skills_from_issue_heuristic(issue, repo_languages)
            diff_rationale = f"Heuristic estimate based on issue labels ({', '.join(issue.labels) if issue.labels else 'none'}) and repository languages."
            candidate_files = []

        # Find matched skills (split into requirement matches vs repository language matches)
        matched_required_skills: List[str] = []
        matched_repo_skills: List[str] = []
        matched_skills: List[str] = []
        missing_skills: List[str] = []
        match_reasons: List[str] = []
        learning_opportunities: List[str] = []

        # 1. Check direct required skills overlap (Issue-Requirement Match)
        for req_skill in required_skills:
            if req_skill.lower() in dev_skills_set:
                matched_required_skills.append(req_skill)
                matched_skills.append(req_skill)
                match_reasons.append(f"Issue requires {req_skill} knowledge, which matches your skill profile.")
            else:
                missing_skills.append(req_skill)
                learning_opportunities.append(f"Working on this issue provides an opportunity to gain experience with {req_skill}.")

        # 2. Check candidate files extensions against developer programming languages
        dev_langs_lower = {l.lower() for l in normalized_profile.programming_languages}
        files_matched = False
        for cf in candidate_files:
            for ext, skill_name in EXTENSION_TO_SKILL.items():
                if cf.path.lower().endswith(ext):
                    if skill_name.lower() in dev_langs_lower:
                        if not files_matched:
                            match_reasons.append(f"Candidate file '{cf.path}' matches your {skill_name} programming language skills.")
                            files_matched = True
                        if skill_name not in matched_skills:
                            matched_skills.append(skill_name)
                    break

        # 3. Check repository languages match (Repository-Language / Profile Match)
        for r_lang in repo_languages.keys():
            norm_r_lang = normalize_skill(r_lang)
            if norm_r_lang and norm_r_lang.lower() in dev_langs_lower:
                if norm_r_lang not in matched_repo_skills:
                    matched_repo_skills.append(norm_r_lang)
                if norm_r_lang not in matched_skills:
                    matched_skills.append(norm_r_lang)

        # 4. Check domain / interest match with issue labels or areas
        labels_lower = {lbl.lower() for lbl in issue.labels}
        for interest in normalized_profile.interests:
            if interest.lower() in labels_lower or interest.lower() in issue.title.lower():
                match_reasons.append(f"Issue topic relates to your interest in {interest}.")

        # Compute transparent match score based strictly on analyzed requirements
        total_eval_skills = len(required_skills)
        if total_eval_skills > 0:
            matched_req_count = len(matched_required_skills)
            base_score = matched_req_count / float(total_eval_skills)

            # Bonus for candidate files alignment if not already 1.0 and some base match exists
            if files_matched and base_score > 0.0 and base_score < 1.0:
                base_score = min(1.0, base_score + 0.1)

            score = round(max(0.0, min(1.0, base_score)), 2)

            if score == 0.0:
                if matched_repo_skills:
                    match_reasons.insert(
                        0,
                        f"Repository primary language ({', '.join(matched_repo_skills)}) matches your profile. "
                        f"However, specific issue requirements ({', '.join(missing_skills)}) represent a learning opportunity."
                    )
                else:
                    match_reasons.append("No direct skill overlap detected between your profile and this issue's requirements.")
            elif matched_repo_skills:
                match_reasons.append(f"Repository primary language ({', '.join(matched_repo_skills)}) also matches your declared stack.")
        elif len(matched_skills) > 0:
            # Heuristic match when no required skills specified
            score = 0.5
            match_reasons.append("Moderate match based on repository language and topic alignment.")
        else:
            score = 0.0
            if not match_reasons:
                match_reasons.append("No direct skill overlap detected between your profile and this issue's requirements.")

        # Determine presentation label (strictly avoids 'best', 'winner', 'easiest')
        if score >= 0.75:
            match_label = "Highest skill-match score"
        elif score >= 0.5:
            match_label = "Strong skill overlap"
        elif score > 0.0:
            match_label = "Moderate skill match"
        elif matched_repo_skills:
            match_label = "Repo stack match • Learning opportunity"
        else:
            match_label = "Learning opportunity"

        skill_match_result = SkillMatchResult(
            score=score,
            matched_skills=normalize_skill_list(matched_skills),
            matched_required_skills=normalize_skill_list(matched_required_skills),
            matched_repo_skills=normalize_skill_list(matched_repo_skills),
            missing_skills=normalize_skill_list(missing_skills),
            match_reasons=match_reasons,
            learning_opportunities=learning_opportunities,
        )

        return IssueRecommendationItem(
            issue=issue,
            skill_match=skill_match_result,
            difficulty=difficulty,
            difficulty_rationale=diff_rationale,
            analysis=analysis,
            match_label=match_label,
        )

    async def get_recommendations_for_repository(
        self,
        owner: str,
        repo: str,
        profile: Optional[DeveloperSkillProfile] = None,
        branch: Optional[str] = None,
        issue_numbers: Optional[List[int]] = None,
    ) -> IssueRecommendationResponse:
        """
        Evaluates repository issues against the developer profile, produces personalized recommendations,
        and sorts them deterministically by match score descending, then issue number ascending.
        """
        # Resolve active profile
        active_profile = profile if profile is not None else profile_service.get_profile()
        normalized_profile = normalize_profile(active_profile)

        # Fetch open repository issues
        raw_issues = await github_service.fetch_issues(owner, repo, state="open")
        repo_languages = await github_service.fetch_languages(owner, repo)

        # Convert to typed IssueItem models (filtering PRs is already done by github_service)
        issue_items = [IssueItem(**item) for item in raw_issues]

        if issue_numbers:
            target_nums = set(issue_numbers)
            issue_items = [item for item in issue_items if item.number in target_nums]

        recommendations: List[IssueRecommendationItem] = []

        for item in issue_items:
            # Check if we have cached AI analysis for this issue
            cached_resp = self.get_cached_analysis(owner, repo, item.number)
            analysis_data = cached_resp.analysis if cached_resp else None

            rec = self.match_issue(
                issue=item,
                profile=normalized_profile,
                analysis=analysis_data,
                repo_languages=repo_languages,
            )
            recommendations.append(rec)

        # Deterministic sorting: match_score descending, then issue.number ascending
        recommendations.sort(
            key=lambda r: (-r.skill_match.score, r.issue.number)
        )

        return IssueRecommendationResponse(
            repository=f"{owner}/{repo}",
            recommendations=recommendations,
            total_issues_considered=len(issue_items),
            profile_used=normalized_profile,
            explanation=(
                "Recommendations are ranked by estimated skill match based on the provided profile. "
                "AI Difficulty Estimates describe intrinsic complexity and are evaluated independently of skill match."
            ),
        )


skill_matching_service = SkillMatchingService()
