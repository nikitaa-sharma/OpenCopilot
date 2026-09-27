"use client";

import { Sparkles, CheckCircle, AlertCircle, FileCode, Clock } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Issue } from "@/types";

interface IssueAnalysisModalProps {
  issue: Issue | null;
  open: boolean;
  onClose: () => void;
  onOpenGuide?: (issue: Issue) => void;
}

export function IssueAnalysisModal({
  issue,
  open,
  onClose,
  onOpenGuide,
}: IssueAnalysisModalProps) {
  if (!issue) return null;

  const analysis = issue.analysis;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl" onClose={onClose}>
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs text-muted-foreground">
              Issue #{issue.issueNumber}
            </span>
            <Badge variant="warning" className="text-[10px]">
              AI difficulty estimate: {issue.difficulty}
            </Badge>
          </div>
          <DialogTitle className="text-lg font-bold text-foreground">
            {issue.title}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            AI-assisted contribution scope and architectural impact analysis
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Executive Summary */}
          <div className="p-4 rounded-lg bg-secondary/30 border border-border/80 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>AI Technical Summary</span>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              {analysis?.summary || issue.description}
            </p>
          </div>

          {/* Affected Components & Files */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3.5 rounded-lg border border-border bg-card/60 space-y-2">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <FileCode className="h-3.5 w-3.5 text-sky-600 dark:text-sky-400" />
                <span>Affected Components</span>
              </span>
              <ul className="space-y-1">
                {(analysis?.affectedComponents || ["fastapi/routing.py", "docs/"]).map(
                  (comp) => (
                    <li
                      key={comp}
                      className="text-xs font-mono text-muted-foreground bg-secondary/60 px-2 py-0.5 rounded"
                    >
                      {comp}
                    </li>
                  )
                )}
              </ul>
            </div>

            <div className="p-3.5 rounded-lg border border-border bg-card/60 space-y-2">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                <span>Complexity Profile</span>
              </span>
              <div className="space-y-1 text-xs text-muted-foreground">
                <p>
                  Estimated effort:{" "}
                  <span className="text-foreground font-medium">
                    {analysis?.estimatedHours || "2-4 hours"}
                  </span>
                </p>
                <p>
                  Prerequisites:{" "}
                  <span className="text-foreground font-medium">
                    Basic async testing
                  </span>
                </p>
              </div>
            </div>
          </div>

          {/* Required Skills */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-foreground">
              Required Technical Skills:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {issue.requiredSkills.map((skill) => (
                <Badge key={skill} variant="outline" className="text-xs font-mono">
                  {skill}
                </Badge>
              ))}
            </div>
          </div>

          {/* Demarcation Note */}
          <div className="p-3 rounded-md bg-secondary/20 border border-dashed border-border/60 text-[11px] text-muted-foreground">
            Demonstration preview: This analysis is an illustrative simulation. Live LLM reasoning will be activated in Phase 4.
          </div>
        </div>

        {/* Modal Actions */}
        <div className="mt-4 pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
          <a
            href={`https://github.com/fastapi/fastapi/issues/${issue.issueNumber}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:text-foreground underline"
          >
            Open Issue on GitHub
          </a>

          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={onClose} className="text-xs">
              Close
            </Button>
            {onOpenGuide && (
              <Button
                size="sm"
                onClick={() => {
                  onClose();
                  onOpenGuide(issue);
                }}
                className="text-xs"
              >
                View Contribution Guide
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
