"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  UserCheck,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  BookOpen,
  GraduationCap,
  Layers,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DeveloperSkillProfile,
  GitHubIssueItem,
  IssueAIAnalysisResponse,
  IssueRecommendationItem,
  IssueRecommendationResponse,
} from "@/types";
import { recommendRepositoryIssues, analyzeIssueAI, ApiError } from "@/lib/api";
import { LiveIssueAIModal } from "@/components/issues/live-issue-ai-modal";

interface RecommendedIssuesProps {
  owner?: string;
  repo?: string;
  branch?: string;
  profile?: DeveloperSkillProfile;
  isLive?: boolean;
  onSelectIssue?: (issueId: number) => void;
  onScrollToGuide?: () => void;
  onScrollToProfile?: () => void;
}

export function RecommendedIssues({
  owner,
  repo,
  branch,
  profile,
  isLive = false,
  onSelectIssue,
  onScrollToGuide,
  onScrollToProfile,
}: RecommendedIssuesProps) {
  const [recommendations, setRecommendations] = useState<IssueRecommendationItem[]>([]);
  const [totalConsidered, setTotalConsidered] = useState(0);
  const [explanation, setExplanation] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIssues, setExpandedIssues] = useState<{ [issueNumber: number]: boolean }>({});

  // Live issue analysis modal state
  const [selectedIssueForAnalysis, setSelectedIssueForAnalysis] = useState<GitHubIssueItem | null>(null);
  const [analysisModalOpen, setAnalysisModalOpen] = useState(false);
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<IssueAIAnalysisResponse | null>(null);

  const fetchRecommendations = useCallback(async () => {
    if (!isLive || !owner || !repo) return;

    setIsLoading(true);
    setError(null);
    try {
      const resp: IssueRecommendationResponse = await recommendRepositoryIssues(
        owner,
        repo,
        profile,
        branch
      );
      setRecommendations(resp.recommendations);
      setTotalConsidered(resp.total_issues_considered);
      setExplanation(resp.explanation);
      // Expand top issue by default
      if (resp.recommendations.length > 0) {
        setExpandedIssues({ [resp.recommendations[0].issue.number]: true });
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to load personalized recommendations from the server.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [isLive, owner, repo, profile, branch]);

  useEffect(() => {
    if (isLive && owner && repo) {
      fetchRecommendations();
    }
  }, [isLive, owner, repo, profile, fetchRecommendations]);

  const toggleExpanded = (issueNum: number) => {
    setExpandedIssues((prev) => ({
      ...prev,
      [issueNum]: !prev[issueNum],
    }));
  };

  const handleAnalyzeIssue = async (issueItem: GitHubIssueItem) => {
    setSelectedIssueForAnalysis(issueItem);
    setAnalysisModalOpen(true);
    setIsAnalysisLoading(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    const targetUrl = `https://github.com/${owner}/${repo}`;
    try {
      const result = await analyzeIssueAI(targetUrl, issueItem.number, branch);
      setAnalysisResult(result);
      // Refresh recommendations to use newly cached AI analysis
      fetchRecommendations();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setAnalysisError(err.message);
      } else {
        setAnalysisError("Failed to analyze issue with AI. Please verify Ollama is running.");
      }
    } finally {
      setIsAnalysisLoading(false);
    }
  };

  const getDifficultyBadge = (difficulty?: string) => {
    const d = (difficulty || "unknown").toLowerCase();
    if (d === "beginner") {
      return (
        <Badge variant="success" className="text-xs font-mono">
          AI Difficulty: Beginner
        </Badge>
      );
    }
    if (d === "intermediate") {
      return (
        <Badge variant="warning" className="text-xs font-mono">
          AI Difficulty: Intermediate
        </Badge>
      );
    }
    if (d === "advanced") {
      return (
        <Badge variant="destructive" className="text-xs font-mono">
          AI Difficulty: Advanced
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-xs font-mono">
        AI Difficulty: Unknown
      </Badge>
    );
  };

  const getMatchScoreBadge = (score: number) => {
    const percentage = Math.round(score * 100);
    if (percentage >= 75) {
      return (
        <Badge variant="success" className="text-xs font-semibold">
          {percentage}% Skill Match
        </Badge>
      );
    }
    if (percentage >= 40) {
      return (
        <Badge variant="warning" className="text-xs font-semibold">
          {percentage}% Skill Match
        </Badge>
      );
    }
    if (percentage > 0) {
      return (
        <Badge variant="outline" className="text-xs font-semibold border-primary/40 text-primary">
          {percentage}% Skill Match
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-xs font-semibold text-muted-foreground">
        0% Skill Match • Learning Opportunity
      </Badge>
    );
  };

  // Check if profile is empty
  const isProfileEmpty =
    !profile ||
    (profile.programming_languages.length === 0 &&
      profile.frameworks.length === 0 &&
      profile.tools.length === 0 &&
      profile.domains.length === 0 &&
      profile.interests.length === 0);

  // DEMO DATA for initial preview mode
  const demoRecommendation: IssueRecommendationItem = {
    issue: {
      number: 157,
      title: "Add additional test coverage for query parameters",
      body: "Expand pytest test suites to cover edge cases with list query parameters.",
      state: "open",
      html_url: "https://github.com/fastapi/fastapi/issues/157",
      labels: ["testing", "good first issue"],
      comments_count: 2,
    },
    skill_match: {
      score: 0.85,
      matched_skills: ["Python", "FastAPI", "Testing", "Git"],
      missing_skills: ["Pytest"],
      match_reasons: [
        "Issue requires Python knowledge, which matches your skill profile.",
        "Your profile includes FastAPI, aligning directly with the repository framework.",
        "Candidate files in tests/ match your declared interest in Testing.",
      ],
      learning_opportunities: [
        "Working on this issue provides an opportunity to gain experience with Pytest parameterization.",
      ],
    },
    difficulty: "beginner",
    difficulty_rationale: "Small localized test addition with existing pattern fixtures.",
    match_label: "Highest skill-match score",
  };

  const displayList = isLive ? recommendations : [demoRecommendation];

  return (
    <section id="recommendations" className="py-12 border-t border-border/40 scroll-mt-16 bg-card/20">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Skill-Targeted Discovery</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Recommended for You
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {isLive
                ? `Personalized issue matches calculated transparently from your skill profile (${totalConsidered} issues evaluated).`
                : "Issues that appear to match your skills and experience."}
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {isLive ? (
              <Button
                variant="outline"
                size="sm"
                onClick={fetchRecommendations}
                disabled={isLoading}
                className="gap-1.5 text-xs h-8"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
                <span>Refresh Recommendations</span>
              </Button>
            ) : (
              <Badge variant="warning" className="text-xs font-medium uppercase tracking-wider">
                Example Preview • Demo Mode
              </Badge>
            )}
          </div>
        </div>

        {/* Empty Profile Notice */}
        {isProfileEmpty && isLive && (
          <div className="mb-6 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 max-w-4xl mx-auto">
            <AlertCircle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-foreground space-y-1">
              <p className="font-semibold text-amber-500">
                Add your skills to personalize issue recommendations.
              </p>
              <p className="text-muted-foreground">
                You haven&apos;t added any programming languages or frameworks yet. Recommendations currently reflect general repository topic alignment.
              </p>
            </div>
            {onScrollToProfile && (
              <Button
                size="sm"
                variant="outline"
                onClick={onScrollToProfile}
                className="text-xs h-8 border-amber-500/40 text-amber-500 hover:bg-amber-500/10 shrink-0"
              >
                Configure Profile
              </Button>
            )}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="p-12 text-center max-w-4xl mx-auto bg-card/80 border border-border rounded-xl space-y-3">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="text-sm font-medium text-foreground">
              Evaluating repository issues against your developer profile...
            </p>
            <p className="text-xs text-muted-foreground">
              Calculating deterministic skill match scores and identifying learning opportunities.
            </p>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-6 text-center max-w-4xl mx-auto bg-destructive/10 border border-destructive/30 rounded-xl space-y-3">
            <AlertCircle className="h-6 w-6 mx-auto text-destructive" />
            <p className="text-sm font-semibold text-destructive">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchRecommendations}
              className="text-xs"
            >
              Try Again
            </Button>
          </div>
        )}

        {/* Empty Issues State */}
        {isLive && !isLoading && !error && recommendations.length === 0 && (
          <div className="p-8 text-center max-w-4xl mx-auto bg-card/80 border border-border rounded-xl space-y-2">
            <AlertCircle className="h-6 w-6 mx-auto text-muted-foreground" />
            <h4 className="text-sm font-semibold text-foreground">No open issues were found.</h4>
            <p className="text-xs text-muted-foreground">
              This repository currently has no open issues or they could not be retrieved from GitHub.
            </p>
          </div>
        )}

        {/* Recommendations List */}
        {!isLoading && !error && displayList.length > 0 && (
          <div className="space-y-6 max-w-4xl mx-auto">
            {displayList.map((rec) => {
              const isExpanded = !!expandedIssues[rec.issue.number];
              const matchPercentage = Math.round(rec.skill_match.score * 100);

              return (
                <Card
                  key={rec.issue.number}
                  className="border-border bg-card/90 shadow-xl overflow-hidden transition-all hover:border-primary/40"
                >
                  <CardHeader className="p-5 sm:p-6 border-b border-border/40 bg-secondary/15">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-sm font-bold text-primary">
                            Issue #{rec.issue.number}
                          </span>
                          {getMatchScoreBadge(rec.skill_match.score)}
                          {getDifficultyBadge(rec.difficulty)}
                          <Badge variant="outline" className="text-xs font-mono text-muted-foreground">
                            {rec.match_label}
                          </Badge>
                        </div>

                        <CardTitle className="text-base sm:text-lg font-bold text-foreground hover:text-primary transition-colors">
                          {rec.issue.title}
                        </CardTitle>

                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {rec.issue.labels.map((lbl) => (
                            <span
                              key={lbl}
                              className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border/40"
                            >
                              {lbl}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 shrink-0 self-start">
                        {isLive && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleAnalyzeIssue(rec.issue)}
                            className="gap-1.5 text-xs h-8"
                          >
                            <Sparkles className="h-3.5 w-3.5 text-primary" />
                            <span>Analyze with AI</span>
                          </Button>
                        )}

                        {onScrollToGuide && (
                          <Button
                            size="sm"
                            variant="default"
                            onClick={() => {
                              if (onSelectIssue) onSelectIssue(rec.issue.number);
                              if (onScrollToGuide) onScrollToGuide();
                            }}
                            className="gap-1.5 text-xs h-8 bg-primary hover:bg-primary/90 text-primary-foreground"
                          >
                            <BookOpen className="h-3.5 w-3.5" />
                            <span>Contribution Guide</span>
                          </Button>
                        )}

                        <a
                          href={rec.issue.html_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground bg-secondary hover:bg-secondary/80 border border-border px-3 py-1.5 rounded-md transition-colors h-8"
                        >
                          <span>View on GitHub</span>
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="p-5 sm:p-6 space-y-5">
                    {/* Skills Breakdown Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Matched Skills */}
                      <div className="p-3.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            <span>Matched Skills ({rec.skill_match.matched_skills.length})</span>
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {rec.skill_match.matched_skills.length === 0 ? (
                            <span className="text-xs text-muted-foreground/70 italic">
                              No direct overlap detected.
                            </span>
                          ) : (
                            rec.skill_match.matched_skills.map((skill) => (
                              <span
                                key={skill}
                                className="inline-flex items-center gap-1 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 px-2.5 py-0.5 rounded-md"
                              >
                                <span>{skill}</span>
                              </span>
                            ))
                          )}
                        </div>
                      </div>

                      {/* Skill Gaps */}
                      <div className="p-3.5 rounded-lg bg-amber-500/5 border border-amber-500/20 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                            <GraduationCap className="h-3.5 w-3.5" />
                            <span>Skill Gaps ({rec.skill_match.missing_skills.length})</span>
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {rec.skill_match.missing_skills.length === 0 ? (
                            <span className="text-xs text-muted-foreground/70 italic">
                              All required skills matched in your profile!
                            </span>
                          ) : (
                            rec.skill_match.missing_skills.map((skill) => (
                              <span
                                key={skill}
                                className="inline-flex items-center gap-1 text-xs font-mono bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 px-2.5 py-0.5 rounded-md"
                              >
                                <span>{skill}</span>
                              </span>
                            ))
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Accordion: Why Recommended & Learning Opportunities */}
                    <div className="border border-border/60 rounded-lg overflow-hidden">
                      <button
                        type="button"
                        onClick={() => toggleExpanded(rec.issue.number)}
                        className="w-full flex items-center justify-between p-3.5 text-xs font-semibold text-foreground bg-secondary/20 hover:bg-secondary/40 transition-colors text-left"
                      >
                        <div className="flex items-center space-x-2">
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                          <span>Why this issue matches your skills ({matchPercentage}% match)</span>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="p-4 bg-secondary/10 border-t border-border/60 space-y-4 text-xs leading-relaxed animate-in fade-in duration-150">
                          {/* Match Reasons */}
                          <div className="space-y-1.5">
                            <span className="font-bold text-foreground block">
                              Match Reasons:
                            </span>
                            <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
                              {rec.skill_match.match_reasons.map((reason, idx) => (
                                <li key={idx}>{reason}</li>
                              ))}
                            </ul>
                          </div>

                          {/* Learning Opportunities */}
                          {rec.skill_match.learning_opportunities.length > 0 && (
                            <div className="space-y-1.5 pt-2 border-t border-border/40">
                              <span className="font-bold text-amber-600 dark:text-amber-400 block flex items-center gap-1.5">
                                <BookOpen className="h-3.5 w-3.5" />
                                <span>Learning Opportunities:</span>
                              </span>
                              <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
                                {rec.skill_match.learning_opportunities.map((opp, idx) => (
                                  <li key={idx}>{opp}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* AI Difficulty Rationale if present */}
                          {rec.difficulty_rationale && (
                            <div className="p-2.5 rounded bg-secondary/40 border border-border/40 text-[11px] text-muted-foreground">
                              <span className="font-semibold text-foreground">AI Difficulty Estimate Rationale: </span>
                              {rec.difficulty_rationale}
                            </div>
                          )}

                          {/* Matching criteria disclaimer */}
                          <p className="text-[11px] text-muted-foreground/70 font-mono pt-1">
                            Note: Skill match scores represent the proportion of analyzed requirements that overlap with your provided profile. Difficulty is an intrinsic technical complexity estimate evaluated separately.
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Grounded Live Issue AI Analysis Modal */}
      <LiveIssueAIModal
        issue={selectedIssueForAnalysis}
        open={analysisModalOpen}
        isLoading={isAnalysisLoading}
        error={analysisError}
        analysisResult={analysisResult}
        onClose={() => setAnalysisModalOpen(false)}
        onRetry={() => {
          if (selectedIssueForAnalysis) {
            handleAnalyzeIssue(selectedIssueForAnalysis);
          }
        }}
      />
    </section>
  );
}
