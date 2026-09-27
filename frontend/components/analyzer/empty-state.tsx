"use client";

import { GitPullRequest, Search, Sparkles, ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  onLoadDemo: () => void;
  onScrollToTop: () => void;
}

export function EmptyState({ onLoadDemo, onScrollToTop }: EmptyStateProps) {
  return (
    <section className="py-16 border-t border-border/40">
      <div className="container mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
        <Card className="border-dashed border-border/80 bg-card/40 p-8 sm:p-12 shadow-lg">
          <CardContent className="p-0 space-y-5">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <GitPullRequest className="h-7 w-7" />
            </div>

            <div className="space-y-2 max-w-lg mx-auto">
              <h3 className="text-xl font-bold text-foreground">
                Analyze a repository to get started.
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Enter a public GitHub repository URL above and OpenSource Copilot will prepare the project overview, issues, and AI insights.
              </p>
            </div>

            <div className="pt-3 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={onScrollToTop}
                className="gap-2 text-xs"
              >
                <ArrowUp className="h-3.5 w-3.5" />
                <span>Enter Repository URL</span>
              </Button>

              <Button
                size="sm"
                onClick={onLoadDemo}
                className="gap-2 text-xs font-semibold shadow-sm"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>Try Sample Repository</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
