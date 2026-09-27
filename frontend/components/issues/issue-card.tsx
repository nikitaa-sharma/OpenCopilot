"use client";

import { Sparkles, ExternalLink, MessageSquare, User as UserIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GitHubIssueItem, Issue } from "@/types";

interface IssueCardProps {
  issue: Issue | GitHubIssueItem;
  isLive?: boolean;
  onViewAnalysis?: (issue: Issue) => void;
  onAnalyzeAI?: (issue: GitHubIssueItem) => void;
}

export function IssueCard({ issue, isLive = false, onViewAnalysis, onAnalyzeAI }: IssueCardProps) {
  const issueNumber = "issueNumber" in issue ? issue.issueNumber : issue.number;
  const issueTitle = issue.title;
  const issueDescription =
    ("description" in issue ? issue.description : issue.body) || "No description provided.";
  const issueLabels = issue.labels || [];
  const issueState = issue.state || "open";
  const issueUrl =
    ("html_url" in issue ? issue.html_url : undefined) ||
    `https://github.com/fastapi/fastapi/issues/${issueNumber}`;
  const difficulty = "difficulty" in issue ? issue.difficulty : undefined;
  const requiredSkills = "requiredSkills" in issue ? issue.requiredSkills : undefined;
  const user = "user" in issue ? issue.user : undefined;
  const commentsCount = "comments_count" in issue ? issue.comments_count : undefined;

  const getDifficultyBadge = (diff?: string) => {
    if (!diff) return null;
    switch (diff) {
      case "Beginner":
        return <Badge variant="success">AI difficulty: Beginner</Badge>;
      case "Intermediate":
        return <Badge variant="warning">AI difficulty: Intermediate</Badge>;
      case "Advanced":
        return <Badge variant="destructive">AI difficulty: Advanced</Badge>;
      default:
        return <Badge variant="outline">AI difficulty: {diff}</Badge>;
    }
  };

  return (
    <Card className="border-border bg-card/70 hover:border-primary/50 transition-all shadow-sm flex flex-col justify-between">
      <CardHeader className="p-5 pb-3">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center space-x-2 flex-wrap">
            <span className="font-mono text-xs font-semibold text-primary">
              #{issueNumber}
            </span>
            <span className="text-[10px] text-muted-foreground uppercase font-mono bg-secondary/80 px-1.5 py-0.5 rounded border border-border">
              {issueState}
            </span>
            {isLive && user && (
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground font-mono">
                <UserIcon className="h-3 w-3" />
                <span>{user}</span>
              </span>
            )}
          </div>

          {/* Show AI difficulty only for demo data */}
          {!isLive && difficulty && getDifficultyBadge(difficulty)}

          {isLive && typeof commentsCount === "number" && commentsCount > 0 && (
            <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground font-mono">
              <MessageSquare className="h-3 w-3" />
              <span>{commentsCount}</span>
            </span>
          )}
        </div>

        <CardTitle className="text-base font-semibold text-foreground leading-snug line-clamp-2">
          {issueTitle}
        </CardTitle>

        {/* Labels */}
        {issueLabels.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-2">
            {issueLabels.slice(0, 5).map((label) => (
              <span
                key={label}
                className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                  label.toLowerCase().includes("good first") || label.toLowerCase().includes("help wanted")
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                    : label.toLowerCase().includes("bug")
                    ? "bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400"
                    : label.toLowerCase().includes("doc")
                    ? "bg-sky-500/10 border-sky-500/30 text-sky-600 dark:text-sky-400"
                    : "bg-secondary border-border text-muted-foreground"
                }`}
              >
                {label}
              </span>
            ))}
            {issueLabels.length > 5 && (
              <span className="text-[10px] text-muted-foreground self-center">
                +{issueLabels.length - 5} more
              </span>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="p-5 pt-2 space-y-4">
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
          {issueDescription}
        </p>

        {/* Required skills (Only for demo items) */}
        {!isLive && requiredSkills && requiredSkills.length > 0 && (
          <div className="space-y-1.5 pt-2 border-t border-border/40">
            <span className="text-[11px] text-muted-foreground font-medium">
              Required skills:
            </span>
            <div className="flex flex-wrap gap-1">
              {requiredSkills.map((skill) => (
                <Badge
                  key={skill}
                  variant="outline"
                  className="text-[10px] py-0 px-1.5 font-mono text-foreground/80"
                >
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="pt-2">
          {isLive ? (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAnalyzeAI && onAnalyzeAI(issue as GitHubIssueItem)}
                className="flex-1 justify-center gap-1.5 text-xs font-medium bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 hover:border-primary/40 transition-colors"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>Analyze with AI</span>
              </Button>
              <a
                href={issueUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-3 h-9 rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground text-xs font-medium transition-colors"
                title="View Issue on GitHub"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => "issueNumber" in issue && onViewAnalysis && onViewAnalysis(issue as Issue)}
              className="w-full justify-center gap-1.5 text-xs font-medium hover:bg-primary/10 hover:text-primary hover:border-primary/40 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>View AI Analysis</span>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
