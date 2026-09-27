"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export type AnalysisStageStatus = "pending" | "in_progress" | "completed";

export interface AnalysisStage {
  id: string;
  label: string;
  status: AnalysisStageStatus;
}

interface AnalysisProgressProps {
  stages: AnalysisStage[];
  repoUrl?: string;
  onCancel?: () => void;
}

export function AnalysisProgress({
  stages,
  repoUrl = "https://github.com/fastapi/fastapi",
  onCancel,
}: AnalysisProgressProps) {
  // Calculate completion percentage
  const completedCount = stages.filter((s) => s.status === "completed").length;
  const inProgressCount = stages.filter((s) => s.status === "in_progress").length;
  const progressPercent = Math.round(
    ((completedCount + inProgressCount * 0.5) / stages.length) * 100
  );

  return (
    <div className="container mx-auto max-w-2xl px-4 py-8 animate-in fade-in duration-300">
      <Card className="border-border bg-card/95 backdrop-blur shadow-2xl overflow-hidden">
        <CardHeader className="border-b border-border/40 pb-4 bg-secondary/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Loader2 className="h-5 w-5 text-primary animate-spin" />
              <div>
                <CardTitle className="text-base font-semibold">
                  Analyzing repository...
                </CardTitle>
                <p className="text-xs text-muted-foreground font-mono truncate max-w-sm mt-0.5">
                  {repoUrl}
                </p>
              </div>
            </div>
            <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
              {progressPercent}%
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          {/* Progress bar */}
          <div className="w-full bg-secondary/60 h-2 rounded-full overflow-hidden">
            <div
              className="bg-primary h-full transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Staged Checklist */}
          <div className="space-y-3.5">
            {stages.map((stage) => {
              return (
                <div
                  key={stage.id}
                  className="flex items-center space-x-3 text-sm transition-all"
                >
                  {stage.status === "completed" && (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  )}
                  {stage.status === "in_progress" && (
                    <span className="relative flex h-4 w-4 items-center justify-center shrink-0">
                      <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-primary opacity-75" />
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary" />
                    </span>
                  )}
                  {stage.status === "pending" && (
                    <Circle className="h-4 w-4 text-muted-foreground/40 shrink-0" />
                  )}

                  <span
                    className={
                      stage.status === "completed"
                        ? "text-foreground font-medium"
                        : stage.status === "in_progress"
                        ? "text-foreground font-semibold text-primary"
                        : "text-muted-foreground/60"
                    }
                  >
                    {stage.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Demonstration Notice */}
          <div className="pt-2 border-t border-border/40 flex items-center justify-between text-xs text-muted-foreground">
            <span>Demonstration State • Easily hooks into job status API</span>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="hover:text-foreground text-xs underline"
              >
                Reset
              </button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
