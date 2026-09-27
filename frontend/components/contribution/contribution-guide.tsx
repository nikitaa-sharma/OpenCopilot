"use client";

import { useState, useEffect } from "react";
import {
  BookOpen,
  FolderSearch,
  PenTool,
  Code2,
  CheckCircle,
  CheckCircle2,
  FileText,
  GitPullRequest,
  ExternalLink,
  Sparkles,
  Bot,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
  GraduationCap,
  ShieldCheck,
  Terminal,
  ListChecks,
  FileCode,
  Square,
  CheckSquare,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  ContributionGuideResponse,
  ContributionGuide as ContributionGuideData,
  DeveloperSkillProfile,
  GitHubIssueItem,
} from "@/types";
import { generateContributionGuide, ApiError } from "@/lib/api";

interface ContributionGuideProps {
  owner?: string;
  repo?: string;
  branch?: string;
  issueNumber?: number;
  availableIssues?: GitHubIssueItem[];
  profile?: DeveloperSkillProfile;
  isLive?: boolean;
  onAskAiAboutIssue?: () => void;
  onSelectIssue?: (issueNumber: number) => void;
}

export function ContributionGuide({
  owner,
  repo,
  branch,
  issueNumber: initialIssueNumber,
  availableIssues = [],
  profile,
  isLive = false,
  onAskAiAboutIssue,
  onSelectIssue,
}: ContributionGuideProps) {
  const [selectedIssueNumber, setSelectedIssueNumber] = useState<number | undefined>(
    initialIssueNumber || (availableIssues.length > 0 ? availableIssues[0].number : undefined)
  );
  const [inputIssueNumber, setInputIssueNumber] = useState<string>(
    initialIssueNumber ? String(initialIssueNumber) : ""
  );
  const [guideData, setGuideData] = useState<ContributionGuideResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const [completedChecklist, setCompletedChecklist] = useState<{ [index: number]: boolean }>({});

  // Sync with prop updates
  useEffect(() => {
    if (initialIssueNumber && initialIssueNumber !== selectedIssueNumber) {
      setSelectedIssueNumber(initialIssueNumber);
      setInputIssueNumber(String(initialIssueNumber));
    }
  }, [initialIssueNumber, selectedIssueNumber]);

  // Load guide when issue selection changes and live mode is active
  const handleFetchGuide = async (issueNum: number) => {
    if (!owner || !repo || !issueNum || issueNum < 1) return;

    setIsLoading(true);
    setError(null);
    setCompletedChecklist({});

    try {
      const result = await generateContributionGuide(
        owner,
        repo,
        issueNum,
        branch,
        profile
      );
      setGuideData(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message);
      } else {
        setError("Failed to generate contribution guide. Please verify your connection or try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectIssueFromList = (num: number) => {
    setSelectedIssueNumber(num);
    setInputIssueNumber(String(num));
    if (onSelectIssue) onSelectIssue(num);
    if (isLive && owner && repo) {
      handleFetchGuide(num);
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(inputIssueNumber, 10);
    if (!isNaN(parsed) && parsed > 0) {
      setSelectedIssueNumber(parsed);
      if (onSelectIssue) onSelectIssue(parsed);
      if (isLive && owner && repo) {
        handleFetchGuide(parsed);
      }
    }
  };

  const toggleChecklistItem = (idx: number) => {
    setCompletedChecklist((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  // Demo fallback steps when not live
  const demoSteps = [
    {
      number: "01",
      title: "Understand the Issue",
      description: "Read the issue description, reproduction steps, and maintainer feedback carefully to confirm requirements.",
      icon: BookOpen,
    },
    {
      number: "02",
      title: "Find Relevant Files",
      description: "Locate the targeted source code and corresponding test suite files within the repository structure.",
      icon: FolderSearch,
    },
    {
      number: "03",
      title: "Plan the Change",
      description: "Draft an implementation strategy that preserves backwards compatibility and conforms to style guidelines.",
      icon: PenTool,
    },
    {
      number: "04",
      title: "Implement the Solution",
      description: "Make focused, minimal code modifications in a new git feature branch created from the default branch.",
      icon: Code2,
    },
    {
      number: "05",
      title: "Run Tests",
      description: "Execute the local test suite using pytest to ensure existing tests pass and new edge-case tests succeed.",
      icon: CheckCircle,
    },
    {
      number: "06",
      title: "Update Documentation",
      description: "Add docstrings, update relevant markdown pages under docs/, and check multilingual documentation guides.",
      icon: FileText,
    },
    {
      number: "07",
      title: "Create Pull Request",
      description: "Push your branch, complete the repository pull request template, and reference the target issue number.",
      icon: GitPullRequest,
    },
  ];

  const guide = guideData?.guide;
  const issue = guideData?.issue;

  return (
    <section id="guide" className="py-12 border-t border-border/40 scroll-mt-16">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Sparkles className="h-3.5 w-3.5" />
              <span>AI-Powered Contribution Guide</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Repository Contribution Guide
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Actionable, grounded implementation instructions generated specifically for selected issues using repository RAG.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {isLive ? (
              <Badge variant="outline" className="text-xs font-medium text-emerald-400 border-emerald-500/40 bg-emerald-500/10">
                Phase 11: Grounded AI Active
              </Badge>
            ) : (
              <Badge variant="warning" className="text-xs font-medium uppercase tracking-wider">
                Example Preview • Demo Mode
              </Badge>
            )}
          </div>
        </div>

        {/* Issue Selector & Control Bar (when live or issues available) */}
        {isLive && owner && repo && (
          <Card className="border-border/80 bg-card/60 shadow-sm">
            <CardContent className="p-4 sm:p-5">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Select Target Issue for Contribution
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    {availableIssues.slice(0, 5).map((iss) => (
                      <Button
                        key={iss.number}
                        size="sm"
                        variant={selectedIssueNumber === iss.number ? "default" : "outline"}
                        onClick={() => handleSelectIssueFromList(iss.number)}
                        className="text-xs h-7 gap-1"
                        disabled={isLoading}
                      >
                        <span>#{iss.number}</span>
                        <span className="truncate max-w-[120px] sm:max-w-[180px] opacity-80">
                          {iss.title}
                        </span>
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Manual Issue Number Input */}
                <form onSubmit={handleManualSubmit} className="flex items-center gap-2 w-full md:w-auto">
                  <div className="relative flex-1 md:w-44">
                    <Input
                      type="number"
                      placeholder="Issue # (e.g. 157)"
                      value={inputIssueNumber}
                      onChange={(e) => setInputIssueNumber(e.target.value)}
                      className="h-8 text-xs font-mono"
                      min={1}
                      disabled={isLoading}
                    />
                  </div>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={isLoading || !inputIssueNumber.trim()}
                    className="h-8 text-xs gap-1.5 shrink-0"
                  >
                    {isLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    <span>{guideData ? "Regenerate" : "Generate Guide"}</span>
                  </Button>
                </form>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && (
          <Card className="border-primary/40 bg-primary/5 shadow-md">
            <CardContent className="p-10 flex flex-col items-center justify-center text-center space-y-4">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary animate-pulse">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-foreground">
                  Generating Grounded Contribution Guide...
                </h3>
                <p className="text-xs text-muted-foreground max-w-md">
                  Fetching issue metadata, retrieving repository context via RAG, and compiling verified implementation steps.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <Card className="border-destructive/40 bg-destructive/5 shadow-sm">
            <CardContent className="p-6 flex items-start gap-4">
              <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="space-y-2 flex-1">
                <h3 className="text-sm font-semibold text-destructive">
                  Could Not Generate Contribution Guide
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {error}
                </p>
                {selectedIssueNumber && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleFetchGuide(selectedIssueNumber)}
                    className="text-xs h-7 gap-1.5 mt-2"
                  >
                    <RefreshCw className="h-3 w-3" />
                    <span>Try Again</span>
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Live Grounded Guide Content */}
        {!isLoading && guideData && guide && issue && (
          <div className="space-y-8 animate-in fade-in duration-200">
            {/* Guide Header Banner */}
            <Card className="border-primary/40 bg-card shadow-md overflow-hidden">
              <CardHeader className="p-5 sm:p-6 bg-secondary/20 border-b border-border/40">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="font-mono text-xs text-primary border-primary/40">
                        Issue #{issue.number}
                      </Badge>
                      <Badge
                        variant={issue.state === "open" ? "success" : "secondary"}
                        className="text-[11px] font-mono capitalize"
                      >
                        {issue.state}
                      </Badge>
                      <Badge variant="outline" className="text-[11px] font-mono text-muted-foreground">
                        Mode: {guideData.retrieval_mode}
                      </Badge>
                      <Badge variant="outline" className="text-[11px] font-mono text-muted-foreground">
                        {guideData.sources.length} sources verified
                      </Badge>
                    </div>
                    <CardTitle className="text-lg sm:text-xl font-bold text-foreground">
                      {issue.title}
                    </CardTitle>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <a
                      href={issue.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground bg-secondary hover:bg-secondary/80 border border-border px-3 py-1.5 rounded-md transition-colors h-8"
                    >
                      <span>View on GitHub</span>
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                    {onAskAiAboutIssue && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={onAskAiAboutIssue}
                        className="gap-1.5 text-xs h-8"
                      >
                        <Bot className="h-3.5 w-3.5" />
                        <span>Chat About Issue</span>
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-5 sm:p-6 space-y-6">
                {/* 1. Issue Understanding */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider">
                    <BookOpen className="h-4 w-4" />
                    <span>1. Issue Understanding</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-lg bg-secondary/30 border border-border/40 space-y-1.5">
                      <span className="text-xs font-semibold text-foreground">Summary</span>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {guide.issue_understanding.summary}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-destructive/5 border border-destructive/20 space-y-1.5">
                      <span className="text-xs font-semibold text-destructive">Problem / Bug Symptoms</span>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {guide.issue_understanding.problem}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-1.5">
                      <span className="text-xs font-semibold text-emerald-400">Expected Outcome</span>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {guide.issue_understanding.expected_outcome}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 2. Prerequisites & Skills */}
                {guide.prerequisites.length > 0 && (
                  <div className="space-y-2.5 pt-2 border-t border-border/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                      <Terminal className="h-4 w-4 text-primary" />
                      <span>2. Prerequisites & Environment</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {guide.prerequisites.map((prereq, idx) => (
                        <div
                          key={idx}
                          className="inline-flex items-center gap-1.5 text-xs bg-secondary/50 border border-border/60 text-foreground px-3 py-1 rounded-md"
                        >
                          <CheckCircle2 className="h-3 w-3 text-primary" />
                          <span>{prereq}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 3. Relevant Repository Files (Validated Against Evidence) */}
                {guide.relevant_files.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                        <FolderSearch className="h-4 w-4 text-primary" />
                        <span>3. Relevant Files to Inspect</span>
                      </div>
                      <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/40 font-mono">
                        <ShieldCheck className="h-3 w-3 mr-1 inline" /> Grounded in Repo Chunks
                      </Badge>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {guide.relevant_files.map((file, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-secondary/20 border border-border/60 flex items-start gap-3"
                        >
                          <FileCode className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                          <div className="space-y-1 min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <code className="text-xs font-mono font-bold text-foreground truncate">
                                {file.path}
                              </code>
                              <Badge variant="secondary" className="text-[10px] uppercase font-mono shrink-0">
                                {file.role}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                              {file.reason}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4. Sequential Implementation Plan */}
                {guide.implementation_plan.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                      <Code2 className="h-4 w-4 text-primary" />
                      <span>4. Step-by-Step Implementation Plan</span>
                    </div>
                    <div className="space-y-3">
                      {guide.implementation_plan.map((step) => (
                        <div
                          key={step.step}
                          className="p-4 rounded-lg bg-card border border-border/70 hover:border-primary/40 transition-colors space-y-2 shadow-sm"
                        >
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-sm font-black text-primary bg-primary/10 px-2 py-0.5 rounded">
                              Step {step.step}
                            </span>
                            <h4 className="text-sm font-bold text-foreground">
                              {step.title}
                            </h4>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed pl-1">
                            {step.description}
                          </p>
                          {step.files.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5 pt-1 pl-1">
                              <span className="text-[11px] text-muted-foreground/70 font-semibold">Target files:</span>
                              {step.files.map((f, i) => (
                                <code
                                  key={i}
                                  className="text-[11px] font-mono bg-secondary/80 text-primary px-1.5 py-0.5 rounded border border-border/40"
                                >
                                  {f}
                                </code>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 5. Code Areas to Inspect */}
                {guide.code_areas.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                      <PenTool className="h-4 w-4 text-primary" />
                      <span>5. Specific Code Areas to Check</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {guide.code_areas.map((area, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-lg bg-secondary/20 border border-border/50 space-y-1.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <code className="text-xs font-mono font-bold text-primary truncate">
                              {area.path}
                            </code>
                            <span className="text-[11px] font-mono text-muted-foreground shrink-0">
                              {area.area}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {area.guidance}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 6. Testing Plan */}
                {guide.testing_plan.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                      <span>6. Testing & Validation Plan</span>
                    </div>
                    <div className="space-y-2.5">
                      {guide.testing_plan.map((test, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex items-start gap-3"
                        >
                          <Badge variant="outline" className="text-[10px] font-mono uppercase text-emerald-400 border-emerald-500/40 shrink-0 mt-0.5">
                            {test.type}
                          </Badge>
                          <div className="space-y-1 flex-1 min-w-0">
                            <p className="text-xs text-foreground leading-relaxed">
                              {test.description}
                            </p>
                            {test.files.length > 0 && (
                              <div className="flex flex-wrap gap-1.5 pt-0.5">
                                {test.files.map((tf, i) => (
                                  <code key={i} className="text-[11px] font-mono text-emerald-400/90 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                                    {tf}
                                  </code>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 7. Documentation Plan */}
                {guide.documentation_plan.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-border/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                      <FileText className="h-4 w-4 text-primary" />
                      <span>7. Documentation Updates</span>
                    </div>
                    <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground">
                      {guide.documentation_plan.map((doc, idx) => (
                        <li key={idx} className="leading-relaxed">{doc}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 8. Pull Request Pre-Flight Checklist */}
                {guide.pull_request_checklist.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-bold text-foreground uppercase tracking-wider">
                        <ListChecks className="h-4 w-4 text-primary" />
                        <span>8. Pull Request Pre-Flight Checklist</span>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        {Object.values(completedChecklist).filter(Boolean).length} / {guide.pull_request_checklist.length} completed
                      </span>
                    </div>
                    <div className="space-y-2">
                      {guide.pull_request_checklist.map((item, idx) => {
                        const isDone = !!completedChecklist[idx];
                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => toggleChecklistItem(idx)}
                            className={`w-full text-left p-3 rounded-lg border transition-all flex items-start gap-3 ${
                              isDone
                                ? "bg-emerald-500/10 border-emerald-500/30 text-foreground"
                                : "bg-card border-border/60 hover:border-primary/40 text-muted-foreground"
                            }`}
                          >
                            {isDone ? (
                              <CheckSquare className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                            ) : (
                              <Square className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                            )}
                            <span className={`text-xs leading-relaxed ${isDone ? "line-through opacity-80" : ""}`}>
                              {item}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 9. Learning Opportunities */}
                {guide.learning_opportunities.length > 0 && (
                  <div className="space-y-2.5 pt-2 border-t border-border/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                      <GraduationCap className="h-4 w-4" />
                      <span>9. Contributor Learning Opportunities</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {guide.learning_opportunities.map((opp, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs text-muted-foreground leading-relaxed flex items-start gap-2"
                        >
                          <Sparkles className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                          <span>{opp}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 10. Uncertainties & Caveats */}
                {guide.uncertainties.length > 0 && (
                  <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-600 dark:text-amber-400">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Uncertainties & Missing Context</span>
                    </div>
                    <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground">
                      {guide.uncertainties.map((u, idx) => (
                        <li key={idx} className="leading-relaxed">{u}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 11. Collapsible Verified Repository Evidence */}
                {guideData.sources.length > 0 && (
                  <div className="border border-border/60 rounded-lg overflow-hidden pt-1">
                    <button
                      type="button"
                      onClick={() => setShowEvidence(!showEvidence)}
                      className="w-full flex items-center justify-between p-3.5 text-xs font-semibold text-foreground bg-secondary/30 hover:bg-secondary/50 transition-colors text-left"
                    >
                      <div className="flex items-center space-x-2">
                        <ShieldCheck className="h-4 w-4 text-emerald-400" />
                        <span>Verified Repository Chunks Backing This Guide ({guideData.sources.length})</span>
                      </div>
                      {showEvidence ? (
                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                    </button>

                    {showEvidence && (
                      <div className="p-4 bg-secondary/10 border-t border-border/60 space-y-3">
                        {guideData.sources.map((src, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded bg-card border border-border/60 space-y-1.5 font-mono text-xs"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                              <span className="font-bold text-primary">{src.path}</span>
                              <div className="flex items-center gap-2 text-muted-foreground">
                                {src.start_line && src.end_line && (
                                  <span>Lines {src.start_line}–{src.end_line}</span>
                                )}
                                {src.score !== null && src.score !== undefined && (
                                  <Badge variant="outline" className="text-[10px] text-emerald-400">
                                    {(src.score * 100).toFixed(1)}% match
                                  </Badge>
                                )}
                              </div>
                            </div>
                            {src.reason && (
                              <p className="text-[11px] font-sans text-muted-foreground italic">
                                {src.reason}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Fallback Static Preview (Shown when not live or before generating) */}
        {(!isLive || (!guideData && !isLoading)) && (
          <div className="space-y-6">
            <Card className="border-primary/30 bg-primary/5 overflow-hidden shadow-md">
              <CardHeader className="p-5 pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-primary font-semibold text-sm">
                    <Sparkles className="h-4 w-4" />
                    <span>How the AI Contribution Guide Works</span>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono text-primary border-primary/30">
                    Phase 11 Blueprint
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-5 pt-0 space-y-4">
                <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed">
                  When you select an issue from the backlog or recommendations above, OpenSource Copilot retrieves relevant repository chunks via pgvector, passes the issue context through our anti-hallucination prompt, and provides a structured 9-step implementation pathway verified against actual source files.
                </p>

                {availableIssues.length > 0 && isLive && (
                  <div className="pt-1 flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleSelectIssueFromList(availableIssues[0].number)}
                      className="gap-1.5 text-xs"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Generate Guide for #{availableIssues[0].number}</span>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 7-Step Timeline Preview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {demoSteps.map((step) => {
                const IconComponent = step.icon;
                return (
                  <Card
                    key={step.number}
                    className="border-border/80 bg-card/70 hover:border-primary/40 transition-colors shadow-sm relative overflow-hidden"
                  >
                    <CardHeader className="p-5 pb-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-2xl font-black text-primary/40">
                          {step.number}
                        </span>
                        <div className="h-8 w-8 rounded-md bg-secondary/80 flex items-center justify-center text-primary">
                          <IconComponent className="h-4 w-4" />
                        </div>
                      </div>
                      <CardTitle className="text-sm font-bold text-foreground">
                        {step.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-5 pt-0">
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {step.description}
                      </p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
