"use client";

import {
  Sparkles,
  ExternalLink,
  AlertTriangle,
  FileCode,
  CheckCircle2,
  HelpCircle,
  Layers,
  Wrench,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GitHubIssueItem, IssueAIAnalysisResponse } from "@/types";

interface LiveIssueAIModalProps {
  issue: GitHubIssueItem | null;
  open: boolean;
  isLoading: boolean;
  error: string | null;
  analysisResult: IssueAIAnalysisResponse | null;
  onClose: () => void;
  onRetry?: () => void;
}

export function LiveIssueAIModal({
  issue,
  open,
  isLoading,
  error,
  analysisResult,
  onClose,
  onRetry,
}: LiveIssueAIModalProps) {
  if (!issue) return null;

  const analysis = analysisResult?.analysis;

  const getDifficultyBadge = (difficulty?: string) => {
    const diff = (difficulty || "unknown").toLowerCase();
    switch (diff) {
      case "beginner":
        return (
          <Badge variant="success" className="text-xs font-mono">
            AI Estimate: Beginner
          </Badge>
        );
      case "intermediate":
        return (
          <Badge variant="warning" className="text-xs font-mono">
            AI Estimate: Intermediate
          </Badge>
        );
      case "advanced":
        return (
          <Badge variant="destructive" className="text-xs font-mono">
            AI Estimate: Advanced
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-xs font-mono">
            AI Estimate: {difficulty || "Unknown"}
          </Badge>
        );
    }
  };

  const getConfidenceBadge = (confidence?: string) => {
    const conf = (confidence || "medium").toLowerCase();
    switch (conf) {
      case "likely":
      case "high":
        return <Badge variant="success" className="text-[10px] uppercase font-mono">Likely</Badge>;
      case "possible":
      case "medium":
        return <Badge variant="warning" className="text-[10px] uppercase font-mono">Possible</Badge>;
      case "speculative":
      case "low":
        return <Badge variant="secondary" className="text-[10px] uppercase font-mono">Speculative</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px] uppercase font-mono">{conf}</Badge>;
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto" onClose={onClose}>
        <DialogHeader>
          <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-primary">
                Issue #{issue.number}
              </span>
              <span className="text-[10px] text-muted-foreground uppercase font-mono bg-secondary/80 px-1.5 py-0.5 rounded border border-border">
                {issue.state}
              </span>
              {analysisResult && (
                <span className="text-[11px] font-mono text-muted-foreground bg-primary/10 border border-primary/20 text-primary px-2 py-0.5 rounded">
                  {analysisResult.provider} ({analysisResult.model})
                </span>
              )}
            </div>

            {issue.html_url && (
              <a
                href={issue.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground font-mono transition-colors"
              >
                <span>View on GitHub</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>

          <DialogTitle className="text-lg font-bold text-foreground leading-snug">
            {issue.title}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Grounded AI analysis, candidate files, and step-by-step investigation guide
          </DialogDescription>
        </DialogHeader>

        {/* Loading State */}
        {isLoading && (
          <div className="py-12 px-4 text-center space-y-4">
            <div className="inline-flex items-center justify-center p-3 rounded-full bg-primary/10 border border-primary/20 text-primary animate-pulse">
              <Sparkles className="h-6 w-6 animate-spin" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-foreground">
                Analyzing Issue with AI...
              </h4>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto leading-relaxed">
                Extracting repository file tree, searching for keyword matches, and formulating
                an evidence-grounded investigation plan.
              </p>
            </div>
            <div className="w-48 h-1.5 bg-secondary mx-auto rounded-full overflow-hidden">
              <div className="h-full bg-primary animate-pulse rounded-full w-2/3" />
            </div>
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="py-6 space-y-4">
            <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/10 space-y-2">
              <div className="flex items-center gap-2 text-destructive font-semibold text-sm">
                <AlertTriangle className="h-4 w-4" />
                <span>AI Issue Analysis Failed</span>
              </div>
              <p className="text-xs text-destructive/90 leading-relaxed font-mono">
                {error}
              </p>
              {error.toLowerCase().includes("unavailable") || error.toLowerCase().includes("ollama") ? (
                <div className="mt-3 p-3 rounded-md bg-background/80 border border-border text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground">How to resolve:</p>
                  <p>1. Start Ollama locally: <code className="bg-secondary px-1 py-0.5 rounded font-mono text-[11px]">ollama serve</code></p>
                  <p>2. Ensure the model is installed: <code className="bg-secondary px-1 py-0.5 rounded font-mono text-[11px]">ollama pull llama3</code></p>
                  <p>3. Click Retry below.</p>
                </div>
              ) : null}
            </div>

            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="gap-2 text-xs font-medium"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Retry Analysis</span>
              </Button>
            )}
          </div>
        )}

        {/* Successful Analysis Results */}
        {!isLoading && !error && analysis && (
          <div className="space-y-6 py-3">
            {/* Quick Badges Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-secondary/20 border border-border">
              <div className="space-y-1">
                <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">
                  Difficulty
                </span>
                <div>{getDifficultyBadge(analysis.difficulty)}</div>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">
                  Issue Type
                </span>
                <div>
                  <Badge variant="outline" className="text-xs uppercase font-mono capitalize">
                    {analysis.issue_type}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider">
                  Confidence
                </span>
                <div>{getConfidenceBadge(analysis.confidence)}</div>
              </div>
            </div>

            {/* AI Plain-Language Explanation */}
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                <Sparkles className="h-4 w-4 text-primary" />
                <span>AI Technical Summary</span>
              </div>
              <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed">
                {analysis.ai_explanation}
              </p>
            </div>

            {/* Difficulty & Skills Rationales */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl border border-border bg-card/60 space-y-2">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-primary" />
                  <span>Difficulty Rationale (AI Estimate)</span>
                </span>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {analysis.difficulty_rationale}
                </p>
              </div>

              <div className="p-4 rounded-xl border border-border bg-card/60 space-y-2">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Wrench className="h-3.5 w-3.5 text-primary" />
                  <span>Required Skills (AI Estimate)</span>
                </span>
                <div className="flex flex-wrap gap-1.5 mb-1.5">
                  {analysis.required_skills.map((skill) => (
                    <Badge
                      key={skill}
                      variant="outline"
                      className="text-[11px] font-mono py-0.5 px-2 bg-secondary/80"
                    >
                      {skill}
                    </Badge>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {analysis.skills_rationale}
                </p>
              </div>
            </div>

            {/* Candidate Files Requiring Verification */}
            <div className="space-y-3">
              <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 flex items-start gap-2.5">
                <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <div className="text-xs text-amber-900 dark:text-amber-200/90 leading-relaxed">
                  <strong className="text-amber-800 dark:text-amber-300 font-semibold">
                    Candidate files requiring verification — keyword match, not proof
                  </strong>
                  <p className="text-[11px] text-amber-800/80 dark:text-amber-200/70 mt-0.5">
                    These candidate files were identified by matching terms in the issue against the repository tree.
                    Always inspect and verify before assuming root cause.
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                {analysis.candidate_files.length > 0 ? (
                  analysis.candidate_files.map((cf) => (
                    <div
                      key={cf.path}
                      className="p-3 rounded-lg border border-border bg-card/80 hover:border-primary/40 transition-colors space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5 font-mono text-xs font-semibold text-primary">
                          <FileCode className="h-3.5 w-3.5 text-primary/80" />
                          <span>{cf.path}</span>
                        </div>
                        {getConfidenceBadge(cf.confidence)}
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {cf.reason}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground italic">
                    No specific candidate files could be confidently identified from the issue text.
                  </p>
                )}
              </div>
            </div>

            {/* Investigation Steps */}
            {analysis.investigation_steps.length > 0 && (
              <div className="p-4 rounded-xl border border-border bg-card/60 space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Step-by-Step Investigation Approach</span>
                </div>
                <div className="space-y-2">
                  {analysis.investigation_steps.map((step, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2.5 text-xs text-muted-foreground leading-relaxed"
                    >
                      <span className="font-mono text-[11px] font-bold text-primary px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20 shrink-0">
                        {idx + 1}
                      </span>
                      <span>{step.replace(/^\d+\.\s*/, "")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Affected Areas & Prerequisites */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {analysis.affected_areas.length > 0 && (
                <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-2">
                  <span className="text-xs font-semibold text-foreground">
                    Affected Areas / Components
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.affected_areas.map((area) => (
                      <Badge
                        key={area}
                        variant="secondary"
                        className="text-[11px] font-mono px-2 py-0.5"
                      >
                        {area}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {analysis.prerequisites && (
                <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-2">
                  <span className="text-xs font-semibold text-foreground">
                    Prerequisites & Environment
                  </span>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {analysis.prerequisites}
                  </p>
                </div>
              )}
            </div>

            {/* Evidence & Grounding Breakdown */}
            <div className="space-y-3 pt-2 border-t border-border/60">
              <span className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
                Evidence & Grounding Breakdown
              </span>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Observed Evidence */}
                <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Observed Evidence</span>
                  </div>
                  <ul className="text-[11px] text-muted-foreground space-y-1 list-disc list-inside">
                    {analysis.observed_evidence.map((obs, i) => (
                      <li key={i} className="leading-relaxed">{obs}</li>
                    ))}
                  </ul>
                </div>

                {/* Inferences */}
                <div className="p-3 rounded-lg border border-sky-500/20 bg-sky-500/5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-600 dark:text-sky-400">
                    <Layers className="h-3.5 w-3.5" />
                    <span>AI Inferences</span>
                  </div>
                  <ul className="text-[11px] text-muted-foreground space-y-1 list-disc list-inside">
                    {analysis.inferences.map((inf, i) => (
                      <li key={i} className="leading-relaxed">{inf}</li>
                    ))}
                  </ul>
                </div>

                {/* Unknowns */}
                <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
                    <HelpCircle className="h-3.5 w-3.5" />
                    <span>Unknowns to Verify</span>
                  </div>
                  <ul className="text-[11px] text-muted-foreground space-y-1 list-disc list-inside">
                    {analysis.unknowns.map((unk, i) => (
                      <li key={i} className="leading-relaxed">{unk}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Context stats footer */}
            {analysisResult.context_stats && (
              <div className="text-[11px] text-muted-foreground/80 font-mono text-center pt-2">
                Context: {analysisResult.context_stats.files_included} files sampled •{" "}
                {analysisResult.context_stats.total_context_chars.toLocaleString()} chars processed
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
