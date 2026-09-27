"use client";

import { useState } from "react";
import { Github, Search, Sparkles, ArrowRight, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface RepositoryInputProps {
  onAnalyze: (url: string) => void;
  isAnalyzing: boolean;
  initialUrl?: string;
}

export function RepositoryInput({
  onAnalyze,
  isAnalyzing,
  initialUrl = "",
}: RepositoryInputProps) {
  const [url, setUrl] = useState(initialUrl);
  const [inputError, setInputError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setInputError("Please enter a GitHub repository URL to proceed.");
      return;
    }
    if (!trimmed.includes("github.com/")) {
      setInputError("Please enter a valid GitHub repository URL (e.g. https://github.com/owner/repo).");
      return;
    }
    setInputError(null);
    onAnalyze(trimmed);
  };

  const handleTrySample = () => {
    const sample = "https://github.com/fastapi/fastapi";
    setUrl(sample);
    setInputError(null);
    onAnalyze(sample);
  };

  return (
    <section id="analyzer" className="relative pt-12 pb-16 md:pt-20 md:pb-24 overflow-hidden">
      {/* Subtle developer grid pattern */}
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,#1f29370f_1px,transparent_1px),linear-gradient(to_bottom,#1f29370f_1px,transparent_1px)] bg-[size:3rem_3rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />

      <div className="container mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
        {/* Badge */}
        <div className="inline-flex items-center space-x-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary mb-6 shadow-sm">
          <Sparkles className="h-3.5 w-3.5" />
          <span>AI-Powered Open Source Onboarding</span>
        </div>

        {/* Heading */}
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl max-w-4xl mx-auto leading-tight text-foreground">
          Understand. Contribute.{" "}
          <span className="bg-gradient-to-r from-blue-600 via-sky-500 to-indigo-500 dark:from-blue-400 dark:via-sky-300 dark:to-indigo-400 bg-clip-text text-transparent">
            Build Open Source.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto font-normal leading-relaxed">
          Analyze any public GitHub repository, understand its codebase, explore issues, and get AI-assisted guidance for contributing.
        </p>

        {/* Repository Input Box */}
        <div className="mt-10 max-w-2xl mx-auto">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col sm:flex-row items-center gap-2.5 p-2 rounded-xl border border-border bg-card/80 backdrop-blur shadow-xl"
          >
            <div className="relative flex-1 w-full flex items-center">
              <Github className="absolute left-3.5 h-5 w-5 text-muted-foreground" />
              <Input
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (inputError) setInputError(null);
                }}
                placeholder="https://github.com/owner/repository"
                className="pl-11 h-12 bg-background/50 border-0 focus-visible:ring-1 focus-visible:ring-primary text-sm font-mono placeholder:font-sans"
                disabled={isAnalyzing}
                aria-label="GitHub Repository URL"
              />
            </div>
            <Button
              type="submit"
              size="lg"
              disabled={isAnalyzing}
              className="w-full sm:w-auto h-12 px-6 font-semibold shadow-md gap-2 shrink-0"
            >
              <Github className="h-4 w-4" />
              <span>{isAnalyzing ? "Analyzing..." : "Analyze Repository"}</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          {/* Validation error message */}
          {inputError && (
            <p className="mt-2 text-xs text-destructive dark:text-rose-400 flex items-center justify-center gap-1">
              <XCircle className="h-3.5 w-3.5" />
              <span>{inputError}</span>
            </p>
          )}

          {/* Subtext and Sample Quick-click */}
          <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
            <span className="text-muted-foreground/80">
              Currently supports public GitHub repositories
            </span>

            <div className="flex items-center space-x-1.5">
              <span>Try:</span>
              <button
                type="button"
                onClick={handleTrySample}
                disabled={isAnalyzing}
                className="font-mono text-[11px] text-primary hover:text-primary/80 hover:underline bg-secondary/80 px-2 py-0.5 rounded border border-border transition-colors cursor-pointer"
              >
                github.com/fastapi/fastapi
              </button>
            </div>
          </div>


        </div>
      </div>
    </section>
  );
}
