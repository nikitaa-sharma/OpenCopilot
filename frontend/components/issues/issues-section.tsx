"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";
import { IssueFilters, FilterCategory } from "@/components/issues/issue-filters";
import { IssueCard } from "@/components/issues/issue-card";
import { IssueAnalysisModal } from "@/components/issues/issue-analysis-modal";
import { LiveIssueAIModal } from "@/components/issues/live-issue-ai-modal";
import { Badge } from "@/components/ui/badge";
import { GitHubIssueItem, Issue, IssueAIAnalysisResponse } from "@/types";
import { analyzeIssueAI, ApiError } from "@/lib/api";

const DEMO_ISSUES: Issue[] = [
  {
    id: 124,
    repositoryId: 1,
    githubIssueId: 98124,
    issueNumber: 124,
    title: "Improve documentation for dependency injection sub-dependencies",
    description: "Provide clear code examples and architecture diagrams demonstrating deep nested dependency injection overrides in FastAPI applications.",
    state: "open",
    labels: ["documentation", "good first issue"],
    difficulty: "Beginner",
    requiredSkills: ["Python", "Markdown", "FastAPI"],
    analysis: {
      difficultyScore: "Beginner",
      requiredSkills: ["Python", "Markdown", "FastAPI"],
      summary: "This issue targets tutorial clarity in docs/en/docs/tutorial/dependencies/sub-dependencies.md. No changes to core Python routing logic are required.",
      affectedComponents: ["docs/en/docs/tutorial/dependencies/", "docs_src/dependencies/"],
      estimatedHours: "1-2 hours",
      keyFiles: ["docs/en/docs/tutorial/dependencies/sub-dependencies.md"],
    },
  },
  {
    id: 157,
    repositoryId: 1,
    githubIssueId: 98157,
    issueNumber: 157,
    title: "Add additional test coverage for query parameters",
    description: "Expand pytest test suites to cover edge cases with list query parameters, default values, and custom alias validation errors.",
    state: "open",
    labels: ["testing", "good first issue"],
    difficulty: "Intermediate",
    requiredSkills: ["Python", "Pytest", "Git"],
    analysis: {
      difficultyScore: "Intermediate",
      requiredSkills: ["Python", "Pytest", "Git"],
      summary: "Requires creating new test functions inside tests/test_query_params.py asserting status codes 422 for invalid aliases and 200 for valid parameter matrices.",
      affectedComponents: ["tests/test_query_params.py", "fastapi/params.py"],
      estimatedHours: "2-3 hours",
      keyFiles: ["tests/test_query_params.py"],
    },
  },
  {
    id: 189,
    repositoryId: 1,
    githubIssueId: 98189,
    issueNumber: 189,
    title: "Improve request processing throughput for large JSON payloads",
    description: "Investigate and benchmark JSON deserialization bottlenecks when parsing deeply nested Pydantic models in high-concurrency environments.",
    state: "open",
    labels: ["enhancement", "performance"],
    difficulty: "Advanced",
    requiredSkills: ["Python", "Asyncio", "ASGI", "Starlette"],
    analysis: {
      difficultyScore: "Advanced",
      requiredSkills: ["Python", "Asyncio", "ASGI", "Starlette"],
      summary: "Involves profiling the request body parsing pipeline in fastapi/routing.py and benchmarking orjson vs standard json serialization.",
      affectedComponents: ["fastapi/routing.py", "fastapi/dependencies/utils.py"],
      estimatedHours: "6-8 hours",
      keyFiles: ["fastapi/routing.py"],
    },
  },
];

interface IssuesSectionProps {
  issues?: GitHubIssueItem[];
  isLive?: boolean;
  repoUrl?: string;
  branch?: string;
  onScrollToGuide?: () => void;
}

export function IssuesSection({
  issues,
  isLive = false,
  repoUrl,
  branch,
  onScrollToGuide,
}: IssuesSectionProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterCategory>("All");
  const [selectedIssueForModal, setSelectedIssueForModal] = useState<Issue | null>(null);

  // Live Issue AI Analysis State
  const [selectedLiveIssue, setSelectedLiveIssue] = useState<GitHubIssueItem | null>(null);
  const [liveIssueLoading, setLiveIssueLoading] = useState(false);
  const [liveIssueError, setLiveIssueError] = useState<string | null>(null);
  const [liveIssueResult, setLiveIssueResult] = useState<IssueAIAnalysisResponse | null>(null);

  const handleAnalyzeLiveIssue = async (issue: GitHubIssueItem) => {
    setSelectedLiveIssue(issue);
    setLiveIssueLoading(true);
    setLiveIssueError(null);
    setLiveIssueResult(null);

    // Derive target repository URL if not directly supplied
    const targetUrl =
      repoUrl ||
      (issue.html_url ? issue.html_url.replace(/\/issues\/\d+.*$/, "") : "https://github.com/fastapi/fastapi");

    try {
      const result = await analyzeIssueAI(targetUrl, issue.number, branch);
      setLiveIssueResult(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setLiveIssueError(err.message);
      } else {
        setLiveIssueError(
          "An unexpected error occurred while communicating with the AI service. Please verify Ollama is running."
        );
      }
    } finally {
      setLiveIssueLoading(false);
    }
  };

  // If live issues are available, filter them
  const hasLiveIssues = isLive && issues !== undefined;

  const filteredIssues = hasLiveIssues
    ? issues.filter((issue) => {
        const query = searchQuery.toLowerCase();
        const matchesQuery =
          !query ||
          issue.title.toLowerCase().includes(query) ||
          (issue.body && issue.body.toLowerCase().includes(query)) ||
          issue.labels.some((l) => l.toLowerCase().includes(query)) ||
          (issue.user && issue.user.toLowerCase().includes(query));

        if (!matchesQuery) return false;

        const labelsLower = issue.labels.map((l) => l.toLowerCase());
        if (activeFilter === "All") return true;
        if (activeFilter === "Good First Issue") {
          return labelsLower.some((l) => l.includes("good first") || l.includes("help wanted"));
        }
        if (activeFilter === "Documentation") {
          return labelsLower.some((l) => l.includes("doc"));
        }
        if (activeFilter === "Enhancement") {
          return labelsLower.some((l) => l.includes("enhancement") || l.includes("feature"));
        }
        if (activeFilter === "Bug") {
          return labelsLower.some((l) => l.includes("bug"));
        }
        if (activeFilter === "Beginner") {
          return labelsLower.some((l) => l.includes("good first") || l.includes("beginner") || l.includes("easy"));
        }
        return true;
      })
    : DEMO_ISSUES.filter((issue) => {
        const query = searchQuery.toLowerCase();
        const matchesQuery =
          !query ||
          issue.title.toLowerCase().includes(query) ||
          issue.description.toLowerCase().includes(query) ||
          issue.labels.some((l) => l.toLowerCase().includes(query)) ||
          issue.requiredSkills.some((s) => s.toLowerCase().includes(query));

        if (!matchesQuery) return false;

        if (activeFilter === "All") return true;
        if (activeFilter === "Beginner" && issue.difficulty === "Beginner") return true;
        if (activeFilter === "Intermediate" && issue.difficulty === "Intermediate") return true;
        if (activeFilter === "Advanced" && issue.difficulty === "Advanced") return true;
        if (activeFilter === "Good First Issue" && issue.labels.includes("good first issue")) return true;
        if (activeFilter === "Documentation" && issue.labels.includes("documentation")) return true;
        if (activeFilter === "Enhancement" && issue.labels.includes("enhancement")) return true;
        if (activeFilter === "Bug" && issue.labels.includes("bug")) return true;

        return false;
      });

  return (
    <section id="issues" className="py-12 border-t border-border/40 scroll-mt-16">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>Issue Backlog</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Repository Issues
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {hasLiveIssues
                ? "Live open issues fetched directly from GitHub (pull requests strictly excluded)."
                : "Search and explore issues with AI-estimated complexity and prerequisite skill tags."}
            </p>
          </div>

          {hasLiveIssues ? (
            <Badge variant="success" className="text-xs font-medium uppercase tracking-wider self-start sm:self-auto">
              Live GitHub Data
            </Badge>
          ) : (
            <Badge variant="warning" className="text-xs font-medium uppercase tracking-wider self-start sm:self-auto">
              Example Preview • Demo Data
            </Badge>
          )}
        </div>

        {/* Filter Controls */}
        <IssueFilters
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
          totalCount={filteredIssues.length}
        />

        {/* Issues Grid */}
        {filteredIssues.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredIssues.map((issue) => (
              <IssueCard
                key={issue.id || ("number" in issue ? issue.number : issue.issueNumber)}
                issue={issue}
                isLive={hasLiveIssues}
                onViewAnalysis={(iss) => setSelectedIssueForModal(iss as Issue)}
                onAnalyzeAI={handleAnalyzeLiveIssue}
              />
            ))}
          </div>
        ) : (
          <div className="p-8 rounded-xl border border-dashed border-border bg-card/40 text-center">
            <p className="text-sm text-muted-foreground">
              No issues found matching &quot;{searchQuery}&quot; with filter &quot;{activeFilter}&quot;.
            </p>
          </div>
        )}

        {/* AI Analysis Modal Dialog (Used for demo issues) */}
        {!hasLiveIssues && (
          <IssueAnalysisModal
            issue={selectedIssueForModal}
            open={!!selectedIssueForModal}
            onClose={() => setSelectedIssueForModal(null)}
            onOpenGuide={onScrollToGuide}
          />
        )}

        {/* Live GitHub Issue AI Analysis Modal */}
        {hasLiveIssues && (
          <LiveIssueAIModal
            issue={selectedLiveIssue}
            open={!!selectedLiveIssue}
            isLoading={liveIssueLoading}
            error={liveIssueError}
            analysisResult={liveIssueResult}
            onClose={() => setSelectedLiveIssue(null)}
            onRetry={() => selectedLiveIssue && handleAnalyzeLiveIssue(selectedLiveIssue)}
          />
        )}
      </div>
    </section>
  );
}
