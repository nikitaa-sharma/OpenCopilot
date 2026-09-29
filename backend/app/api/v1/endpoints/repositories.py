from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.repository import (
    RepositoryAnalyzeRequest,
    RepositoryAnalysisResponse,
    RepositoryTreeResponse,
    FileContentResponse,
    RepositoryIngestionRequest,
    RepositoryIngestionResponse,
    RepositoryAIAnalysisResponse,
    IssueAIAnalysisRequest,
    IssueAIAnalysisResponse,
    RAGRetrieveRequest,
    RAGRetrievalResponse,
    RAGChunkResult,
    RAGRetrievalStatistics,
    RAGContextResponse,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGVectorSearchRequest,
    RAGVectorSearchResponse,
    VectorChunkResult,
    RAGVectorSearchStatistics,
    RepositoryChatRequest,
    RepositoryChatResponse,
    ChatSourceItem,
)
from app.schemas.profile import (
    IssueRecommendationRequest,
    IssueRecommendationResponse,
)
from app.services.skill_matching_service import skill_matching_service
from app.embeddings.base import EmbeddingProviderError
from app.chat import ChatQuestion, repository_chat_service
from app.contribution import (
    ContributionGuideRequest,
    ContributionGuideResponse,
    contribution_guide_service,
)
from app.services.github_service import (
    github_service,
    InvalidGitHubURLError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubServiceError,
)
from app.services.repository_ingestion_service import repository_ingestion_service
from app.services.repository_analysis_service import (
    repository_analysis_service,
    AIAnalysisError,
    AIAnalysisValidationError,
)
from app.services.issue_analysis_service import issue_analysis_service
from app.rag.service import repository_rag_service
from app.services.llm_provider import (
    LLMProviderUnavailableError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMProviderError,
)
from app.services.llm_factory import UnsupportedLLMProviderError
from app.services.structure_explainer_service import structure_explainer_service
from app.schemas.structure_explainer import (
    StructureExplainerRequest,
    StructureExplainerResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=RepositoryAnalysisResponse,
    summary="Analyze a public GitHub repository",
    description=(
        "Validates the provided GitHub repository URL, queries the GitHub REST API "
        "to retrieve repository metadata, language breakdown, README content, and "
        "the first page of open issues (strictly excluding pull requests)."
    ),
    responses={
        200: {"description": "Repository successfully analyzed."},
        400: {"description": "Invalid or malformed GitHub repository URL."},
        404: {"description": "Repository not found or is not publicly accessible."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API unavailable or request timed out."},
        500: {"description": "Unexpected internal server error."},
    },
)
async def analyze_repository(request: RepositoryAnalyzeRequest) -> RepositoryAnalysisResponse:
    """
    Handle repository analysis request:
    1. Validates the URL structure and GitHub domain.
    2. Calls the GitHub service layer.
    3. Returns typed, structured analysis response.
    """
    try:
        data = await github_service.analyze_repository(request.url)
        return RepositoryAnalysisResponse(**data)
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found or is not publicly accessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while analyzing '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"Service error while analyzing '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error analyzing '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the repository.",
        )


@router.get(
    "/{owner}/{repo}/tree",
    response_model=RepositoryTreeResponse,
    summary="Get repository file tree hierarchy",
    description=(
        "Retrieves the recursive Git tree for the repository, returning normalized "
        "file and directory items annotated with language and classification."
    ),
    responses={
        200: {"description": "Repository tree successfully retrieved."},
        404: {"description": "Repository or branch not found."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API unavailable or request timed out."},
    },
)
async def get_repository_tree(
    owner: str,
    repo: str,
    branch: Optional[str] = Query(None, description="Branch or commit ref (default: repository default branch)"),
) -> RepositoryTreeResponse:
    """Retrieve structured repository file tree."""
    try:
        data = await repository_ingestion_service.get_repository_tree(
            owner=owner, repo=repo, branch=branch
        )
        return RepositoryTreeResponse(**data)
    except GitHubNotFoundError as exc:
        logger.info(f"Tree not found for {owner}/{repo}@{branch}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while getting tree for {owner}/{repo}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"Service error getting tree for {owner}/{repo}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error fetching tree for {owner}/{repo}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving repository tree.",
        )


@router.get(
    "/{owner}/{repo}/files/{path:path}",
    response_model=FileContentResponse,
    summary="Get individual repository file content",
    description=(
        "Retrieves and safely decodes the text content of a single repository file. "
        "Safely handles binary files, size limits, and encodings."
    ),
    responses={
        200: {"description": "File content successfully retrieved."},
        400: {"description": "Invalid file path."},
        404: {"description": "File not found in repository."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API unavailable or request timed out."},
    },
)
async def get_repository_file(
    owner: str,
    repo: str,
    path: str,
    branch: Optional[str] = Query(None, description="Branch or commit ref"),
) -> FileContentResponse:
    """Retrieve individual file content and metadata."""
    try:
        data = await repository_ingestion_service.get_file_content(
            owner=owner, repo=repo, path=path, branch=branch
        )
        return FileContentResponse(**data)
    except InvalidGitHubURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"File not found: {owner}/{repo}:{path}@{branch}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{path}' not found in repository.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while getting file {owner}/{repo}:{path}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"Service error getting file {owner}/{repo}:{path}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error fetching file {owner}/{repo}:{path}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving file content.",
        )


@router.post(
    "/ingest",
    response_model=RepositoryIngestionResponse,
    summary="Ingest repository tree and source files",
    description=(
        "Orchestrates full repository ingestion: fetches git tree, filters relevant source "
        "and documentation files, retrieves text content up to safety limits, and returns "
        "structured repository data suitable for future RAG indexing."
    ),
    responses={
        200: {"description": "Repository successfully ingested."},
        400: {"description": "Invalid or malformed repository URL."},
        404: {"description": "Repository not found or inaccessible."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API unavailable or request timed out."},
    },
)
async def ingest_repository(request: RepositoryIngestionRequest) -> RepositoryIngestionResponse:
    """Orchestrate full repository tree and code ingestion."""
    try:
        data = await repository_ingestion_service.ingest_repository(
            url=request.url, branch=request.branch
        )
        return RepositoryIngestionResponse(**data)
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found or is not publicly accessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while ingesting '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"Service error while ingesting '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error ingesting '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while ingesting the repository.",
        )


@router.post(
    "/analyze-ai",
    response_model=RepositoryAIAnalysisResponse,
    summary="Analyze repository architecture and structure with AI",
    description=(
        "Retrieves repository metadata, file tree, and key configuration/source files, "
        "builds a prioritized context budget, and prompts the configured LLM provider "
        "(default: local Ollama) to generate a grounded, structured architectural analysis."
    ),
    responses={
        200: {"description": "Repository successfully analyzed with AI."},
        400: {"description": "Invalid or malformed repository URL."},
        404: {"description": "Repository not found or AI model not installed in provider."},
        403: {"description": "GitHub API rate limit exceeded."},
        502: {"description": "AI model output failed validation against expected schema."},
        503: {"description": "AI provider is unavailable (e.g. Ollama offline) or GitHub unavailable."},
        504: {"description": "AI provider request timed out."},
        500: {"description": "Unexpected internal server error."},
    },
)
async def analyze_repository_ai(
    request: RepositoryAnalyzeRequest,
    branch: Optional[str] = Query(None, description="Optional branch or commit ref to analyze"),
) -> RepositoryAIAnalysisResponse:
    """
    Handle grounded AI repository architecture analysis:
    1. Validates repository URL.
    2. Builds controlled context from metadata, README, tree, and prioritized source files.
    3. Calls configured LLM provider (Ollama by default).
    4. Validates and returns structured response.
    """
    try:
        response = await repository_analysis_service.analyze_repository_with_ai(
            url=request.url,
            branch=branch,
        )
        return response
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found or is not publicly accessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while analyzing '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error while analyzing '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMProviderUnavailableError as exc:
        logger.warning(f"LLM provider unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMModelNotFoundError as exc:
        logger.warning(f"LLM model not found: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except LLMTimeoutError as exc:
        logger.warning(f"LLM request timed out: {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except AIAnalysisValidationError as exc:
        logger.error(f"AI response validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except UnsupportedLLMProviderError as exc:
        logger.error(f"Configuration error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error during AI analysis of '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the repository with AI.",
        )


@router.post(
    "/structure-explainer",
    response_model=StructureExplainerResponse,
    summary="Repository Structure Explainer / Understand This Repository",
    description=(
        "Provides a clear, beginner-friendly explanation of repository purpose, "
        "directory responsibilities, architecturally significant files, component communication, "
        "data flow, technology map, onboarding reading sequence, and GitHub-compatible Mermaid architecture diagram."
    ),
    responses={
        200: {"description": "Repository structure successfully explained."},
        400: {"description": "Invalid or malformed repository URL."},
        404: {"description": "Repository not found or AI model not installed."},
        403: {"description": "GitHub API rate limit exceeded."},
        502: {"description": "AI model output failed validation against expected schema."},
        503: {"description": "AI provider or GitHub API is unavailable."},
        504: {"description": "AI provider request timed out."},
        500: {"description": "Unexpected internal server error."},
    },
)
async def explain_repository_structure(
    request: StructureExplainerRequest,
    branch: Optional[str] = Query(None, description="Optional branch or commit ref to explain"),
) -> StructureExplainerResponse:
    """
    Handle Repository Structure Explainer analysis:
    1. Validates repository URL.
    2. Gathers metadata, directory tree, manifests, and RAG context snippets.
    3. Calls configured LLM provider to explain architecture, flow, directories, and files.
    4. Generates a valid GitHub-compatible Mermaid architecture diagram.
    """
    try:
        response = await structure_explainer_service.explain_repository_structure(
            url=request.url,
            branch=branch or request.branch,
        )
        return response
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found or is not publicly accessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while explaining '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error while explaining '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMProviderUnavailableError as exc:
        logger.warning(f"LLM provider unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMModelNotFoundError as exc:
        logger.warning(f"LLM model not found: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except LLMTimeoutError as exc:
        logger.warning(f"LLM request timed out: {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except UnsupportedLLMProviderError as exc:
        logger.error(f"Configuration error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error during structure explainer for '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while explaining repository structure.",
        )



@router.post(
    "/issues/analyze",
    response_model=IssueAIAnalysisResponse,
    summary="Analyze GitHub issue and generate investigation guide with AI",
    description=(
        "Retrieves a specific GitHub issue, extracts relevant repository context and file tree, "
        "and uses the configured LLM provider to produce grounded issue analysis, candidate files, "
        "estimated difficulty and skills, investigation steps, and evidence separation."
    ),
    responses={
        200: {"description": "Issue successfully analyzed with AI."},
        400: {"description": "Invalid or malformed repository URL or issue number."},
        404: {"description": "Repository or issue not found, or AI model not installed."},
        403: {"description": "GitHub API rate limit exceeded."},
        502: {"description": "AI model output failed validation against expected schema."},
        503: {"description": "AI provider is unavailable (e.g. Ollama offline) or GitHub unavailable."},
        504: {"description": "AI provider request timed out."},
        500: {"description": "Unexpected internal server error."},
    },
)
async def analyze_issue_ai(
    request: IssueAIAnalysisRequest,
) -> IssueAIAnalysisResponse:
    """
    Handle grounded AI issue analysis:
    1. Validates repository URL and issue number.
    2. Fetches issue details, repo metadata, and tree.
    3. Builds targeted context with candidate files and excerpts.
    4. Calls LLM provider to generate grounded issue recommendations.
    5. Validates and returns structured response.
    """
    try:
        response = await issue_analysis_service.analyze_issue_with_ai(
            url=request.url,
            issue_number=request.issue_number,
            branch=request.branch,
        )
        return response
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Issue or repository not found for URL '{request.url}' #{request.issue_number}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while analyzing issue #{request.issue_number}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error while analyzing issue #{request.issue_number}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMProviderUnavailableError as exc:
        logger.warning(f"LLM provider unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except LLMModelNotFoundError as exc:
        logger.warning(f"LLM model not found: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except LLMTimeoutError as exc:
        logger.warning(f"LLM request timed out: {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except AIAnalysisValidationError as exc:
        logger.error(f"AI issue response validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except UnsupportedLLMProviderError as exc:
        logger.error(f"Configuration error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(
            f"Unexpected error during AI analysis of issue #{request.issue_number} in '{request.url}': {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the issue with AI.",
        )


@router.post(
    "/issues/recommend",
    response_model=IssueRecommendationResponse,
    summary="Get personalized repository issue recommendations",
    description=(
        "Evaluates open repository issues against a developer skill profile (or active profile), "
        "calculates transparent skill match scores, provides grounded match reasons, highlights "
        "skill gaps and learning opportunities, and sorts recommendations deterministically."
    ),
    responses={
        200: {"description": "Personalized issue recommendations returned."},
        400: {"description": "Invalid repository owner or name."},
        404: {"description": "Repository not found."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API service unavailable."},
        500: {"description": "Internal server error."},
    },
)
async def recommend_repository_issues(
    request: IssueRecommendationRequest,
) -> IssueRecommendationResponse:
    """
    Produce personalized repository issue recommendations based on developer skills.
    Reuses existing AI issue analyses from memory cache where available.
    """
    try:
        owner = request.owner.strip()
        repo = request.repo.strip()
        if not owner or not repo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository owner and name must be specified.",
            )
        response = await skill_matching_service.get_recommendations_for_repository(
            owner=owner,
            repo=repo,
            profile=request.profile,
            branch=request.branch,
            issue_numbers=request.issue_numbers,
        )
        return response
    except HTTPException:
        raise
    except InvalidGitHubURLError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error recommending issues for {request.owner}/{request.repo}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating personalized issue recommendations.",
        )


def _to_rag_chunk_result(rc) -> RAGChunkResult:
    """Convert a RetrievedChunk to the API response schema."""
    return RAGChunkResult(
        chunk_id=rc.chunk.chunk_id,
        file_path=rc.chunk.file_path,
        language=rc.chunk.language,
        category=rc.chunk.category,
        start_line=rc.chunk.start_line,
        end_line=rc.chunk.end_line,
        content=rc.chunk.content,
        score=rc.score,
        matched_terms=rc.matched_terms,
        retrieval_reason=rc.retrieval_reason,
    )


@router.post(
    "/rag/retrieve",
    response_model=RAGRetrievalResponse,
    summary="RAG keyword retrieval — find relevant repository chunks",
    description=(
        "Loads repository files via the Phase 4 ingestion pipeline, splits them into "
        "structured chunks using language-aware heuristics, and performs deterministic "
        "keyword-based retrieval to return the most relevant chunks for a query. "
        "Does NOT call any LLM provider."
    ),
    responses={
        200: {"description": "Relevant chunks successfully retrieved."},
        400: {"description": "Invalid or malformed GitHub repository URL."},
        404: {"description": "Repository not found or inaccessible."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API unavailable or timed out."},
    },
)
async def rag_retrieve(request: RAGRetrieveRequest) -> RAGRetrievalResponse:
    """
    RAG retrieval pipeline (Phase 7):
    1. Validate GitHub URL.
    2. Load repository documents via RepositoryIngestionService.
    3. Chunk documents using structure-aware splitter.
    4. Score and rank chunks using deterministic keyword retrieval.
    5. Return top-K results with scores and matched terms.
    """
    try:
        result = await repository_rag_service.retrieve_for_query(
            url=request.repository_url,
            query=request.query,
            branch=request.branch,
            top_k=request.top_k,
        )

        stats = result.statistics
        return RAGRetrievalResponse(
            repository=result.repository,
            query=result.query,
            retrieval_mode=result.retrieval_mode,
            results=[_to_rag_chunk_result(rc) for rc in result.results],
            statistics=RAGRetrievalStatistics(
                documents_loaded=stats.documents_loaded,
                documents_skipped=stats.documents_skipped,
                chunks_created=stats.chunks_created,
                chunks_searched=stats.chunks_searched,
                results_returned=stats.results_returned,
            ),
        )
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found or is not publicly accessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while retrieving RAG chunks: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error during RAG retrieve: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error during RAG retrieve for '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during RAG retrieval.",
        )


@router.post(
    "/rag/context",
    response_model=RAGContextResponse,
    summary="RAG context builder — format retrieved chunks into LLM context",
    description=(
        "Runs the full RAG retrieval pipeline and additionally formats the top retrieved "
        "chunks into a structured context string suitable for future LLM prompting. "
        "Supports both vector and keyword retrieval modes. Does NOT call any LLM provider."
    ),
    responses={
        200: {"description": "Context successfully built."},
        400: {"description": "Invalid or malformed GitHub repository URL."},
        404: {"description": "Repository not found or inaccessible."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "GitHub API unavailable or timed out."},
    },
)
async def rag_context(request: RAGRetrieveRequest) -> RAGContextResponse:
    """
    RAG context pipeline (Phase 7 & 8):
    1-4. Retrieve top chunks (vector or keyword fallback).
    5. Format top-K retrieved chunks into bounded context text.
    6. Return context string + retrieved chunks + statistics.
    """
    try:
        result = await repository_rag_service.context_for_query(
            url=request.repository_url,
            query=request.query,
            branch=request.branch,
            top_k=request.top_k,
        )

        stats = result.statistics
        return RAGContextResponse(
            repository=result.repository,
            query=result.query,
            retrieval_mode=result.retrieval_mode,
            context=result.context,
            retrieved_chunks=[_to_rag_chunk_result(rc) for rc in result.retrieved_chunks],
            statistics=RAGRetrievalStatistics(
                documents_loaded=stats.documents_loaded,
                documents_skipped=stats.documents_skipped,
                chunks_created=stats.chunks_created,
                chunks_searched=stats.chunks_searched,
                results_returned=stats.results_returned,
            ),
        )
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found or is not publicly accessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded during RAG context build: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub API rate limit exceeded. Please try again later or configure a GitHub token.",
        )
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error during RAG context build: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Unexpected error during RAG context for '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during RAG context building.",
        )


@router.post(
    "/rag/index",
    response_model=RAGIndexResponse,
    summary="Index repository into PostgreSQL with pgvector embeddings",
    description=(
        "Loads repository documents, generates structure-aware chunks, computes SHA-256 hashes, "
        "re-uses existing embeddings for unchanged chunks, embeds new/modified chunks using local "
        "SentenceTransformers on CPU, and stores vector embeddings in PostgreSQL + pgvector."
    ),
    responses={
        200: {"description": "Repository successfully indexed."},
        400: {"description": "Invalid repository URL."},
        404: {"description": "Repository not found or not accessible."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "Embedding provider or database unavailable."},
        500: {"description": "Unexpected indexing error."},
    },
)
async def rag_index(request: RAGIndexRequest) -> RAGIndexResponse:
    """
    Phase 8: Index repository chunks into pgvector with local embeddings.
    """
    try:
        result = await repository_rag_service.index_repository(
            url=request.repository_url,
            branch=request.branch,
        )
        return RAGIndexResponse(
            repository=result.repository,
            documents_processed=result.documents_processed,
            chunks_created=result.chunks_created,
            chunks_embedded=result.chunks_embedded,
            chunks_reused=result.chunks_reused,
            chunks_updated=result.chunks_updated,
            embedding_dimension=result.embedding_dimension,
            elapsed_time_seconds=result.elapsed_time_seconds,
        )
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.repository_url}': {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.repository_url}': {exc}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub repository not found.")
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded while indexing repository: {exc}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GitHub API rate limit exceeded.")
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error during repository indexing: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except EmbeddingProviderError as exc:
        logger.error(f"Embedding provider error during indexing: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Embedding provider error: {exc}")
    except Exception as exc:
        logger.exception(f"Unexpected error during RAG indexing for '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during repository indexing.",
        )


@router.post(
    "/rag/vector-search",
    response_model=RAGVectorSearchResponse,
    summary="Semantic similarity search over indexed repository chunks",
    description=(
        "Embeds the user query with the local model and retrieves the top-K most similar "
        "repository chunks from PostgreSQL using pgvector cosine similarity. Falls back to "
        "deterministic keyword retrieval if PostgreSQL/pgvector is unavailable."
    ),
    responses={
        200: {"description": "Search completed successfully."},
        400: {"description": "Invalid query or repository URL."},
        404: {"description": "Repository not found."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "Service unavailable."},
        500: {"description": "Unexpected search error."},
    },
)
async def rag_vector_search(request: RAGVectorSearchRequest) -> RAGVectorSearchResponse:
    """
    Phase 8: Semantic vector search over repository chunks.
    """
    try:
        result = await repository_rag_service.retrieve_for_query(
            url=request.repository_url,
            query=request.query,
            branch=request.branch,
            top_k=request.top_k,
            retrieval_mode="vector",
        )
        chunk_results = [
            VectorChunkResult(
                file_path=rc.chunk.file_path,
                language=rc.chunk.language,
                category=rc.chunk.category,
                start_line=rc.chunk.start_line,
                end_line=rc.chunk.end_line,
                content=rc.chunk.content,
                similarity_score=rc.score,
                metadata=rc.chunk.metadata,
            )
            for rc in result.results
        ]
        return RAGVectorSearchResponse(
            repository=result.repository,
            query=result.query,
            retrieval_mode=result.retrieval_mode,
            results=chunk_results,
            statistics=RAGVectorSearchStatistics(
                total_indexed_chunks=result.statistics.chunks_searched,
                results_returned=len(chunk_results),
            ),
        )
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository URL '{request.repository_url}': {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for URL '{request.repository_url}': {exc}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except GitHubRateLimitError as exc:
        logger.warning(f"Rate limit exceeded during vector search: {exc}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GitHub rate limit exceeded.")
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error during vector search: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error in vector search for '{request.repository_url}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during vector search.",
        )


@router.post(
    "/chat",
    response_model=RepositoryChatResponse,
    summary="Repository-aware grounded AI chat with verified evidence",
    description=(
        "Retrieves relevant repository chunks using semantic vector search with keyword "
        "fallback, formats bounded context, queries the configured LLM provider, "
        "and validates evidence citations against actual retrieved source chunks."
    ),
    responses={
        200: {"description": "Chat response generated successfully with verified sources."},
        400: {"description": "Empty question or invalid repository specification."},
        404: {"description": "Repository or LLM model not found."},
        403: {"description": "GitHub API rate limit exceeded."},
        502: {"description": "LLM response decoding or validation error."},
        503: {"description": "LLM provider (e.g. Ollama) or GitHub service unavailable."},
        504: {"description": "LLM provider request timed out."},
        500: {"description": "Unexpected internal server error."},
    },
)
async def chat_with_repository(request: RepositoryChatRequest) -> RepositoryChatResponse:
    """
    Phase 9: Repository-aware AI chat grounded in RAG.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace-only.",
        )

    if not request.owner or not request.owner.strip() or not request.repo or not request.repo.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both repository owner and repo name must be provided.",
        )

    question = ChatQuestion(
        owner=request.owner.strip(),
        repo=request.repo.strip(),
        question=request.question.strip(),
        branch=request.branch.strip() if request.branch else None,
        top_k=request.top_k,
    )

    try:
        chat_answer = await repository_chat_service.chat(question)

        sources = [
            ChatSourceItem(
                path=s.path,
                chunk_id=s.chunk_id,
                start_line=s.start_line,
                end_line=s.end_line,
                category=s.category,
                score=s.score,
                retrieval_reason=s.retrieval_reason,
            )
            for s in chat_answer.sources
        ]

        return RepositoryChatResponse(
            answer=chat_answer.answer,
            sources=sources,
            retrieval_mode=chat_answer.retrieval_mode,
            retrieved_chunks_count=chat_answer.retrieved_chunks_count,
            uncertainties=chat_answer.uncertainties,
        )
    except ValueError as exc:
        logger.warning(f"Validation error in repository chat: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository specification: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubNotFoundError as exc:
        logger.info(f"Repository not found for chat: {question.repository_identifier}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{question.repository_identifier}' not found or is inaccessible.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"GitHub rate limit exceeded during chat: {exc}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GitHub API rate limit exceeded.")
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error during chat: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except LLMProviderUnavailableError as exc:
        logger.warning(f"LLM provider unavailable during chat: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except LLMModelNotFoundError as exc:
        logger.warning(f"LLM model not found during chat: {exc}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except LLMTimeoutError as exc:
        logger.warning(f"LLM timeout during chat: {exc}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error in repository chat for '{question.repository_identifier}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during repository chat.",
        )


@router.post(
    "/issues/contribution-guide",
    response_model=ContributionGuideResponse,
    summary="Generate AI contribution guide for an issue",
    description=(
        "Generates a repository-specific, grounded contribution guide for a specific GitHub issue. "
        "Retrieves issue metadata, queries repository context via RAG, invokes LLM with anti-hallucination "
        "constraints, strictly validates all cited file paths against retrieved chunks, and optionally "
        "personalizes guidance based on the developer's skill profile."
    ),
    responses={
        200: {"description": "Contribution guide successfully generated."},
        400: {"description": "Invalid repository owner, name, or issue number."},
        404: {"description": "Repository or issue not found, or LLM model not found."},
        403: {"description": "GitHub API rate limit exceeded."},
        503: {"description": "LLM provider or GitHub service unavailable."},
        504: {"description": "LLM provider request timed out."},
        500: {"description": "Unexpected internal server error."},
    },
)
async def generate_contribution_guide(
    request: ContributionGuideRequest,
) -> ContributionGuideResponse:
    """
    Phase 11: Grounded AI Contribution Guide for an issue.
    """
    if not request.owner or not request.owner.strip() or not request.repo or not request.repo.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both repository owner and repo name must be provided.",
        )

    if request.issue_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issue number must be a positive integer.",
        )

    try:
        response = await contribution_guide_service.generate_guide(request)
        return response
    except ValueError as exc:
        logger.warning(f"Validation error in contribution guide: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except InvalidGitHubURLError as exc:
        logger.warning(f"Invalid repository specification: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubNotFoundError as exc:
        logger.info(f"Repository or issue not found: {request.owner}/{request.repo}#{request.issue_number}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue #{request.issue_number} or repository '{request.owner}/{request.repo}' not found.",
        )
    except GitHubRateLimitError as exc:
        logger.warning(f"GitHub rate limit exceeded during contribution guide: {exc}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GitHub API rate limit exceeded.")
    except GitHubServiceError as exc:
        logger.error(f"GitHub service error during contribution guide: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except LLMProviderUnavailableError as exc:
        logger.warning(f"LLM provider unavailable during contribution guide: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except LLMModelNotFoundError as exc:
        logger.warning(f"LLM model not found during contribution guide: {exc}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except LLMTimeoutError as exc:
        logger.warning(f"LLM timeout during contribution guide: {exc}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    except Exception as exc:
        logger.exception(
            f"Unexpected error in contribution guide for '{request.owner}/{request.repo}#{request.issue_number}': {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the contribution guide.",
        )


