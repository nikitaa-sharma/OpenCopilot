/**
 * Core Domain Types & UI Data Contracts for OpenSource Copilot
 */

export type RepositoryState = "idle" | "analyzing" | "ready" | "error";

export type ErrorType = "invalid_url" | "private_repo" | "not_found" | "rate_limit";

export interface UserSkill {
  id: number;
  name: string;
  proficiencyLevel: "beginner" | "intermediate" | "advanced";
}

export interface User {
  id: number;
  username: string;
  githubId?: string;
  email?: string;
  avatarUrl?: string;
  skills: UserSkill[];
  createdAt: string;
}

export interface FileTreeNode {
  id: string;
  name: string;
  type: "file" | "folder";
  path: string;
  description?: string;
  children?: FileTreeNode[];
}

export interface TechnologyItem {
  name: string;
  role: string;
  category: "Language" | "Framework" | "Library" | "Testing" | "Tooling";
  description: string;
  iconName: string;
}

export interface IssueAnalysis {
  difficultyScore: "Beginner" | "Intermediate" | "Advanced";
  requiredSkills: string[];
  summary: string;
  affectedComponents: string[];
  estimatedHours?: string;
  keyFiles?: string[];
}

export interface ContributionGuide {
  issueId: number;
  steps: {
    number: string;
    title: string;
    description: string;
    icon: string;
  }[];
  recommendedFiles: string[];
  testingTips?: string;
}

export interface Issue {
  id: number;
  repositoryId: number;
  githubIssueId: number;
  issueNumber: number;
  title: string;
  body?: string;
  state: "open" | "closed" | string;
  labels: string[];
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  requiredSkills: string[];
  description: string;
  analysis?: IssueAnalysis;
  contributionGuide?: ContributionGuide;
}

export interface RepositoryStats {
  stars: string;
  forks: string;
  openIssues: number;
  primaryLanguage: string;
}

export interface Repository {
  id: number;
  owner: string;
  name: string;
  fullName: string;
  url: string;
  description?: string;
  defaultBranch: string;
  stats: RepositoryStats;
  topics: string[];
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  sources?: ChatSourceItem[];
  retrievalMode?: string;
  uncertainties?: string[];
}

// GitHub API Integration Types (Phase 3)
export interface GitHubLicense {
  key?: string;
  name?: string;
  spdx_id?: string;
  url?: string;
}

export interface GitHubRepositoryInfo {
  id?: number;
  owner: string;
  name: string;
  full_name: string;
  description?: string;
  html_url?: string;
  default_branch: string;
  visibility: string;
  language?: string;
  license?: GitHubLicense | null;
  stars: number;
  forks: number;
  watchers: number;
  open_issues_count: number;
  topics: string[];
  created_at?: string;
  updated_at?: string;
  pushed_at?: string;
}

export interface GitHubReadmeInfo {
  name: string;
  content?: string;
  html_url?: string;
  size: number;
}

export interface GitHubIssueItem {
  id?: number;
  number: number;
  title: string;
  body?: string;
  state: string;
  html_url: string;
  labels: string[];
  user?: string;
  comments_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface AnalysisSource {
  provider: string;
  owner: string;
  repository: string;
}

export interface RepositoryAnalysisResponse {
  repository: GitHubRepositoryInfo;
  languages: Record<string, number>;
  readme?: GitHubReadmeInfo | null;
  issues: GitHubIssueItem[];
  source: AnalysisSource;
}

// Phase 4: Repository Tree and Ingestion Types
export interface RepoTreeItem {
  path: string;
  type: "file" | "directory";
  size?: number | null;
  sha?: string | null;
  category?: string | null;
  language?: string | null;
}

export interface RepositoryTreeResponse {
  repository: string;
  branch: string;
  truncated: boolean;
  total_items: number;
  tree: RepoTreeItem[];
}

export interface FileContentResponse {
  path: string;
  name: string;
  language?: string | null;
  category: string;
  size: number;
  sha?: string | null;
  content?: string | null;
  encoding: string;
  is_binary: boolean;
  skip_reason?: string | null;
}

export interface IngestionStatistics {
  total_tree_items: number;
  directories: number;
  files: number;
  selected_files: number;
  skipped_files: number;
  total_code_bytes: number;
}

export interface RepositoryIngestionResponse {
  repository: {
    owner: string;
    name: string;
    branch: string;
  };
  statistics: IngestionStatistics;
  files: FileContentResponse[];
}

// ==============================================================================
// AI Repository Analysis Types (Phase 5)
// ==============================================================================

export interface AITechnologyItem {
  name: string;
  category: string;
  evidence: string;
}

export interface AIDirectoryExplanation {
  path: string;
  explanation: string;
  evidence?: string | null;
}

export interface AIFileExplanation {
  path: string;
  reason: string;
  evidence?: string | null;
}

export interface AIEntryPoint {
  path: string;
  description: string;
  confidence: "high" | "medium" | "low" | "unknown" | string;
}

export interface AITestingOverview {
  framework: string;
  structure: string;
  evidence?: string | null;
}

export interface RepositoryAIAnalysis {
  summary: string;
  purpose: string;
  architecture: string;
  technology_stack: AITechnologyItem[];
  important_directories: AIDirectoryExplanation[];
  important_files: AIFileExplanation[];
  entry_points: AIEntryPoint[];
  testing: AITestingOverview;
  beginner_explanation: string;
  confidence_assessment: string;
}

export interface RepositoryAIAnalysisResponse {
  repository: {
    owner: string;
    name: string;
    branch: string;
  };
  analysis: RepositoryAIAnalysis;
  provider: string;
  model: string;
  context_stats?: {
    files_included: number;
    total_context_chars: number;
  } | null;
}

// ==============================================================================
// AI Issue Analysis & Recommendation Types (Phase 6)
// ==============================================================================

export interface CandidateFile {
  path: string;
  reason: string;
  confidence: "likely" | "possible" | "speculative" | string;
}

export interface IssueAIAnalysis {
  issue_type: "bug" | "feature" | "documentation" | "refactor" | "test" | "chore" | string;
  difficulty: "beginner" | "intermediate" | "advanced" | "unknown" | string;
  difficulty_rationale: string;
  required_skills: string[];
  skills_rationale: string;
  candidate_files: CandidateFile[];
  affected_areas: string[];
  investigation_steps: string[];
  prerequisites: string;
  ai_explanation: string;
  observed_evidence: string[];
  inferences: string[];
  unknowns: string[];
  confidence: "high" | "medium" | "low" | string;
}

export interface IssueAIAnalysisRequest {
  url: string;
  issue_number: number;
  branch?: string;
}

export interface IssueAIAnalysisResponse {
  repository: {
    owner: string;
    name: string;
    branch: string;
  };
  issue_number: number;
  issue_title: string;
  issue_url: string;
  analysis: IssueAIAnalysis;
  provider: string;
  model: string;
  context_stats?: {
    files_included: number;
    total_context_chars: number;
  } | null;
}

// ==============================================================================
// RAG Pipeline Types (Phase 7)
// ==============================================================================

export interface RAGChunkResult {
  chunk_id: string;
  file_path: string;
  language?: string | null;
  category: string;
  start_line: number;
  end_line: number;
  content: string;
  score: number;
  matched_terms: string[];
  retrieval_reason: string;
}

export interface RAGRetrievalStatistics {
  documents_loaded: number;
  documents_skipped: number;
  chunks_created: number;
  chunks_searched: number;
  results_returned: number;
}

export interface RAGRetrievalResponse {
  repository: string;
  query: string;
  retrieval_mode?: string;
  results: RAGChunkResult[];
  statistics: RAGRetrievalStatistics;
}

export interface RAGContextResponse {
  repository: string;
  query: string;
  retrieval_mode?: string;
  context: string;
  retrieved_chunks: RAGChunkResult[];
  statistics: RAGRetrievalStatistics;
}

// ==============================================================================
// Phase 8: Local Embeddings & Vector Semantic Search Types
// ==============================================================================

export interface RAGIndexRequest {
  repository_url: string;
  branch?: string;
}

export interface RAGIndexResponse {
  repository: string;
  documents_processed: number;
  chunks_created: number;
  chunks_embedded: number;
  chunks_reused: number;
  chunks_updated: number;
  embedding_dimension: number;
  elapsed_time_seconds?: number;
}

export interface RAGVectorSearchRequest {
  repository_url: string;
  query: string;
  top_k?: number;
  branch?: string;
}

export interface VectorChunkResult {
  file_path: string;
  language?: string | null;
  category: string;
  start_line: number;
  end_line: number;
  content: string;
  similarity_score: number;
  metadata?: Record<string, unknown>;
}

export interface RAGVectorSearchResponse {
  repository: string;
  query: string;
  retrieval_mode: string;
  results: VectorChunkResult[];
  statistics: {
    total_indexed_chunks?: number;
    results_returned: number;
  };
}

// ==============================================================================
// Phase 9: Repository-Aware AI Chat Types
// ==============================================================================

export interface ChatSourceItem {
  path: string;
  chunk_id?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  category: string;
  score?: number | null;
  retrieval_reason?: string | null;
}

export interface RepositoryChatRequest {
  owner: string;
  repo: string;
  question: string;
  branch?: string;
  top_k?: number;
}

export interface RepositoryChatResponse {
  answer: string;
  sources: ChatSourceItem[];
  retrieval_mode: string;
  retrieved_chunks_count: number;
  uncertainties: string[];
}

// ==============================================================================
// Phase 10: Developer Skill Profile & Personalized Recommendations
// ==============================================================================

export interface DeveloperSkillProfile {
  programming_languages: string[];
  frameworks: string[];
  tools: string[];
  domains: string[];
  experience_level?: "beginner" | "intermediate" | "advanced" | string;
  interests: string[];
}

export interface SkillMatchResult {
  score: number;
  matched_skills: string[];
  matched_required_skills?: string[];
  matched_repo_skills?: string[];
  missing_skills: string[];
  match_reasons: string[];
  learning_opportunities: string[];
}

export interface IssueRecommendationItem {
  issue: GitHubIssueItem;
  skill_match: SkillMatchResult;
  difficulty: "beginner" | "intermediate" | "advanced" | "unknown" | string;
  difficulty_rationale?: string | null;
  analysis?: IssueAIAnalysis | null;
  match_label: string;
}

export interface IssueRecommendationRequest {
  owner: string;
  repo: string;
  branch?: string;
  profile?: DeveloperSkillProfile;
  issue_numbers?: number[];
}

export interface IssueRecommendationResponse {
  repository: string;
  recommendations: IssueRecommendationItem[];
  total_issues_considered: number;
  profile_used?: DeveloperSkillProfile | null;
  explanation: string;
}

// ==============================================================================
// Phase 11: AI Contribution Guide Types
// ==============================================================================

export interface ContributionGuideUnderstanding {
  summary: string;
  problem: string;
  expected_outcome: string;
}

export interface ContributionGuideFile {
  path: string;
  role: "source" | "test" | "config" | "documentation" | string;
  reason: string;
}

export interface ContributionGuideStep {
  step: number;
  title: string;
  description: string;
  files: string[];
}

export interface ContributionGuideCodeArea {
  path: string;
  area: string;
  guidance: string;
}

export interface ContributionGuideTestItem {
  type: "unit" | "integration" | "regression" | "manual" | string;
  description: string;
  files: string[];
}

export interface ContributionGuideEvidence {
  path: string;
  chunk_id?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  category: string;
  score?: number | null;
  reason?: string | null;
}

export interface ContributionGuide {
  issue_understanding: ContributionGuideUnderstanding;
  prerequisites: string[];
  relevant_files: ContributionGuideFile[];
  implementation_plan: ContributionGuideStep[];
  code_areas: ContributionGuideCodeArea[];
  testing_plan: ContributionGuideTestItem[];
  documentation_plan: string[];
  pull_request_checklist: string[];
  learning_opportunities: string[];
  uncertainties: string[];
  evidence: ContributionGuideEvidence[];
}

export interface ContributionGuideRequest {
  owner: string;
  repo: string;
  issue_number: number;
  branch?: string;
  profile?: DeveloperSkillProfile;
  top_k?: number;
}

export interface ContributionGuideResponse {
  issue: GitHubIssueItem;
  guide: ContributionGuide;
  retrieval_mode: string;
  sources: ContributionGuideEvidence[];
  uncertainties: string[];
}

/**
 * Phase 12: Authentication & User Accounts
 */
export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  avatar_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthRegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface AuthLoginRequest {
  email: string;
  password: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface AuthStatusResponse {
  authenticated: boolean;
  user?: AuthUser | null;
}

// ==============================================================================
// Repository Structure Explainer / Understand This Repository Types
// ==============================================================================

export interface RepositoryOverviewDetail {
  what_it_does: string;
  main_purpose: string;
  primary_technologies: string[];
  application_type: string;
  entry_points: string[];
  high_level_architecture: string;
}

export interface DirectoryExplanationDetail {
  name: string;
  purpose: string;
  contains: string;
  important_subdirectories: string[];
  relationship: string;
  evidence?: string | null;
  confidence: "high" | "medium" | "low" | "uncertain" | string;
}

export interface ImportantFileDetail {
  path: string;
  category: "manifest" | "config" | "entry_point" | "routing" | "database" | "api" | "test" | "devops" | "documentation" | "core_logic" | string;
  description: string;
  evidence?: string | null;
}

export interface ArchitectureExplanation {
  overview: string;
  pattern: string;
  layers: string[];
  diagram_mermaid: string;
}

export interface RepositoryFlow {
  execution_start: string;
  component_communication: string;
  data_entry: string;
  data_processing: string;
  data_storage: string;
  result_delivery: string;
}

export interface TechnologyMap {
  frontend: string[];
  backend: string[];
  database: string[];
  apis: string[];
  ai_ml: string[];
  testing: string[];
  devops: string[];
  build_tools: string[];
}

export interface WhereToStartStep {
  step_number: number;
  title: string;
  target_path?: string | null;
  guidance: string;
  why: string;
}

export interface StructureExplainerAnalysis {
  overview: RepositoryOverviewDetail;
  directories: DirectoryExplanationDetail[];
  important_files: ImportantFileDetail[];
  architecture: ArchitectureExplanation;
  flow: RepositoryFlow;
  technology_map: TechnologyMap;
  where_to_start: WhereToStartStep[];
  confidence_evidence: string;
}

export interface StructureExplainerResponse {
  repository: {
    owner: string;
    name: string;
    branch?: string;
  };
  explainer: StructureExplainerAnalysis;
  provider: string;
  model: string;
  context_stats?: {
    files_included: number;
    total_context_chars: number;
  } | null;
}


