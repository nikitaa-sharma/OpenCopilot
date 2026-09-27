"use client";

import { useState } from "react";
import {
  Sparkles,
  Cpu,
  Layers,
  FileCode,
  FolderTree,
  PlayCircle,
  TestTube,
  BookOpen,
  Info,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RepositoryAIAnalysis, RepositoryAIAnalysisResponse } from "@/types";

interface AIAnalysisSectionProps {
  analysisResponse?: RepositoryAIAnalysisResponse | null;
  isLoading?: boolean;
  error?: string | null;
  isLive?: boolean;
  onRetry?: () => void;
  onSelectFile?: (filePath: string) => void;
}

// Fallback demo data for preview when running offline or in demo mode
const DEMO_AI_ANALYSIS: RepositoryAIAnalysis = {
  summary:
    "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints and OpenAPI standards.",
  purpose:
    "Solves the challenge of building production-ready, performant REST APIs with automatic request validation, serialization, and interactive documentation with minimal boilerplate.",
  architecture:
    "Constructed on a layered architecture utilizing Starlette for high-concurrency async ASGI web routing and Pydantic for strict data validation and serialization. Features a declarative Dependency Injection system that cleanly decouples authorization, database sessions, and business logic.",
  technology_stack: [
    { name: "Python", category: "Language", evidence: "pyproject.toml, language statistics (100%)" },
    { name: "Starlette", category: "Framework", evidence: "pyproject.toml dependencies" },
    { name: "Pydantic", category: "Library", evidence: "pyproject.toml, fastapi/params.py" },
    { name: "Swagger / OpenAPI", category: "Tooling", evidence: "fastapi/openapi/docs.py" },
    { name: "pytest", category: "Testing", evidence: "pyproject.toml [tool.pytest.ini_options]" },
  ],
  important_directories: [
    {
      path: "fastapi/",
      explanation: "Core package containing router implementations, dependency resolution, and app lifecycle.",
      evidence: "Observed primary package root with 15+ submodules",
    },
    {
      path: "fastapi/openapi/",
      explanation: "Specification models and interactive documentation generation (Swagger UI and ReDoc).",
      evidence: "Contains openapi schema generation utilities",
    },
    {
      path: "tests/",
      explanation: "Comprehensive test suite covering sync/async endpoints, form data, and security scopes.",
      evidence: "Contains 100+ pytest test suites",
    },
  ],
  important_files: [
    {
      path: "fastapi/applications.py",
      reason: "Defines the core `FastAPI` application class that inherits from Starlette.",
      evidence: "Class FastAPI definition and middleware lifecycle hooks",
    },
    {
      path: "fastapi/routing.py",
      reason: "Implements APIRouter, endpoint parameter validation, and response handlers.",
      evidence: "Route decorator definitions and request validation pipeline",
    },
    {
      path: "fastapi/params.py",
      reason: "Declarative parameter descriptors for Query, Path, Body, Header, and Depends.",
      evidence: "Parameter validation classes",
    },
  ],
  entry_points: [
    {
      path: "fastapi/__init__.py",
      description: "Public API package root exporting `FastAPI`, `APIRouter`, `Depends`, `HTTPException`.",
      confidence: "high",
    },
    {
      path: "fastapi/applications.py",
      description: "Application instantiation entrypoint for ASGI servers (Uvicorn / Hypercorn).",
      confidence: "high",
    },
  ],
  testing: {
    framework: "pytest (with pytest-asyncio and coverage)",
    structure: "Centralized `tests/` directory with module-specific test files matching `test_*.py`.",
    evidence: "pyproject.toml test dependencies and directory tree structure",
  },
  beginner_explanation:
    "If you want to understand how FastAPI works internally, start by inspecting `fastapi/__init__.py` to see what is exported. Next, open `fastapi/applications.py` to see how a `FastAPI` instance is initialized. Look at `fastapi/routing.py` to understand how routes are registered and parameters are converted using Pydantic models. Run `pytest` to execute tests locally.",
  confidence_assessment:
    "High confidence: Analysis grounded in explicit definitions in `pyproject.toml`, directory structure, and core module files.",
};

export function AIAnalysisSection({
  analysisResponse,
  isLoading = false,
  error,
  isLive = false,
  onRetry,
  onSelectFile,
}: AIAnalysisSectionProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "architecture" | "structure" | "guide">("overview");

  // Use live AI response if available; otherwise use demo data if not loading/erroring
  const data: RepositoryAIAnalysis | null =
    analysisResponse?.analysis || (!isLive ? DEMO_AI_ANALYSIS : null);
  const providerName = analysisResponse?.provider || "ollama";
  const modelName = analysisResponse?.model || "llama3";
  const stats = analysisResponse?.context_stats;

  return (
    <section id="ai-analysis" className="py-12 border-t border-border/40 scroll-mt-16">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span>Grounded AI Architecture Understanding</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
              <span>AI Repository Analysis</span>
            </h2>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {isLive && analysisResponse ? (
              <Badge variant="success" className="gap-1.5 text-xs font-medium">
                <Cpu className="h-3 w-3" />
                <span>AI: {providerName} ({modelName})</span>
              </Badge>
            ) : (
              <Badge variant="warning" className="gap-1.5 text-xs font-medium">
                <Sparkles className="h-3 w-3" />
                <span>AI Demo Preview</span>
              </Badge>
            )}

            {stats && (
              <span className="text-[11px] text-muted-foreground bg-secondary/80 border border-border px-2.5 py-0.5 rounded-full font-mono">
                {stats.files_included} files indexed • {stats.total_context_chars.toLocaleString()} chars
              </span>
            )}
          </div>
        </div>

        {/* Demarcation Banner */}
        <div className="mb-6 p-3.5 rounded-lg bg-secondary/30 border border-border/70 flex items-start gap-3">
          <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
          <div className="text-xs text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground">Evidence Grounding Notice: </span>
            This architectural analysis is generated by local AI ({providerName}) using strictly grounded evidence from the repository metadata, README, file tree, and source configuration. No code execution was performed.
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <Card className="border-border bg-card/80 p-8 text-center space-y-4 shadow-xl">
            <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary animate-pulse">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-foreground">Analyzing Repository Architecture with AI</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Prioritizing files, building context budget, and querying the local AI provider...
              </p>
            </div>
          </Card>
        )}

        {/* Error / Offline State */}
        {!isLoading && error && (
          <Card className="border-border bg-card/90 p-6 sm:p-8 shadow-xl text-center space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <AlertCircle className="h-6 w-6" />
            </div>
            <div className="space-y-2 max-w-lg mx-auto">
              <h3 className="text-lg font-semibold text-foreground">Local AI Provider Offline</h3>
              <p className="text-sm text-muted-foreground">{error}</p>
              <div className="p-3 bg-secondary/80 rounded border border-border text-left font-mono text-xs text-muted-foreground">
                <p className="text-foreground font-semibold mb-1">To enable local AI analysis:</p>
                <p>1. Start Ollama: <span className="text-primary">ollama serve</span></p>
                <p>2. Download model: <span className="text-primary">ollama run {modelName}</span></p>
              </div>
            </div>
            {onRetry && (
              <Button onClick={onRetry} size="sm" className="gap-2 text-xs">
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Retry AI Analysis</span>
              </Button>
            )}
          </Card>
        )}

        {/* Main Content Card */}
        {!isLoading && !error && data && (
          <Card className="border-border bg-card/80 backdrop-blur shadow-xl overflow-hidden">
            {/* Tab Navigation */}
            <CardHeader className="border-b border-border/40 p-4 sm:p-6 bg-secondary/10">
              <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
                <Button
                  variant={activeTab === "overview" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("overview")}
                  className="gap-2 text-xs"
                >
                  <BookOpen className="h-3.5 w-3.5" />
                  <span>Overview & Purpose</span>
                </Button>

                <Button
                  variant={activeTab === "architecture" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("architecture")}
                  className="gap-2 text-xs"
                >
                  <Layers className="h-3.5 w-3.5" />
                  <span>Architecture & Stack</span>
                </Button>

                <Button
                  variant={activeTab === "structure" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("structure")}
                  className="gap-2 text-xs"
                >
                  <FolderTree className="h-3.5 w-3.5" />
                  <span>Key Files & Dirs</span>
                </Button>

                <Button
                  variant={activeTab === "guide" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("guide")}
                  className="gap-2 text-xs"
                >
                  <PlayCircle className="h-3.5 w-3.5" />
                  <span>Beginner Onboarding</span>
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-6 sm:p-8 space-y-6">
              {/* TAB 1: OVERVIEW & PURPOSE */}
              {activeTab === "overview" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      <span>Project Summary</span>
                    </h4>
                    <p className="text-base text-foreground leading-relaxed">
                      {data.summary}
                    </p>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-border/40">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                      <span>Problem Solved & Target Audience</span>
                    </h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {data.purpose}
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-secondary/30 border border-border/60 space-y-2">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Confidence & Evidence Assessment
                    </h5>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {data.confidence_assessment}
                    </p>
                  </div>
                </div>
              )}

              {/* TAB 2: ARCHITECTURE & TECH STACK */}
              {activeTab === "architecture" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-primary" />
                      <span>Architecture Overview</span>
                    </h4>
                    <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-line">
                      {data.architecture}
                    </p>
                  </div>

                  {/* Grounded Technology Stack */}
                  <div className="space-y-3 pt-4 border-t border-border/40">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Grounded Technology Stack & Evidence
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {data.technology_stack.map((tech, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-secondary/30 border border-border/60 space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-foreground">{tech.name}</span>
                            <Badge variant="info" className="text-[10px] uppercase">
                              {tech.category}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground flex items-center gap-1">
                            <span className="font-mono text-[11px] text-muted-foreground/80 truncate">
                              Evidence: {tech.evidence}
                            </span>
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Testing Structure */}
                  <div className="p-4 rounded-lg bg-secondary/20 border border-border/60 space-y-2">
                    <div className="flex items-center gap-2">
                      <TestTube className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                        Testing Suite: {data.testing.framework}
                      </h4>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {data.testing.structure}
                    </p>
                    {data.testing.evidence && (
                      <p className="text-[11px] font-mono text-muted-foreground/70">
                        Evidence: {data.testing.evidence}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 3: KEY FILES & DIRECTORIES */}
              {activeTab === "structure" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  {/* Entry Points */}
                  {data.entry_points.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <PlayCircle className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span>Identified Entry Points</span>
                      </h4>
                      <div className="space-y-2">
                        {data.entry_points.map((entry, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-secondary/30 border border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <div className="space-y-0.5">
                              <span className="font-mono text-xs font-semibold text-primary">
                                {entry.path}
                              </span>
                              <p className="text-xs text-muted-foreground">{entry.description}</p>
                            </div>
                            <Badge
                              variant={entry.confidence === "high" ? "success" : "info"}
                              className="self-start sm:self-auto text-[10px] uppercase font-mono"
                            >
                              {entry.confidence} confidence
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Important Files */}
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <FileCode className="h-3.5 w-3.5 text-primary" />
                      <span>Architecturally Significant Files</span>
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {data.important_files.map((file, idx) => (
                        <div
                          key={idx}
                          onClick={() => onSelectFile && onSelectFile(file.path)}
                          className="p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 border border-border/60 transition-colors cursor-pointer space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-xs font-semibold text-primary truncate">
                              {file.path}
                            </span>
                            <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0" />
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">{file.reason}</p>
                          {file.evidence && (
                            <p className="text-[10px] font-mono text-muted-foreground/70 truncate">
                              {file.evidence}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Important Directories */}
                  <div className="space-y-3 pt-2 border-t border-border/40">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <FolderTree className="h-3.5 w-3.5 text-primary" />
                      <span>Important Directories</span>
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {data.important_directories.map((dir, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-secondary/30 border border-border/60 space-y-1.5"
                        >
                          <span className="font-mono text-xs font-semibold text-foreground">
                            {dir.path}
                          </span>
                          <p className="text-xs text-muted-foreground leading-relaxed">{dir.explanation}</p>
                          {dir.evidence && (
                            <p className="text-[10px] font-mono text-muted-foreground/70 truncate">
                              {dir.evidence}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: BEGINNER ONBOARDING GUIDE */}
              {activeTab === "guide" && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-primary" />
                    <h4 className="text-sm font-semibold text-foreground">
                      Contributor Onboarding & Codebase Reading Guide
                    </h4>
                  </div>
                  <div className="p-4 rounded-lg bg-secondary/25 border border-border/60 text-sm text-foreground/90 leading-relaxed whitespace-pre-line">
                    {data.beginner_explanation}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </section>
  );
}
