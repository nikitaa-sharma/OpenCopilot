import {
  ErrorType,
  RepositoryAnalysisResponse,
  RepositoryTreeResponse,
  FileContentResponse,
  RepositoryIngestionResponse,
  RepositoryAIAnalysisResponse,
  IssueAIAnalysisResponse,
  RAGRetrievalResponse,
  RAGContextResponse,
  RAGIndexResponse,
  RAGVectorSearchResponse,
  RepositoryChatResponse,
  DeveloperSkillProfile,
  IssueRecommendationResponse,
  ContributionGuideResponse,
  StructureExplainerResponse,
  AuthUser,
  AuthRegisterRequest,
  AuthLoginRequest,
  AuthTokenResponse,
  AuthStatusResponse,
} from "@/types";


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export class ApiError extends Error {
  statusCode: number;
  errorType: ErrorType;
  detail?: string;

  constructor(message: string, statusCode: number, errorType: ErrorType, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.errorType = errorType;
    this.detail = detail;
  }
}

function mapStatusToErrorType(status: number): ErrorType {
  if (status === 404) return "not_found";
  if (status === 403) return "rate_limit";
  if (status === 400) return "invalid_url";
  return "not_found";
}

// ---------------------------------------------------------------------------
// Phase 12: Auth Token Storage & Header Helpers
// ---------------------------------------------------------------------------
const AUTH_TOKEN_STORAGE_KEY = "opencopilot_access_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } catch {
    // ignore local storage errors
  }
}

export function removeAuthToken(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * Sends a public repository URL to the FastAPI backend for GitHub analysis.
 */
export async function analyzeRepository(url: string): Promise<RepositoryAnalysisResponse> {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url: trimmedUrl }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Unable to connect to the backend server (${errorMsg}). Please ensure the backend is running.`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        detail = errorJson.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  const data: RepositoryAnalysisResponse = await response.json();
  return data;
}

/**
 * Fetches the recursive repository tree hierarchy for a repository.
 */
export async function getRepositoryTree(
  owner: string,
  repo: string,
  branch?: string
): Promise<RepositoryTreeResponse> {
  const query = branch ? `?branch=${encodeURIComponent(branch)}` : "";
  const url = `${API_BASE_URL}/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/tree${query}`;

  let response: Response;
  try {
    response = await fetch(url);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend while fetching tree: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "Failed to load repository tree.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Fetches the text content and metadata of a single repository file on-demand.
 */
export async function getRepositoryFile(
  owner: string,
  repo: string,
  path: string,
  branch?: string
): Promise<FileContentResponse> {
  const query = branch ? `?branch=${encodeURIComponent(branch)}` : "";
  // Encode each segment of path to preserve forward slashes
  const encodedPath = path.split("/").map(encodeURIComponent).join("/");
  const url = `${API_BASE_URL}/v1/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/files/${encodedPath}${query}`;

  let response: Response;
  try {
    response = await fetch(url);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend while fetching file: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = `Failed to load file '${path}'.`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Triggers batch repository ingestion for source code and documentation.
 */
export async function ingestRepository(
  url: string,
  branch?: string
): Promise<RepositoryIngestionResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url: url.trim(), branch }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend while ingesting repository: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "Failed to ingest repository.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Checks backend health status.
 */
export async function checkBackendHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

/**
 * Sends a public repository URL to the FastAPI backend for AI architecture analysis.
 */
export async function analyzeRepositoryAI(
  url: string,
  branch?: string
): Promise<RepositoryAIAnalysisResponse> {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  const queryParams = branch ? `?branch=${encodeURIComponent(branch)}` : "";
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/analyze-ai${queryParams}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url: trimmedUrl }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Unable to connect to the backend server (${errorMsg}). Please ensure the backend is running.`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred during AI analysis.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        detail = errorJson.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Sends a public repository URL to the FastAPI backend for Repository Structure Explainer
 * / Understand This Repository analysis.
 */
export async function explainRepositoryStructure(
  url: string,
  branch?: string
): Promise<StructureExplainerResponse> {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  const queryParams = branch ? `?branch=${encodeURIComponent(branch)}` : "";
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/structure-explainer${queryParams}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url: trimmedUrl, branch }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Unable to connect to the backend server (${errorMsg}). Please ensure the backend is running.`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred while explaining repository structure.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        detail = errorJson.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Sends a public repository URL and issue number to the FastAPI backend for AI issue analysis.
 */
export async function analyzeIssueAI(
  url: string,
  issueNumber: number,
  branch?: string
): Promise<IssueAIAnalysisResponse> {
  const trimmedUrl = url.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/issues/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: trimmedUrl,
        issue_number: issueNumber,
        branch,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Unable to connect to the backend server (${errorMsg}). Please ensure the backend is running.`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = `An unexpected error occurred during AI analysis of issue #${issueNumber}.`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        detail = errorJson.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * RAG keyword retrieval — returns the most relevant repository chunks for a query.
 * Does NOT call any LLM provider.
 */
export async function ragRetrieve(
  repositoryUrl: string,
  query: string,
  topK?: number,
  branch?: string
): Promise<RAGRetrievalResponse> {
  const trimmedUrl = repositoryUrl.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/rag/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_url: trimmedUrl,
        query,
        top_k: topK,
        branch,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for RAG retrieval: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred during RAG retrieval.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * RAG context builder — retrieves relevant chunks and formats them into
 * a bounded context string suitable for LLM prompting (future phases).
 * Does NOT call any LLM provider.
 */
export async function ragContext(
  repositoryUrl: string,
  query: string,
  topK?: number,
  branch?: string
): Promise<RAGContextResponse> {
  const trimmedUrl = repositoryUrl.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/rag/context`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_url: trimmedUrl,
        query,
        top_k: topK,
        branch,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for RAG context: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred during RAG context building.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 8: Index a repository into PostgreSQL with pgvector embeddings.
 * Generates local SentenceTransformer embeddings for new/changed chunks.
 */
export async function indexRepositoryRAG(
  repositoryUrl: string,
  branch?: string
): Promise<RAGIndexResponse> {
  const trimmedUrl = repositoryUrl.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/rag/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_url: trimmedUrl,
        branch,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for RAG indexing: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred during RAG indexing.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 8: Vector semantic search over indexed repository chunks using pgvector.
 */
export async function ragVectorSearch(
  repositoryUrl: string,
  query: string,
  topK?: number,
  branch?: string
): Promise<RAGVectorSearchResponse> {
  const trimmedUrl = repositoryUrl.trim();
  if (!trimmedUrl) {
    throw new ApiError("Repository URL cannot be empty.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/rag/vector-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_url: trimmedUrl,
        query,
        top_k: topK,
        branch,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for RAG vector search: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred during RAG vector search.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 9: Repository-aware grounded AI chat with verified evidence.
 */
export async function chatWithRepository(
  owner: string,
  repo: string,
  question: string,
  branch?: string,
  topK?: number
): Promise<RepositoryChatResponse> {
  const trimmedQuestion = question.trim();
  if (!trimmedQuestion) {
    throw new ApiError("Question cannot be empty.", 400, "invalid_url");
  }

  const trimmedOwner = owner.trim();
  const trimmedRepo = repo.trim();
  if (!trimmedOwner || !trimmedRepo) {
    throw new ApiError("Repository owner and name must be specified.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        owner: trimmedOwner,
        repo: trimmedRepo,
        question: trimmedQuestion,
        branch: branch?.trim() || undefined,
        top_k: topK,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for repository chat: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred during repository chat.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 10: Fetch current developer skill profile.
 */
export async function getDeveloperSkillProfile(): Promise<DeveloperSkillProfile> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/profile/skills`, {
      headers: {
        ...getAuthHeaders(),
      },
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for profile retrieval: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "Could not retrieve developer skill profile.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 10: Update and normalize developer skill profile.
 */
export async function saveDeveloperSkillProfile(
  profile: DeveloperSkillProfile
): Promise<DeveloperSkillProfile> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/profile/skills`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(profile),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for profile update: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "Could not update developer skill profile.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 10: Fetch personalized repository issue recommendations based on developer profile.
 */
export async function recommendRepositoryIssues(
  owner: string,
  repo: string,
  profile?: DeveloperSkillProfile,
  branch?: string
): Promise<IssueRecommendationResponse> {
  const trimmedOwner = owner.trim();
  const trimmedRepo = repo.trim();
  if (!trimmedOwner || !trimmedRepo) {
    throw new ApiError("Repository owner and name must be specified.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/issues/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        owner: trimmedOwner,
        repo: trimmedRepo,
        profile,
        branch: branch?.trim() || undefined,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for issue recommendations: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred while recommending issues.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Phase 11: Generate grounded AI contribution guide for an issue.
 */
export async function generateContributionGuide(
  owner: string,
  repo: string,
  issueNumber: number,
  branch?: string,
  profile?: DeveloperSkillProfile,
  topK?: number
): Promise<ContributionGuideResponse> {
  const trimmedOwner = owner.trim();
  const trimmedRepo = repo.trim();
  if (!trimmedOwner || !trimmedRepo) {
    throw new ApiError("Repository owner and name must be specified.", 400, "invalid_url");
  }
  if (!issueNumber || issueNumber < 1) {
    throw new ApiError("A valid positive issue number must be provided.", 400, "invalid_url");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/repositories/issues/contribution-guide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        owner: trimmedOwner,
        repo: trimmedRepo,
        issue_number: issueNumber,
        branch: branch?.trim() || undefined,
        profile,
        top_k: topK,
      }),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(
      `Failed to connect to backend for contribution guide: ${errorMsg}`,
      503,
      "not_found"
    );
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred while generating the contribution guide.";
    try {
      const errorJson = await response.json();
      if (errorJson.detail) detail = errorJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Phase 12: Authentication API Endpoints
// ---------------------------------------------------------------------------

/**
 * Register a new user account with email, password, and display name.
 */
export async function registerUser(payload: AuthRegisterRequest): Promise<AuthTokenResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(`Failed to connect to auth service: ${errorMsg}`, 503, "not_found");
  }

  if (!response.ok) {
    let detail = "Registration failed. Please check your details and try again.";
    try {
      const errJson = await response.json();
      if (errJson.detail) detail = errJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  const data: AuthTokenResponse = await response.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

/**
 * Log in with existing credentials to obtain a JWT token.
 */
export async function loginUser(payload: AuthLoginRequest): Promise<AuthTokenResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(`Failed to connect to auth service: ${errorMsg}`, 503, "not_found");
  }

  if (!response.ok) {
    let detail = "Invalid email or password.";
    try {
      const errJson = await response.json();
      if (errJson.detail) detail = errJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  const data: AuthTokenResponse = await response.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

/**
 * Fetch current authenticated user's profile (/auth/me).
 */
export async function getCurrentUser(): Promise<AuthUser> {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError("Not authenticated", 401, "not_found");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Network error";
    throw new ApiError(`Failed to connect to auth service: ${errorMsg}`, 503, "not_found");
  }

  if (!response.ok) {
    let detail = "Session expired or invalid.";
    try {
      const errJson = await response.json();
      if (errJson.detail) detail = errJson.detail;
    } catch {
      detail = response.statusText || detail;
    }
    // Remove invalid token on 401
    if (response.status === 401) {
      removeAuthToken();
    }
    throw new ApiError(detail, response.status, mapStatusToErrorType(response.status), detail);
  }

  return response.json();
}

/**
 * Log out user: notifies backend and removes client token.
 */
export async function logoutUser(): Promise<void> {
  const token = getAuthToken();
  try {
    if (token) {
      await fetch(`${API_BASE_URL}/v1/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    }
  } catch {
    // Non-blocking logout network failure
  } finally {
    removeAuthToken();
  }
}

