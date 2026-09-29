"use client";

import React, { useState } from "react";
import {
  Compass,
  Layers,
  FolderTree,
  FileCode,
  ArrowRight,
  Sparkles,
  Cpu,
  Database,
  Terminal,
  Server,
  Code2,
  Workflow,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  ExternalLink,
  BookOpen,
  Boxes,
  ShieldCheck,
  Search,
  Filter,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MermaidDiagram } from "@/components/ui/mermaid-diagram";
import {
  StructureExplainerAnalysis,
  StructureExplainerResponse,
} from "@/types";

interface StructureExplainerProps {
  explainerResponse?: StructureExplainerResponse | null;
  isLoading?: boolean;
  error?: string | null;
  isLive?: boolean;
  onRetry?: () => void;
  onSelectFile?: (filePath: string) => void;
}

// Fallback demo data for previewing offline or before user requests analysis
const DEMO_EXPLAINER: StructureExplainerAnalysis = {
  overview: {
    what_it_does:
      "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ using standard type hints.",
    main_purpose:
      "Enables developers to write fast, production-grade REST APIs with automated interactive OpenAPI documentation and strict data validation.",
    primary_technologies: ["Python", "Starlette", "Pydantic", "Uvicorn"],
    application_type: "Web Framework / API Engine",
    entry_points: ["fastapi/__init__.py", "fastapi/applications.py"],
    high_level_architecture:
      "Layered ASGI microframework built on Starlette for async routing and Pydantic for data parsing and validation, featuring a declarative dependency injection container.",
  },
  directories: [
    {
      name: "fastapi/",
      purpose: "Main application framework source code.",
      contains: "Core router implementations, dependency resolution, application lifecycle, and exception handlers.",
      important_subdirectories: ["fastapi/openapi", "fastapi/security"],
      relationship: "Main codebase tested by tests/ and exported to developers importing `fastapi`.",
      evidence: "Contains 20+ primary source modules including applications.py and routing.py",
      confidence: "high",
    },
    {
      name: "fastapi/openapi/",
      purpose: "OpenAPI specification generation.",
      contains: "Utilities and schemas for building Swagger UI, ReDoc, and JSON schema definitions.",
      important_subdirectories: [],
      relationship: "Invoked by applications.py when building interactive docs.",
      evidence: "Observed docs.py, models.py, and utils.py",
      confidence: "high",
    },
    {
      name: "tests/",
      purpose: "Automated test suites.",
      contains: "Comprehensive tests covering async endpoints, authentication scopes, dependency injection, and form data.",
      important_subdirectories: ["tests/test_tutorial"],
      relationship: "Verifies all modules inside fastapi/ against regressions.",
      evidence: "Observed 150+ pytest test files with test_*.py naming",
      confidence: "high",
    },
    {
      name: "docs/",
      purpose: "Multilingual documentation and tutorials.",
      contains: "Markdown tutorials, code examples, translated user guides, and architecture references.",
      important_subdirectories: ["docs/en", "docs/zh"],
      relationship: "Documents the features and usage patterns of the fastapi package.",
      evidence: "Observed MkDocs documentation tree and multilingual markdown guides",
      confidence: "high",
    },
    {
      name: ".github/",
      purpose: "GitHub automation and CI/CD pipelines.",
      contains: "GitHub Actions workflows for automated testing, linting, publishing, and triage automation.",
      important_subdirectories: [".github/workflows"],
      relationship: "Builds and tests the repository on every commit and pull request.",
      evidence: "Observed test.yml, lint.yml, and publish.yml",
      confidence: "high",
    },
  ],
  important_files: [
    {
      path: "pyproject.toml",
      category: "manifest",
      description: "Build system configuration, packaging metadata, and test dependencies.",
      evidence: "Defines build-system, flit packaging, and tool.pytest settings",
    },
    {
      path: "fastapi/applications.py",
      category: "entry_point",
      description: "Defines the core `FastAPI` class inheriting from Starlette, managing route mounting and lifecycle.",
      evidence: "Class FastAPI definition with middleware and router dispatching",
    },
    {
      path: "fastapi/routing.py",
      category: "routing",
      description: "Implements APIRouter, endpoint parameter validation pipelines, and response serialization.",
      evidence: "APIRouter class and request handling decorators",
    },
    {
      path: "fastapi/params.py",
      category: "core_logic",
      description: "Declarative parameter descriptors for Query, Path, Body, Header, and Depends.",
      evidence: "Parameter definitions utilized in route signatures",
    },
    {
      path: "fastapi/__init__.py",
      category: "entry_point",
      description: "Public API package entry point exporting `FastAPI`, `APIRouter`, `Depends`, and `HTTPException`.",
      evidence: "Package exports and version string",
    },
  ],
  architecture: {
    overview:
      "FastAPI operates on an asynchronous request-response cycle. An incoming HTTP request is received by the ASGI server (Uvicorn), passed into the FastAPI application class (Starlette ASGI app), evaluated by APIRouter, validated by Pydantic descriptors, and resolved via Dependency Injection before executing the user-defined view function.",
    pattern: "Layered Microframework & Dependency Injection",
    layers: ["ASGI Server (Uvicorn)", "FastAPI Application Core", "APIRouter & Parameter Validation", "Dependency Injection Container", "User View Handlers"],
    diagram_mermaid: `flowchart TD
    Client["HTTP Client / Browser"] --> ASGI["ASGI Server (Uvicorn / Hypercorn)"]
    ASGI --> App["FastAPI Application (Starlette Core)"]
    App --> Router["APIRouter & Validation Pipeline"]
    Router --> DI["Dependency Injection (Depends)"]
    DI --> Handler["User Endpoint Function"]
    Handler --> Pydantic["Pydantic Response Serialization"]
    Pydantic --> OpenAPI["Interactive Docs (Swagger / ReDoc)"]`,
  },
  flow: {
    execution_start: "Execution begins when an ASGI server (like Uvicorn) instantiates and binds to `app = FastAPI()`.",
    component_communication: "Components communicate asynchronously using ASGI callable interfaces, Python type annotations, and coroutine pipelines.",
    data_entry: "HTTP requests (headers, query params, path arguments, JSON bodies) enter through the ASGI scope.",
    data_processing: "Pydantic models inspect and validate raw payloads against endpoint type hints, auto-coercing types.",
    data_storage: "FastAPI is stateless; database sessions or external APIs are provided via declarative `Depends()` utilities.",
    result_delivery: "Returned Python dictionaries or models are serialized to JSON, wrapped in an ASGI response, and streamed back to the client.",
  },
  technology_map: {
    frontend: ["Swagger UI", "ReDoc", "HTML/JS Docs"],
    backend: ["Python", "FastAPI", "Starlette", "Pydantic", "AnyIO"],
    database: ["SQLAlchemy (Integration)", "Databases (Async)"],
    apis: ["OpenAPI 3.1", "JSON Schema", "REST"],
    ai_ml: [],
    testing: ["pytest", "pytest-asyncio", "coverage"],
    devops: ["Docker", "GitHub Actions"],
    build_tools: ["flit", "pip", "hatchling"],
  },
  where_to_start: [
    {
      step_number: 1,
      title: "1. Read Documentation & Project Overview",
      target_path: "README.md",
      guidance: "Read the overview to grasp the philosophy: developer ergonomics, speed, and automatic interactive docs.",
      why: "Gives essential domain context and explains the high-level design principles.",
    },
    {
      step_number: 2,
      title: "2. Inspect Dependencies in pyproject.toml",
      target_path: "pyproject.toml",
      guidance: "Notice that FastAPI relies directly on Starlette for web fundamentals and Pydantic for validation.",
      why: "Reveals what FastAPI builds upon versus what it implements itself.",
    },
    {
      step_number: 3,
      title: "3. Check the Public Exports in __init__.py",
      target_path: "fastapi/__init__.py",
      guidance: "Examine what symbols are exposed to end users: FastAPI, APIRouter, Depends, Query, Path.",
      why: "Helps you understand the public contract before looking at internal plumbing.",
    },
    {
      step_number: 4,
      title: "4. Study the Application Core in applications.py",
      target_path: "fastapi/applications.py",
      guidance: "Look at the `FastAPI` class constructor, route registration, and middleware pipeline.",
      why: "This is the central orchestrator connecting Starlette, OpenAPI, and routing.",
    },
    {
      step_number: 5,
      title: "5. Explore Route Handling in routing.py",
      target_path: "fastapi/routing.py",
      guidance: "Trace how route decorators convert endpoints into validated ASGI callables.",
      why: "This is where the core magic of parameter conversion and validation occurs.",
    },
    {
      step_number: 6,
      title: "6. Run and Inspect Tests in tests/",
      target_path: "tests/",
      guidance: "Run `pytest` and view test files to see how endpoints are invoked in isolated environments.",
      why: "Tests demonstrate exact expected inputs, outputs, and edge cases.",
    },
  ],
  confidence_evidence:
    "Grounded evidence compiled from repository metadata, pyproject.toml dependencies, tree inspection (45+ modules), and primary package modules.",
};

export function StructureExplainer({
  explainerResponse,
  isLoading = false,
  error,
  isLive = false,
  onRetry,
  onSelectFile,
}: StructureExplainerProps) {
  const [activeTab, setActiveTab] = useState<
    "overview" | "directories" | "files" | "architecture" | "techmap" | "onboarding"
  >("overview");
  const [fileFilter, setFileFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const data: StructureExplainerAnalysis =
    explainerResponse?.explainer || (!isLive ? DEMO_EXPLAINER : DEMO_EXPLAINER);
  const provider = explainerResponse?.provider || "ollama";
  const model = explainerResponse?.model || "llama3.2:3b";
  const stats = explainerResponse?.context_stats;

  // Filtered files
  const filteredFiles = (data.important_files || []).filter((f) => {
    const matchesFilter = fileFilter === "all" || f.category === fileFilter;
    const matchesSearch =
      searchQuery === "" ||
      f.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <section id="structure-explainer" className="py-12 border-t border-border/40 scroll-mt-16">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Compass className="h-4 w-4 text-primary" />
              <span>Understand This Repository</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
              <span>Repository Structure Explainer</span>
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-2xl">
              A beginner-friendly architectural walkthrough explaining what this codebase does, what its directories and files are responsible for, and where to start reading.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap self-start md:self-auto">
            {data.overview.application_type && (
              <Badge variant="secondary" className="text-xs font-medium border border-border">
                {data.overview.application_type}
              </Badge>
            )}

            {isLive && explainerResponse ? (
              <Badge variant="success" className="gap-1.5 text-xs font-medium">
                <Cpu className="h-3 w-3" />
                <span>AI: {provider} ({model})</span>
              </Badge>
            ) : (
              <Badge variant="warning" className="gap-1.5 text-xs font-medium">
                <Sparkles className="h-3 w-3" />
                <span>AI Demo Preview</span>
              </Badge>
            )}

            {stats && (
              <span className="text-[11px] text-muted-foreground bg-secondary/80 border border-border px-2.5 py-0.5 rounded-full font-mono">
                {stats.files_included} files • {stats.total_context_chars.toLocaleString()} chars
              </span>
            )}
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <Card className="border-border bg-card/80 p-8 text-center space-y-4 shadow-xl">
            <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary animate-pulse">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-foreground">Analyzing Repository Structure & Architecture</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Inspecting directories, manifests, RAG context snippets, and generating beginner-friendly explanations...
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
              <h3 className="text-lg font-semibold text-foreground">Structure Explainer Provider Notice</h3>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            {onRetry && (
              <Button onClick={onRetry} size="sm" className="gap-2 text-xs">
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Retry Structure Explainer</span>
              </Button>
            )}
          </Card>
        )}

        {/* Main Interactive Dashboard Card */}
        {!isLoading && data && (
          <Card className="border-border bg-card/80 backdrop-blur shadow-xl overflow-hidden">
            {/* Tab Navigation */}
            <CardHeader className="border-b border-border/40 p-3 sm:p-4 bg-secondary/15">
              <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 sm:pb-0">
                <Button
                  variant={activeTab === "overview" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("overview")}
                  className="gap-2 text-xs whitespace-nowrap"
                >
                  <BookOpen className="h-3.5 w-3.5" />
                  <span>Overview & Architecture</span>
                </Button>

                <Button
                  variant={activeTab === "directories" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("directories")}
                  className="gap-2 text-xs whitespace-nowrap"
                >
                  <FolderTree className="h-3.5 w-3.5" />
                  <span>Directory Explorer ({data.directories?.length || 0})</span>
                </Button>

                <Button
                  variant={activeTab === "files" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("files")}
                  className="gap-2 text-xs whitespace-nowrap"
                >
                  <FileCode className="h-3.5 w-3.5" />
                  <span>Important Files & Flow</span>
                </Button>

                <Button
                  variant={activeTab === "techmap" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("techmap")}
                  className="gap-2 text-xs whitespace-nowrap"
                >
                  <Boxes className="h-3.5 w-3.5" />
                  <span>Technology Map</span>
                </Button>

                <Button
                  variant={activeTab === "onboarding" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveTab("onboarding")}
                  className="gap-2 text-xs whitespace-nowrap"
                >
                  <Workflow className="h-3.5 w-3.5" />
                  <span>Where Should I Start?</span>
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-5 sm:p-7 space-y-7">
              {/* TAB 1: OVERVIEW & ARCHITECTURE */}
              {activeTab === "overview" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  {/* High Level Overview Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-primary" />
                        <span>What The Project Does</span>
                      </span>
                      <p className="text-sm text-foreground/95 leading-relaxed">
                        {data.overview.what_it_does}
                      </p>
                    </div>

                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Main Purpose & Target Audience</span>
                      </span>
                      <p className="text-sm text-foreground/95 leading-relaxed">
                        {data.overview.main_purpose}
                      </p>
                    </div>
                  </div>

                  {/* App Classification & Entry Points */}
                  <div className="p-4 rounded-xl bg-secondary/20 border border-border/60 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4 text-primary" />
                        <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                          Application Type & Primary Technologies
                        </span>
                      </div>
                      <Badge variant="outline" className="font-mono text-xs">
                        {data.overview.application_type}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-2 pt-1">
                      {data.overview.primary_technologies.map((tech) => (
                        <span
                          key={tech}
                          className="px-2.5 py-1 text-xs font-mono rounded-md bg-secondary text-foreground border border-border"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>

                    {data.overview.entry_points.length > 0 && (
                      <div className="pt-2 border-t border-border/40">
                        <span className="text-xs text-muted-foreground font-semibold">Important Entry Points: </span>
                        <div className="inline-flex flex-wrap gap-1.5 ml-1">
                          {data.overview.entry_points.map((ep) => (
                            <code
                              key={ep}
                              onClick={() => onSelectFile && onSelectFile(ep)}
                              className="text-xs font-mono bg-primary/10 text-primary px-2 py-0.5 rounded cursor-pointer hover:underline"
                            >
                              {ep}
                            </code>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Architecture Explanation & Mermaid Diagram */}
                  <div className="space-y-4 pt-3 border-t border-border/40">
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Layers className="h-4 w-4 text-primary" />
                        <span>High-Level Architecture Pattern ({data.architecture.pattern})</span>
                      </h4>
                      <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-line">
                        {data.architecture.overview}
                      </p>
                    </div>

                    {/* Mermaid Diagram */}
                    {data.architecture.diagram_mermaid && (
                      <div className="mt-4">
                        <MermaidDiagram
                          chart={data.architecture.diagram_mermaid}
                          title={`${data.overview.application_type} Architecture Diagram`}
                        />
                      </div>
                    )}

                    {/* Architecture Layers */}
                    {data.architecture.layers && data.architecture.layers.length > 0 && (
                      <div className="p-3.5 rounded-lg bg-secondary/30 border border-border/60">
                        <span className="text-xs font-semibold text-muted-foreground block mb-2">
                          Identified Architectural Layers:
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {data.architecture.layers.map((layer, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-md bg-secondary text-foreground border border-border/70"
                            >
                              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                              <span>{layer}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: DIRECTORY EXPLORER */}
              {activeTab === "directories" && (
                <div className="space-y-5 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                        <FolderTree className="h-4 w-4 text-primary" />
                        <span>Directory Explorer</span>
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Detailed breakdown of top-level directories, their contents, responsibilities, and relationships.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {data.directories.map((dir, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-secondary/25 hover:bg-secondary/40 border border-border/70 space-y-3 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 font-mono text-sm font-bold text-primary">
                            <FolderTree className="h-4 w-4 text-primary shrink-0" />
                            <span>{dir.name}</span>
                          </div>
                          <Badge
                            variant={dir.confidence === "high" ? "success" : dir.confidence === "uncertain" ? "warning" : "info"}
                            className="text-[10px] uppercase font-mono"
                          >
                            {dir.confidence}
                          </Badge>
                        </div>

                        <div className="space-y-1.5 text-xs">
                          <div>
                            <span className="font-semibold text-foreground">Purpose: </span>
                            <span className="text-muted-foreground">{dir.purpose}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-foreground">Contains: </span>
                            <span className="text-muted-foreground">{dir.contains}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-foreground">Related to: </span>
                            <span className="text-muted-foreground">{dir.relationship}</span>
                          </div>
                        </div>

                        {dir.important_subdirectories && dir.important_subdirectories.length > 0 && (
                          <div className="pt-2 border-t border-border/40 flex flex-wrap gap-1 items-center">
                            <span className="text-[11px] text-muted-foreground font-semibold">Subdirectories: </span>
                            {dir.important_subdirectories.map((subdir) => (
                              <code
                                key={subdir}
                                className="text-[11px] font-mono bg-secondary px-1.5 py-0.5 rounded text-foreground/80 border border-border/40"
                              >
                                {subdir}
                              </code>
                            ))}
                          </div>
                        )}

                        {dir.evidence && (
                          <div className="text-[11px] font-mono text-muted-foreground/75 truncate pt-1">
                            Evidence: {dir.evidence}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: IMPORTANT FILES & FLOW */}
              {activeTab === "files" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  {/* Repository Execution & Data Flow Walkthrough */}
                  <div className="p-5 rounded-xl bg-secondary/30 border border-border/70 space-y-4">
                    <div className="flex items-center gap-2 font-bold text-sm text-foreground">
                      <Workflow className="h-4 w-4 text-primary" />
                      <span>Repository Flow & Execution Lifecycle</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      <div className="p-3 rounded-lg bg-card border border-border/60 space-y-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-primary flex items-center gap-1">
                          <Terminal className="h-3 w-3" />
                          <span>1. Execution Starts</span>
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {data.flow.execution_start}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-card border border-border/60 space-y-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-blue-500 flex items-center gap-1">
                          <ArrowRight className="h-3 w-3" />
                          <span>2. Data Entry</span>
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {data.flow.data_entry}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-card border border-border/60 space-y-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-500 flex items-center gap-1">
                          <Code2 className="h-3 w-3" />
                          <span>3. Component Communication</span>
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {data.flow.component_communication}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-card border border-border/60 space-y-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-amber-500 flex items-center gap-1">
                          <Cpu className="h-3 w-3" />
                          <span>4. Data Processing</span>
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {data.flow.data_processing}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-card border border-border/60 space-y-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-purple-500 flex items-center gap-1">
                          <Database className="h-3 w-3" />
                          <span>5. State & Storage</span>
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {data.flow.data_storage}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-card border border-border/60 space-y-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-500 flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>6. Result Delivery</span>
                        </span>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {data.flow.result_delivery}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Architecturally Significant Files */}
                  <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                          <FileCode className="h-4 w-4 text-primary" />
                          <span>Important Repository Files ({data.important_files.length})</span>
                        </h4>
                        <p className="text-xs text-muted-foreground">
                          Key manifests, entrypoints, routing modules, and deployment configs.
                        </p>
                      </div>

                      {/* Filter Badges */}
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {["all", "manifest", "entry_point", "routing", "config", "test", "devops"].map((cat) => (
                          <button
                            key={cat}
                            onClick={() => setFileFilter(cat)}
                            className={`px-2.5 py-1 text-[11px] rounded-md transition-colors capitalize ${
                              fileFilter === cat
                                ? "bg-primary text-primary-foreground font-semibold"
                                : "bg-secondary text-muted-foreground hover:text-foreground"
                            }`}
                          >
                            {cat.replace("_", " ")}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      {filteredFiles.map((file, idx) => (
                        <div
                          key={idx}
                          onClick={() => onSelectFile && onSelectFile(file.path)}
                          className="p-3.5 rounded-lg bg-secondary/25 hover:bg-secondary/50 border border-border/70 transition-colors cursor-pointer space-y-1.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-semibold text-primary truncate">
                              {file.path}
                            </span>
                            <Badge variant="outline" className="text-[10px] uppercase font-mono shrink-0">
                              {file.category.replace("_", " ")}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {file.description}
                          </p>
                          {file.evidence && (
                            <p className="text-[10px] font-mono text-muted-foreground/70 truncate">
                              Evidence: {file.evidence}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: TECHNOLOGY MAP */}
              {activeTab === "techmap" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  <div>
                    <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                      <Boxes className="h-4 w-4 text-primary" />
                      <span>Categorized Technology Map</span>
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Technologies, frameworks, databases, and tooling detected in this repository.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Frontend */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Code2 className="h-3.5 w-3.5 text-blue-500" />
                        <span>Frontend ({data.technology_map.frontend?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.frontend && data.technology_map.frontend.length > 0 ? (
                          data.technology_map.frontend.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* Backend */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Server className="h-3.5 w-3.5 text-emerald-500" />
                        <span>Backend ({data.technology_map.backend?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.backend && data.technology_map.backend.length > 0 ? (
                          data.technology_map.backend.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* Database */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Database className="h-3.5 w-3.5 text-purple-500" />
                        <span>Database ({data.technology_map.database?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.database && data.technology_map.database.length > 0 ? (
                          data.technology_map.database.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* APIs */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Workflow className="h-3.5 w-3.5 text-indigo-500" />
                        <span>APIs ({data.technology_map.apis?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.apis && data.technology_map.apis.length > 0 ? (
                          data.technology_map.apis.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* AI / ML */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-pink-500" />
                        <span>AI / ML ({data.technology_map.ai_ml?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.ai_ml && data.technology_map.ai_ml.length > 0 ? (
                          data.technology_map.ai_ml.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* Testing */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
                        <span>Testing ({data.technology_map.testing?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.testing && data.technology_map.testing.length > 0 ? (
                          data.technology_map.testing.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* DevOps */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Terminal className="h-3.5 w-3.5 text-cyan-500" />
                        <span>DevOps ({data.technology_map.devops?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.devops && data.technology_map.devops.length > 0 ? (
                          data.technology_map.devops.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>

                    {/* Build Tools */}
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/60 space-y-2">
                      <span className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Boxes className="h-3.5 w-3.5 text-orange-500" />
                        <span>Build Tools ({data.technology_map.build_tools?.length || 0})</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.technology_map.build_tools && data.technology_map.build_tools.length > 0 ? (
                          data.technology_map.build_tools.map((t) => (
                            <span key={t} className="px-2 py-0.5 text-xs rounded bg-secondary text-foreground font-mono">
                              {t}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground italic">None detected</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 5: ONBOARDING / WHERE SHOULD I START? */}
              {activeTab === "onboarding" && (
                <div className="space-y-6 animate-in fade-in duration-200">
                  <div>
                    <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                      <Workflow className="h-4 w-4 text-primary" />
                      <span>Where Should I Start? (Beginner Exploration Order)</span>
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Recommended chronological order for reading and understanding this specific repository.
                    </p>
                  </div>

                  <div className="space-y-3.5">
                    {data.where_to_start.map((step) => (
                      <div
                        key={step.step_number}
                        className="p-4 rounded-xl bg-secondary/30 border border-border/70 flex flex-col sm:flex-row sm:items-start gap-4"
                      >
                        <div className="h-8 w-8 rounded-full bg-primary/10 text-primary font-bold text-sm flex items-center justify-center shrink-0">
                          {step.step_number}
                        </div>

                        <div className="space-y-1.5 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h4 className="text-sm font-bold text-foreground">{step.title}</h4>
                            {step.target_path && (
                              <code
                                onClick={() => onSelectFile && onSelectFile(step.target_path!)}
                                className="text-xs font-mono bg-secondary px-2 py-0.5 rounded text-primary cursor-pointer hover:underline border border-border/40"
                              >
                                {step.target_path}
                              </code>
                            )}
                          </div>
                          <p className="text-xs text-foreground/90 leading-relaxed">
                            {step.guidance}
                          </p>
                          <p className="text-xs text-muted-foreground italic">
                            <span className="font-semibold not-italic text-muted-foreground/80">Why start here: </span>
                            {step.why}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Confidence and Evidence Ledger */}
                  <div className="p-4 rounded-xl bg-secondary/20 border border-border/60 space-y-2 mt-4">
                    <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                      <span>Evidence & Confidence Assessment</span>
                    </span>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {data.confidence_evidence}
                    </p>
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
