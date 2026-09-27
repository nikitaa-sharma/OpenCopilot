"use client";

import { Star, GitFork, AlertCircle, ExternalLink, Code2, Tag, ArrowDown, Shield } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GitHubRepositoryInfo } from "@/types";

interface RepositoryOverviewProps {
  repository?: GitHubRepositoryInfo | null;
  isLive?: boolean;
  onScrollToIssues?: () => void;
}

export function RepositoryOverview({
  repository,
  isLive = false,
  onScrollToIssues,
}: RepositoryOverviewProps) {
  // Demo fallback data if no live repository data is loaded
  const fallbackData = {
    owner: "fastapi",
    name: "FastAPI",
    fullName: "fastapi/fastapi",
    description: "FastAPI framework for building APIs with Python 3.8+ based on standard Python type hints.",
    url: "https://github.com/fastapi/fastapi",
    stars: "12.4k",
    forks: "2.1k",
    openIssuesAndPrs: "143",
    language: "Python",
    license: "MIT License",
    topics: ["Python", "API", "Web", "Async", "OpenAPI", "TypeHints"],
  };

  const formatCount = (count: number): string => {
    if (count >= 1_000_000) {
      return (count / 1_000_000).toFixed(1) + "M";
    }
    if (count >= 1_000) {
      return (count / 1_000).toFixed(1) + "k";
    }
    return count.toLocaleString();
  };

  const currentData = isLive && repository
    ? {
        owner: repository.owner,
        name: repository.name,
        fullName: repository.full_name,
        description: repository.description || "No description provided for this repository.",
        url: repository.html_url || `https://github.com/${repository.full_name}`,
        stars: formatCount(repository.stars),
        forks: formatCount(repository.forks),
        openIssuesAndPrs: formatCount(repository.open_issues_count),
        language: repository.language || "Not specified",
        license: repository.license?.name || "Not specified",
        topics: repository.topics || [],
      }
    : fallbackData;

  return (
    <section id="overview" className="py-12 border-t border-border/40 scroll-mt-16">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header with Demarcation Notice */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Code2 className="h-3.5 w-3.5" />
              <span>Repository Overview</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Repository Dashboard
            </h2>
          </div>

          {/* Demarcation badge */}
          <div className="flex items-center space-x-2">
            {isLive ? (
              <Badge variant="success" className="text-xs font-medium uppercase tracking-wider">
                Live GitHub Data
              </Badge>
            ) : (
              <Badge variant="warning" className="text-xs font-medium uppercase tracking-wider">
                Example Preview • Demo Data
              </Badge>
            )}
          </div>
        </div>

        {/* Main Dashboard Card */}
        <Card className="border-border bg-card/80 backdrop-blur shadow-xl overflow-hidden">
          <CardHeader className="border-b border-border/40 p-6 sm:p-8 bg-secondary/15">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-xl sm:text-2xl font-bold text-foreground">
                    {currentData.name}
                  </h3>
                  <span className="text-xs text-muted-foreground font-mono bg-secondary px-2 py-0.5 rounded border border-border">
                    {currentData.fullName}
                  </span>
                  <Badge variant="info" className="text-[11px]">
                    Public
                  </Badge>
                  {currentData.license && currentData.license !== "Not specified" && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground bg-secondary/70 border border-border px-2 py-0.5 rounded">
                      <Shield className="h-3 w-3 text-emerald-400" />
                      <span>{currentData.license}</span>
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground max-w-3xl leading-relaxed">
                  {currentData.description}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 shrink-0">
                <a
                  href={currentData.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground bg-secondary/80 hover:bg-secondary border border-border px-3.5 py-2 rounded-md transition-colors"
                >
                  <span>View on GitHub</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>

                <Button
                  size="sm"
                  onClick={onScrollToIssues}
                  className="gap-1.5 text-xs font-medium shadow-sm"
                >
                  <span>View Issues</span>
                  <ArrowDown className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6 sm:p-8 space-y-6">
            {/* Metric Counters */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-secondary/30 border border-border/60">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Stars</span>
                  <Star className="h-4 w-4 text-amber-500 dark:text-amber-400" />
                </div>
                <p className="text-2xl font-bold text-foreground mt-2 font-mono">
                  {currentData.stars}
                </p>
                <span className="text-[11px] text-muted-foreground">GitHub stargazers</span>
              </div>

              <div className="p-4 rounded-lg bg-secondary/30 border border-border/60">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Forks</span>
                  <GitFork className="h-4 w-4 text-sky-500 dark:text-sky-400" />
                </div>
                <p className="text-2xl font-bold text-foreground mt-2 font-mono">
                  {currentData.forks}
                </p>
                <span className="text-[11px] text-muted-foreground">Community forks</span>
              </div>

              <div className="p-4 rounded-lg bg-secondary/30 border border-border/60">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Open Issues & PRs</span>
                  <AlertCircle className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
                </div>
                <p className="text-2xl font-bold text-foreground mt-2 font-mono">
                  {currentData.openIssuesAndPrs}
                </p>
                <span className="text-[11px] text-muted-foreground">Reported by GitHub</span>
              </div>

              <div className="p-4 rounded-lg bg-secondary/30 border border-border/60">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Language</span>
                  <Code2 className="h-4 w-4 text-primary" />
                </div>
                <p className="text-2xl font-bold text-foreground mt-2 font-mono">
                  {currentData.language}
                </p>
                <span className="text-[11px] text-muted-foreground">Primary language</span>
              </div>
            </div>

            {/* Topics Bar */}
            {currentData.topics.length > 0 && (
              <div className="pt-2 flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground shrink-0 font-medium">
                  <Tag className="h-3.5 w-3.5" />
                  <span>Topics:</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {currentData.topics.map((topic) => (
                    <span
                      key={topic}
                      className="text-xs font-medium bg-secondary/70 hover:bg-secondary border border-border/80 px-2.5 py-0.5 rounded-full text-foreground/90 transition-colors"
                    >
                      #{topic}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
