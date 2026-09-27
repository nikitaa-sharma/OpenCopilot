"use client";

import { AlertTriangle, Lock, SearchX, Clock, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorType } from "@/types";

interface ErrorDisplayProps {
  type: ErrorType;
  customMessage?: string;
  customHint?: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ type, customMessage, customHint, onRetry }: ErrorDisplayProps) {
  const errorConfigs = {
    invalid_url: {
      icon: AlertTriangle,
      title: "Invalid Repository URL",
      message: "Please enter a valid GitHub repository URL.",
      hint: "Format should be https://github.com/owner/repository",
    },
    private_repo: {
      icon: Lock,
      title: "Private Repository",
      message: "This repository may be private or inaccessible.",
      hint: "OpenSource Copilot currently analyzes public repositories only.",
    },
    not_found: {
      icon: SearchX,
      title: "Repository Not Found",
      message: "We couldn't find this GitHub repository.",
      hint: "Please check for typos in the owner or repository name.",
    },
    rate_limit: {
      icon: Clock,
      title: "Rate Limit Exceeded",
      message: "GitHub API rate limit reached. Please try again later.",
      hint: "Public unauthenticated requests are rate-limited by GitHub.",
    },
  };

  const config = errorConfigs[type] || errorConfigs.invalid_url;
  const IconComponent = config.icon;

  return (
    <div className="container mx-auto max-w-xl px-4 py-8 animate-in fade-in duration-300">
      <Card className="border-border bg-card/90 shadow-xl overflow-hidden text-center p-6 sm:p-8">
        <CardContent className="p-0 space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-destructive/10 text-destructive dark:text-rose-400 flex items-center justify-center">
            <IconComponent className="h-6 w-6" />
          </div>

          <div>
            <h3 className="text-lg font-semibold text-foreground">{config.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{customMessage || config.message}</p>
            <p className="mt-1 text-xs text-muted-foreground/70 font-mono">{customHint || config.hint}</p>
          </div>

          <div className="pt-2 flex justify-center">
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="gap-2 text-xs"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Try Another Repository</span>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
