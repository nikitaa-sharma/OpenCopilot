"""
Pydantic schemas for Phase 10: Developer Skill Profile & Personalized Recommendations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.repository import IssueAIAnalysis, IssueItem


class DeveloperSkillProfile(BaseModel):
    """
    Lightweight, flexible developer skill profile.
    Used to personalize repository issue recommendations.
    """
    programming_languages: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Programming languages (e.g., Python, JavaScript, TypeScript, Go)",
    )
    frameworks: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Frameworks and libraries (e.g., FastAPI, React, Django, Next.js)",
    )
    tools: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Development tools, databases, or infrastructure (e.g., Git, Docker, PostgreSQL, Redis)",
    )
    domains: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Application domains or focus areas (e.g., AI, Web Development, Cloud, CLI)",
    )
    experience_level: Optional[str] = Field(
        default="beginner",
        max_length=50,
        description="Developer experience level: beginner, intermediate, or advanced",
    )
    interests: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Topics or areas of personal interest (e.g., open source, performance, documentation)",
    )

    @field_validator("programming_languages", "frameworks", "tools", "domains", "interests")
    @classmethod
    def validate_item_lengths(cls, items: List[str]) -> List[str]:
        cleaned = []
        for item in items:
            s = item.strip()
            if len(s) > 100:
                raise ValueError(f"Skill entry exceeds maximum allowed length of 100 characters: '{s[:30]}...'")
            if s:
                cleaned.append(s)
        return cleaned



class SkillMatchResult(BaseModel):
    """
    Transparent breakdown of a skill match calculation.
    Separates matched skills, skill gaps, and learning opportunities.
    """
    score: float = Field(
        ...,
        description="Estimated skill match score between 0.0 and 1.0 (0% to 100%)",
        ge=0.0,
        le=1.0,
    )
    matched_skills: List[str] = Field(
        default_factory=list,
        description="All required or relevant skills that match the developer's profile",
    )
    matched_required_skills: List[str] = Field(
        default_factory=list,
        description="Issue-specific required skills that overlap with the developer profile",
    )
    matched_repo_skills: List[str] = Field(
        default_factory=list,
        description="Repository languages or technologies that overlap with the developer profile",
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Required technical skills identified for the issue that are not in the developer's profile",
    )
    match_reasons: List[str] = Field(
        default_factory=list,
        description="Transparent explanations of why this issue matches the developer profile",
    )
    learning_opportunities: List[str] = Field(
        default_factory=list,
        description="Identified skills or technologies that this issue offers an opportunity to learn",
    )


class IssueRecommendationItem(BaseModel):
    """
    A repository issue paired with personalized skill matching and difficulty estimate.
    """
    issue: IssueItem = Field(..., description="The GitHub issue")
    skill_match: SkillMatchResult = Field(..., description="Calculated skill match details")
    difficulty: str = Field(
        default="unknown",
        description="Intrinsic AI difficulty estimate: beginner, intermediate, advanced, or unknown",
    )
    difficulty_rationale: Optional[str] = Field(
        None,
        description="Rationale for the assigned difficulty estimate",
    )
    analysis: Optional[IssueAIAnalysis] = Field(
        None,
        description="Full grounded AI analysis if issue has been analyzed",
    )
    match_label: str = Field(
        default="Recommended based on your profile",
        description="Human-readable match indicator (e.g., 'Highest skill-match score', 'Strong skill overlap')",
    )


class IssueRecommendationRequest(BaseModel):
    """
    Request payload for personalized repository issue recommendations.
    """
    owner: str = Field(..., max_length=100, description="GitHub repository owner", examples=["pallets"])
    repo: str = Field(..., max_length=100, description="GitHub repository name", examples=["flask"])
    branch: Optional[str] = Field(None, max_length=100, description="Optional branch or commit ref")
    profile: Optional[DeveloperSkillProfile] = Field(
        None,
        description="Optional developer profile override; if omitted, the current active profile is used",
    )
    issue_numbers: Optional[List[int]] = Field(
        None,
        max_length=50,
        description="Optional filter for specific issue numbers to evaluate and rank",
    )



class IssueRecommendationResponse(BaseModel):
    """
    Structured response containing ranked issue recommendations.
    """
    repository: str = Field(..., description="'owner/repo' format")
    recommendations: List[IssueRecommendationItem] = Field(
        default_factory=list,
        description="Issues sorted by match score descending, then issue number ascending",
    )
    total_issues_considered: int = Field(0, description="Total number of open issues evaluated")
    profile_used: Optional[DeveloperSkillProfile] = Field(
        None,
        description="The normalized developer skill profile used for this recommendation calculation",
    )
    explanation: str = Field(
        default="Recommendations ordered by estimated skill match based on the profile provided.",
        description="Transparency note on recommendation criteria and scoring",
    )
