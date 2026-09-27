"""
Domain models for AI Contribution Guide (Phase 11).
Structured schemas representing actionable, repository-grounded guidance for a specific GitHub issue.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.profile import DeveloperSkillProfile
from app.schemas.repository import IssueItem


class ContributionGuideUnderstanding(BaseModel):
    """Plain-language breakdown of what the issue is reporting or requesting."""
    summary: str = Field(..., description="High-level summary of the issue")
    problem: str = Field(..., description="Root cause, bug symptoms, or missing capability")
    expected_outcome: str = Field(..., description="How the repository should behave once resolved")


class ContributionGuideFile(BaseModel):
    """A repository file identified as relevant to resolving this issue."""
    path: str = Field(..., description="Verified file path within the repository")
    role: str = Field(default="source", description="Role: 'source', 'test', 'config', or 'documentation'")
    reason: str = Field(..., description="Why this file needs inspection or modification")


class ContributionGuideStep(BaseModel):
    """A single actionable step in the implementation plan."""
    step: int = Field(..., description="1-based step order")
    title: str = Field(..., description="Short title of the step")
    description: str = Field(..., description="Detailed instructions for this step")
    files: List[str] = Field(default_factory=list, description="Files associated with this step")


class ContributionGuideCodeArea(BaseModel):
    """Specific function, class, or module area within a file to inspect."""
    path: str = Field(..., description="Verified repository file path")
    area: str = Field(..., description="Function, class, or section name")
    guidance: str = Field(..., description="Maintainer guidance on what to check or change")


class ContributionGuideTestItem(BaseModel):
    """Test suite or test case recommendation."""
    type: str = Field(default="unit", description="'unit', 'integration', 'regression', or 'manual'")
    description: str = Field(..., description="What behavior or edge case should be verified")
    files: List[str] = Field(default_factory=list, description="Target test files to run or update")


class ContributionGuideEvidence(BaseModel):
    """Verified evidence chunk backing recommendations in the guide."""
    path: str = Field(..., description="Source file path within repository")
    chunk_id: Optional[str] = Field(None, description="Deterministic chunk identifier")
    start_line: Optional[int] = Field(None, description="1-based start line")
    end_line: Optional[int] = Field(None, description="1-based end line")
    category: str = Field("source", description="File category (e.g. source, test, doc)")
    score: Optional[float] = Field(None, description="Retrieval similarity or relevance score")
    reason: Optional[str] = Field(None, description="Why this chunk was retrieved or cited")


class ContributionGuide(BaseModel):
    """Complete grounded AI contribution guide."""
    issue_understanding: ContributionGuideUnderstanding = Field(..., description="Issue overview and problem statement")
    prerequisites: List[str] = Field(default_factory=list, description="Environment, tools, or domain prerequisites")
    relevant_files: List[ContributionGuideFile] = Field(default_factory=list, description="Validated files to inspect")
    implementation_plan: List[ContributionGuideStep] = Field(default_factory=list, description="Sequential implementation steps")
    code_areas: List[ContributionGuideCodeArea] = Field(default_factory=list, description="Specific code sections to inspect")
    testing_plan: List[ContributionGuideTestItem] = Field(default_factory=list, description="Recommended tests and validation steps")
    documentation_plan: List[str] = Field(default_factory=list, description="Documentation updates needed (docstrings, guides)")
    pull_request_checklist: List[str] = Field(default_factory=list, description="Pre-flight checklist before opening a PR")
    learning_opportunities: List[str] = Field(default_factory=list, description="New skills or patterns to learn from this issue")
    uncertainties: List[str] = Field(default_factory=list, description="Missing context, ambiguities, or items requiring verification")
    evidence: List[ContributionGuideEvidence] = Field(default_factory=list, description="Verified repository source chunks backing this guide")


class ContributionGuideRequest(BaseModel):
    """Request payload for generating an AI contribution guide."""
    owner: str = Field(..., description="GitHub repository owner", examples=["pallets"])
    repo: str = Field(..., description="GitHub repository name", examples=["flask"])
    issue_number: int = Field(..., description="GitHub issue number to guide", ge=1)
    branch: Optional[str] = Field(None, description="Optional branch or commit ref")
    profile: Optional[DeveloperSkillProfile] = Field(None, description="Optional developer profile for personalized guidance")
    top_k: Optional[int] = Field(None, description="Maximum number of context chunks to retrieve", ge=1, le=20)


class ContributionGuideResponse(BaseModel):
    """Structured response returned by the contribution guide endpoint."""
    issue: IssueItem = Field(..., description="Target GitHub issue metadata")
    guide: ContributionGuide = Field(..., description="Grounded contribution guide")
    retrieval_mode: str = Field(default="vector", description="Mode: 'vector', 'keyword', or 'none'")
    sources: List[ContributionGuideEvidence] = Field(default_factory=list, description="Verified repository sources")
    uncertainties: List[str] = Field(default_factory=list, description="Caveats and unresolved items")
