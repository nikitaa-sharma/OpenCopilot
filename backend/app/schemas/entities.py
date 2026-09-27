"""
Pydantic schemas for future OpenSource Copilot API endpoints.
Provides type validation, serialization, and OpenAPI documentation contracts.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class UserSkillBase(BaseModel):
    name: str
    proficiency_level: str = "intermediate"


class UserSkillResponse(UserSkillBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    username: str
    github_id: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    skills: List[UserSkillResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RepositoryAnalyzeRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public GitHub repository URL")


class RepositorySummaryResponse(BaseModel):
    id: int
    owner: str
    name: str
    full_name: str
    url: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    stars_count: int = 0
    forks_count: int = 0
    architecture_summary: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class IssueAnalysisResponse(BaseModel):
    difficulty_score: str
    required_skills: List[str] = []
    summary: str
    affected_components: List[str] = []


class IssueSummaryResponse(BaseModel):
    id: int
    github_issue_id: int
    issue_number: int
    title: str
    state: str
    labels: List[str] = []
    analysis: Optional[IssueAnalysisResponse] = None
    model_config = ConfigDict(from_attributes=True)


class ContributionGuideResponse(BaseModel):
    issue_id: int
    steps: List[str]
    recommended_files: List[str] = []
    testing_tips: Optional[str] = None


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="User question about the repository")


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    context_sources: List[str] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
