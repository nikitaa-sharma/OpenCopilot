from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RepositoryAnalyzeRequest(BaseModel):
    """Request payload for repository analysis."""
    url: str = Field(
        ...,
        max_length=500,
        description="Public GitHub repository URL (e.g. https://github.com/owner/repo or github.com/owner/repo)",
        examples=["https://github.com/fastapi/fastapi", "github.com/pallets/flask"],
    )


class LicenseInfo(BaseModel):
    """License metadata for the repository."""
    key: Optional[str] = None
    name: Optional[str] = None
    spdx_id: Optional[str] = None
    url: Optional[str] = None


class RepositoryInfo(BaseModel):
    """Core GitHub repository metadata."""
    id: Optional[int] = None
    owner: str
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: Optional[str] = None
    default_branch: str = "main"
    visibility: str = "public"
    language: Optional[str] = None
    license: Optional[LicenseInfo] = None
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues_count: int = 0  # GitHub includes both issues and PRs in this counter
    topics: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pushed_at: Optional[str] = None


class ReadmeInfo(BaseModel):
    """Repository README information and decoded content."""
    name: str = "README.md"
    content: Optional[str] = None
    html_url: Optional[str] = None
    size: int = 0


class IssueItem(BaseModel):
    """Individual GitHub issue (pull requests excluded)."""
    id: Optional[int] = None
    number: int
    title: str
    body: Optional[str] = ""
    state: str = "open"
    html_url: str
    labels: List[str] = Field(default_factory=list)
    user: Optional[str] = None
    comments_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AnalysisSource(BaseModel):
    """Origin details of analyzed repository."""
    provider: str = "github"
    owner: str
    repository: str


class RepositoryAnalysisResponse(BaseModel):
    """Structured response returned by the repository analysis endpoint."""
    repository: RepositoryInfo
    languages: Dict[str, int] = Field(
        default_factory=dict,
        description="Dictionary mapping programming language names to byte counts"
    )
    readme: Optional[ReadmeInfo] = None
    issues: List[IssueItem] = Field(
        default_factory=list,
        description="Filtered open issues with pull requests strictly excluded"
    )
    source: AnalysisSource


# ==============================================================================
# Repository Tree & Ingestion Schemas (Phase 4)
# ==============================================================================

class TreeItem(BaseModel):
    """Normalized repository tree item (file or directory)."""
    path: str
    type: str = Field(..., description="'file' or 'directory'")
    size: Optional[int] = Field(None, description="Size in bytes, present for files")
    sha: Optional[str] = None
    category: Optional[str] = Field(None, description="Classification (e.g. source, test, documentation, configuration)")
    language: Optional[str] = Field(None, description="Detected programming language")


class RepositoryTreeResponse(BaseModel):
    """Response payload for repository tree hierarchy."""
    repository: str = Field(..., description="'owner/repo' format")
    branch: str = Field(..., description="Branch or commit ref")
    truncated: bool = Field(False, description="True if git tree exceeded GitHub's maximum items limit")
    total_items: int = Field(0, description="Total count of items in the tree")
    tree: List[TreeItem] = Field(default_factory=list)


class FileContentResponse(BaseModel):
    """Structured response for an individual repository file."""
    path: str
    name: str
    language: Optional[str] = None
    category: str = "source"
    size: int = 0
    sha: Optional[str] = None
    content: Optional[str] = None
    encoding: str = "utf-8"
    is_binary: bool = False
    skip_reason: Optional[str] = None


class IngestionStatistics(BaseModel):
    """Metrics recorded during repository ingestion."""
    total_tree_items: int = 0
    directories: int = 0
    files: int = 0
    selected_files: int = 0
    skipped_files: int = 0
    total_code_bytes: int = 0


class RepositoryRef(BaseModel):
    """Reference metadata for ingested repository."""
    owner: str
    name: str
    branch: str


class RepositoryIngestionRequest(BaseModel):
    """Request payload for full repository ingestion."""
    url: str = Field(
        ...,
        max_length=500,
        description="Public GitHub repository URL",
        examples=["https://github.com/pallets/flask", "psf/requests"],
    )
    branch: Optional[str] = Field(None, max_length=100, description="Optional branch or commit ref to ingest")


class RepositoryIngestionResponse(BaseModel):
    """Structured response returned by the repository ingestion endpoint."""
    repository: RepositoryRef
    statistics: IngestionStatistics
    files: List[FileContentResponse]


# ==============================================================================
# AI Repository Analysis Schemas (Phase 5)
# ==============================================================================

class TechnologyItem(BaseModel):
    """Technology identified with context grounding."""
    name: str
    category: str = "library"
    evidence: str = Field(..., description="File path or configuration indicating this technology")


class DirectoryExplanation(BaseModel):
    """Architectural explanation of a directory."""
    path: str
    explanation: str
    evidence: Optional[str] = None


class FileExplanation(BaseModel):
    """Significance explanation of an important file."""
    path: str
    reason: str
    evidence: Optional[str] = None


class EntryPoint(BaseModel):
    """Identified application entrypoint."""
    path: str
    description: str
    confidence: str = Field("medium", description="'high', 'medium', 'low', or 'unknown'")


class TestingOverview(BaseModel):
    """Testing suite overview and structure."""
    __test__ = False
    framework: str = "None identified"
    structure: str = "No test directory identified"
    evidence: Optional[str] = None



class RepositoryAIAnalysis(BaseModel):
    """Validated structured AI analysis of a software repository."""
    summary: str = Field(..., description="Concise explanation of what the repository does")
    purpose: str = Field(..., description="Problem the project appears to solve")
    architecture: str = Field(..., description="Overview of major components and relationships")
    technology_stack: List[TechnologyItem] = Field(default_factory=list)
    important_directories: List[DirectoryExplanation] = Field(default_factory=list)
    important_files: List[FileExplanation] = Field(default_factory=list)
    entry_points: List[EntryPoint] = Field(default_factory=list)
    testing: TestingOverview = Field(default_factory=TestingOverview)
    beginner_explanation: str = Field(..., description="Plain-English guide for new contributors")
    confidence_assessment: str = Field(..., description="Observed facts vs inferences")


class ContextStats(BaseModel):
    """Statistics about context prepared for AI analysis."""
    files_included: int = 0
    total_context_chars: int = 0


class RepositoryAIAnalysisResponse(BaseModel):
    """Complete response returned by the AI repository analysis endpoint."""
    repository: RepositoryRef
    analysis: RepositoryAIAnalysis
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    context_stats: Optional[ContextStats] = None


# ==============================================================================
# AI Issue Analysis & Recommendation Schemas (Phase 6)
# ==============================================================================

class CandidateFile(BaseModel):
    """Candidate file relevant to issue investigation."""
    path: str = Field(..., description="Path to candidate file in repository")
    reason: str = Field(..., description="Why this file may be relevant to the issue")
    confidence: str = Field("possible", description="'likely', 'possible', or 'speculative'")


class IssueAIAnalysis(BaseModel):
    """Grounded AI analysis of a specific GitHub issue."""
    issue_type: str = Field(..., description="Classification: bug, feature, documentation, refactor, test, or chore")
    difficulty: str = Field(..., description="AI estimated difficulty: beginner, intermediate, advanced, or unknown")
    difficulty_rationale: str = Field(..., description="Explanation of why this difficulty was assigned")
    required_skills: List[str] = Field(default_factory=list, description="Skills or technologies needed")
    skills_rationale: str = Field(..., description="Why these skills are relevant to the issue")
    candidate_files: List[CandidateFile] = Field(
        default_factory=list,
        description="Candidate files requiring verification"
    )
    affected_areas: List[str] = Field(default_factory=list, description="Components, modules, or subsystems affected")
    investigation_steps: List[str] = Field(default_factory=list, description="Step-by-step investigation approach")
    prerequisites: str = Field(..., description="Environment, domain knowledge, or tooling prerequisites")
    ai_explanation: str = Field(..., description="Plain-language explanation of what the issue is reporting/requesting")
    observed_evidence: List[str] = Field(
        default_factory=list,
        description="Direct observations from issue description, labels, or verified repository files"
    )
    inferences: List[str] = Field(
        default_factory=list,
        description="AI deductions made based on the observed evidence"
    )
    unknowns: List[str] = Field(
        default_factory=list,
        description="Unresolved questions or details missing from the issue description"
    )
    confidence: str = Field("medium", description="Overall confidence assessment: 'high', 'medium', or 'low'")


class IssueAIAnalysisRequest(BaseModel):
    """Request payload for AI issue analysis."""
    url: str = Field(
        ...,
        description="Public GitHub repository URL (e.g. https://github.com/owner/repo)",
        examples=["https://github.com/pallets/flask"],
    )
    issue_number: int = Field(..., description="GitHub issue number to analyze", ge=1)
    branch: Optional[str] = Field(None, description="Optional branch or commit ref to inspect for file tree")


class IssueAIAnalysisResponse(BaseModel):
    """Structured response returned by the AI issue analysis endpoint."""
    repository: RepositoryRef
    issue_number: int
    issue_title: str
    issue_url: str
    analysis: IssueAIAnalysis
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    context_stats: Optional[ContextStats] = None


# ==============================================================================
# RAG Pipeline Schemas (Phase 7)
# ==============================================================================

class RAGRetrieveRequest(BaseModel):
    """Request payload for RAG keyword retrieval."""
    repository_url: str = Field(
        ...,
        max_length=500,
        description="Public GitHub repository URL",
        examples=["https://github.com/pallets/flask"],
    )
    query: str = Field(
        ...,
        max_length=1000,
        description="Natural language or code question to search for",
        examples=["Where is the Flask application class defined?"],
    )
    top_k: Optional[int] = Field(
        None,
        description="Maximum number of results to return (default from config: RAG_TOP_K)",
        ge=1,
        le=20,
    )
    branch: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional branch or commit ref (defaults to repository default branch)",
    )


class RAGChunkResult(BaseModel):
    """A retrieved chunk with scoring metadata."""
    chunk_id: str = Field(..., description="Deterministic chunk identifier")
    file_path: str = Field(..., description="Source file path within repository")
    language: Optional[str] = Field(None, description="Programming language")
    category: str = Field(..., description="File category")
    start_line: int = Field(..., description="1-based start line in source file")
    end_line: int = Field(..., description="1-based end line in source file")
    content: str = Field(..., description="Chunk text content")
    score: float = Field(..., description="Relevance score")
    matched_terms: List[str] = Field(default_factory=list, description="Query terms that matched")
    retrieval_reason: str = Field(..., description="Why this chunk was selected")


class RAGRetrievalStatistics(BaseModel):
    """Statistics about a RAG retrieval operation."""
    documents_loaded: int = 0
    documents_skipped: int = 0
    chunks_created: int = 0
    chunks_searched: int = 0
    results_returned: int = 0


class RAGRetrievalResponse(BaseModel):
    """Response from the RAG retrieval endpoint."""
    repository: str = Field(..., description="'owner/repo' format")
    query: str = Field(..., description="Original query")
    retrieval_mode: str = Field(default="keyword", description="Retrieval mode used: keyword, vector, or keyword_fallback")
    results: List[RAGChunkResult] = Field(default_factory=list)
    statistics: RAGRetrievalStatistics = Field(default_factory=RAGRetrievalStatistics)


class RAGContextResponse(BaseModel):
    """Response from the RAG context endpoint."""
    repository: str = Field(..., description="'owner/repo' format")
    query: str = Field(..., description="Original query")
    retrieval_mode: str = Field(default="keyword", description="Retrieval mode used: keyword, vector, or keyword_fallback")
    context: str = Field(..., description="Formatted context string ready for LLM prompting")
    retrieved_chunks: List[RAGChunkResult] = Field(default_factory=list)
    statistics: RAGRetrievalStatistics = Field(default_factory=RAGRetrievalStatistics)


# ==============================================================================
# Phase 8: Local Embeddings & Vector Semantic Search Schemas
# ==============================================================================

class RAGIndexRequest(BaseModel):
    """Request payload for indexing a repository into pgvector with local embeddings."""
    repository_url: str = Field(
        ...,
        description="Public GitHub repository URL",
        examples=["https://github.com/pallets/flask"],
    )
    branch: Optional[str] = Field(
        None,
        description="Optional branch or commit ref (defaults to repository default branch)",
    )


class RAGIndexResponse(BaseModel):
    """Response payload returned after repository embedding indexing."""
    repository: str = Field(..., description="'owner/repo' format")
    documents_processed: int = Field(..., description="Number of repository documents processed")
    chunks_created: int = Field(..., description="Total chunks created from documents")
    chunks_embedded: int = Field(..., description="Chunks newly embedded using local model")
    chunks_reused: int = Field(..., description="Chunks reused via SHA-256 content hash match")
    chunks_updated: int = Field(..., description="Chunks updated in database")
    embedding_dimension: int = Field(..., description="Dimension of embedding vectors (e.g. 384)")
    elapsed_time_seconds: Optional[float] = Field(None, description="Indexing duration in seconds")


class RAGVectorSearchRequest(BaseModel):
    """Request payload for pgvector semantic vector search."""
    repository_url: str = Field(
        ...,
        max_length=500,
        description="Public GitHub repository URL",
        examples=["https://github.com/pallets/flask"],
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language or code query to search for",
        examples=["Where is the Flask application class defined?"],
    )
    top_k: Optional[int] = Field(
        None,
        description="Maximum number of chunks to return (default from config: RAG_TOP_K)",
        ge=1,
        le=20,
    )
    branch: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional branch or commit ref",
    )


class VectorChunkResult(BaseModel):
    """Individual chunk result returned from semantic vector search."""
    file_path: str = Field(..., description="Source file path within repository")
    language: Optional[str] = Field(None, description="Programming language")
    category: str = Field(..., description="File category")
    start_line: int = Field(..., description="1-based start line")
    end_line: int = Field(..., description="1-based end line")
    content: str = Field(..., description="Chunk text content")
    similarity_score: float = Field(..., description="Cosine similarity score (higher = more relevant)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible chunk metadata")


class RAGVectorSearchStatistics(BaseModel):
    """Statistics for a vector search query."""
    total_indexed_chunks: Optional[int] = None
    results_returned: int = 0


class RAGVectorSearchResponse(BaseModel):
    """Response returned from semantic vector search."""
    repository: str = Field(..., description="'owner/repo' format")
    query: str = Field(..., description="Original search query")
    retrieval_mode: str = Field(default="vector", description="Mode: 'vector' or 'keyword_fallback'")
    results: List[VectorChunkResult] = Field(default_factory=list)
    statistics: RAGVectorSearchStatistics = Field(default_factory=RAGVectorSearchStatistics)


# ==============================================================================
# Phase 9: Repository-Aware AI Chat Schemas
# ==============================================================================

class RepositoryChatRequest(BaseModel):
    """Request payload for repository-grounded AI chat."""
    owner: str = Field(..., max_length=100, description="GitHub repository owner", examples=["pallets"])
    repo: str = Field(..., max_length=100, description="GitHub repository name", examples=["flask"])
    question: str = Field(..., max_length=2000, description="Natural language question about the repository", examples=["How does Flask handle incoming HTTP requests?"])
    branch: Optional[str] = Field(None, max_length=100, description="Optional branch or commit ref to inspect")
    top_k: Optional[int] = Field(None, description="Maximum number of context chunks to retrieve", ge=1, le=20)


class ChatSourceItem(BaseModel):
    """A verified repository chunk backing an AI answer."""
    path: str = Field(..., description="File path within the repository")
    chunk_id: Optional[str] = Field(None, description="Deterministic chunk identifier")
    start_line: Optional[int] = Field(None, description="1-based start line if available")
    end_line: Optional[int] = Field(None, description="1-based end line if available")
    category: str = Field("source", description="File category (e.g. source, test, doc)")
    score: Optional[float] = Field(None, description="Retrieval similarity or relevance score")
    retrieval_reason: Optional[str] = Field(None, description="Why this chunk was retrieved or cited")


class RepositoryChatResponse(BaseModel):
    """Response payload for repository AI chat with verified evidence."""
    answer: str = Field(..., description="AI generated answer grounded in repository context")
    sources: List[ChatSourceItem] = Field(default_factory=list, description="Verified repository source chunks supporting the answer")
    retrieval_mode: str = Field(..., description="Retrieval mode used: 'vector', 'keyword', 'keyword_fallback', or 'none'")
    retrieved_chunks_count: int = Field(0, description="Number of repository chunks retrieved for context")
    uncertainties: List[str] = Field(default_factory=list, description="Model-identified uncertainties, caveats, or missing context")

