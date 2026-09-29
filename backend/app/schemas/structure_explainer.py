"""
Pydantic schemas for the 'Repository Structure Explainer' / 'Understand This Repository' feature.
Provides structured, beginner-friendly explanations of repository purpose, architecture,
directories, important files, execution flows, and onboarding guides.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryRef, ContextStats


class RepositoryOverviewDetail(BaseModel):
    """High-level repository overview and classification."""
    what_it_does: str = Field(..., description="Clear explanation of what the repository does")
    main_purpose: str = Field(..., description="Primary problem the project solves and its core target audience")
    primary_technologies: List[str] = Field(default_factory=list, description="Top detected languages and core frameworks")
    application_type: str = Field(..., description="Main application or library type (e.g., Web Framework, CLI Tool, Full-stack Web App, Backend API)")
    entry_points: List[str] = Field(default_factory=list, description="Primary execution entry point files or CLI commands")
    high_level_architecture: str = Field(..., description="Summary of the high-level structural design")


class DirectoryExplanationDetail(BaseModel):
    """Detailed architectural explanation for an important directory."""
    name: str = Field(..., description="Directory path/name (e.g., 'src/', 'tests/', 'api/')")
    purpose: str = Field(..., description="Main purpose of this directory")
    contains: str = Field(..., description="Description of what files and logic live in this directory")
    important_subdirectories: List[str] = Field(default_factory=list, description="Key nested subdirectories")
    relationship: str = Field(..., description="How this directory relates to other parts of the project")
    evidence: Optional[str] = Field(None, description="Observed files, manifests, or patterns supporting this explanation")
    confidence: str = Field("high", description="'high', 'medium', 'low', or 'uncertain'")


class ImportantFileDetail(BaseModel):
    """Explanation of an architecturally significant file."""
    path: str = Field(..., description="Relative file path in repository")
    category: str = Field(..., description="Category: manifest, config, entry_point, routing, database, api, test, devops, documentation, or core_logic")
    description: str = Field(..., description="Plain-English explanation of what this important file does")
    evidence: Optional[str] = Field(None, description="Observed exports, definitions, or configuration")


class ArchitectureExplanation(BaseModel):
    """Beginner-friendly architecture explanation with Mermaid diagram."""
    overview: str = Field(..., description="Narrative overview of how components connect")
    pattern: str = Field("Modular", description="Architectural pattern (e.g. Client-Server, Layered MVC, Microframework, Event-Driven)")
    layers: List[str] = Field(default_factory=list, description="Key logical layers (e.g., Presentation, API, Services, Storage)")
    diagram_mermaid: str = Field(..., description="Valid GitHub-compatible Mermaid flowchart TD diagram")


class RepositoryFlow(BaseModel):
    """Step-by-step execution and data flow walkthrough."""
    execution_start: str = Field(..., description="Where and how execution starts")
    component_communication: str = Field(..., description="How major components interact and communicate")
    data_entry: str = Field(..., description="Where and how external data/requests enter the system")
    data_processing: str = Field(..., description="How data is transformed, validated, and processed")
    data_storage: str = Field(..., description="Where and how data or state is stored/cached (if applicable)")
    result_delivery: str = Field(..., description="How the final response, output, or UI reaches the user")


class TechnologyMap(BaseModel):
    """Categorized mapping of technologies detected in the repository."""
    frontend: List[str] = Field(default_factory=list)
    backend: List[str] = Field(default_factory=list)
    database: List[str] = Field(default_factory=list)
    apis: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    testing: List[str] = Field(default_factory=list)
    devops: List[str] = Field(default_factory=list)
    build_tools: List[str] = Field(default_factory=list)


class WhereToStartStep(BaseModel):
    """Numbered step in beginner-oriented codebase exploration order."""
    step_number: int = Field(..., description="Step index (1 to N)")
    title: str = Field(..., description="Actionable title for this reading step")
    target_path: Optional[str] = Field(None, description="Specific file or directory to inspect")
    guidance: str = Field(..., description="What to look for and understand in this step")
    why: str = Field(..., description="Why this should be read at this stage")


class StructureExplainerAnalysis(BaseModel):
    """Comprehensive grounded analysis for understanding repository structure."""
    overview: RepositoryOverviewDetail
    directories: List[DirectoryExplanationDetail] = Field(default_factory=list)
    important_files: List[ImportantFileDetail] = Field(default_factory=list)
    architecture: ArchitectureExplanation
    flow: RepositoryFlow
    technology_map: TechnologyMap
    where_to_start: List[WhereToStartStep] = Field(default_factory=list)
    confidence_evidence: str = Field(..., description="Evidence breakdown and confidence assessment")


class StructureExplainerRequest(BaseModel):
    """Request payload to analyze repository structure."""
    url: str = Field(..., description="Public GitHub repository URL")
    branch: Optional[str] = Field(None, description="Optional branch or commit ref")


class StructureExplainerResponse(BaseModel):
    """API response for Repository Structure Explainer."""
    repository: RepositoryRef
    explainer: StructureExplainerAnalysis
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    context_stats: Optional[ContextStats] = None
