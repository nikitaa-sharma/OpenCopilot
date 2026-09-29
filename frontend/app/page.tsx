"use client";

import { useState } from "react";
import { RepositoryInput } from "@/components/analyzer/repository-input";
import { AnalysisProgress, AnalysisStage } from "@/components/analyzer/analysis-progress";
import { ErrorDisplay } from "@/components/analyzer/error-display";
import { EmptyState } from "@/components/analyzer/empty-state";
import { RepositoryOverview } from "@/components/repository/repository-overview";
import { AIAnalysisSection } from "@/components/repository/ai-analysis-section";
import { StructureExplainer } from "@/components/repository/structure-explainer";
import { RepositoryTree } from "@/components/repository/repository-tree";
import { TechnologyStack } from "@/components/repository/technology-stack";
import { IssuesSection } from "@/components/issues/issues-section";
import { RecommendedIssues } from "@/components/recommendations/recommended-issue-card";
import { DeveloperSkillProfileComponent } from "@/components/profile/developer-skill-profile";
import { ContributionGuide } from "@/components/contribution/contribution-guide";
import { RepositoryChat } from "@/components/chat/repository-chat";
import {
  RepositoryState,
  ErrorType,
  RepositoryAnalysisResponse,
  RepositoryAIAnalysisResponse,
  StructureExplainerResponse,
  DeveloperSkillProfile,
} from "@/types";
import {
  analyzeRepository,
  analyzeRepositoryAI,
  explainRepositoryStructure,
  ApiError,
} from "@/lib/api";


export default function HomePage() {
  const [repoState, setRepoState] = useState<RepositoryState>("idle");
  const [currentUrl, setCurrentUrl] = useState("https://github.com/fastapi/fastapi");
  const [errorType, setErrorType] = useState<ErrorType>("invalid_url");
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const [errorHint, setErrorHint] = useState<string | undefined>(undefined);

  const [analysisData, setAnalysisData] = useState<RepositoryAnalysisResponse | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Developer Skill Profile State (Phase 10)
  const [developerProfile, setDeveloperProfile] = useState<DeveloperSkillProfile | undefined>(undefined);

  // Selected Issue for AI Contribution Guide (Phase 11)
  const [selectedGuideIssueNumber, setSelectedGuideIssueNumber] = useState<number | undefined>(undefined);

  // AI Architecture Analysis State (Phase 5)
  const [aiAnalysis, setAiAnalysis] = useState<RepositoryAIAnalysisResponse | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const fetchAiAnalysis = async (url: string, branch?: string) => {
    setIsAiLoading(true);
    setAiError(null);
    try {
      const result = await analyzeRepositoryAI(url, branch);
      setAiAnalysis(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setAiError(err.message);
      } else {
        setAiError("An unexpected error occurred while communicating with the AI service.");
      }
    } finally {
      setIsAiLoading(false);
    }
  };

  // Repository Structure Explainer / Understand This Repository State
  const [structureExplainer, setStructureExplainer] = useState<StructureExplainerResponse | null>(null);
  const [isExplainerLoading, setIsExplainerLoading] = useState(false);
  const [explainerError, setExplainerError] = useState<string | null>(null);

  const fetchStructureExplainer = async (url: string, branch?: string) => {
    setIsExplainerLoading(true);
    setExplainerError(null);
    try {
      const result = await explainRepositoryStructure(url, branch);
      setStructureExplainer(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setExplainerError(err.message);
      } else {
        setExplainerError("An unexpected error occurred while generating structure explanation.");
      }
    } finally {
      setIsExplainerLoading(false);
    }
  };

  const [stages, setStages] = useState<AnalysisStage[]>([
    { id: "1", label: "Validating repository URL", status: "completed" },
    { id: "2", label: "Fetching repository metadata & stats", status: "completed" },
    { id: "3", label: "Analyzing language statistics", status: "completed" },
    { id: "4", label: "Reading README documentation", status: "completed" },
    { id: "5", label: "Retrieving open issues (filtering PRs)", status: "completed" },
  ]);

  const handleStartAnalysis = async (url: string) => {
    const trimmed = url.trim();
    if (!trimmed) return;

    setCurrentUrl(trimmed);
    setRepoState("analyzing");
    setIsDemoMode(false);
    setErrorMessage(undefined);
    setErrorHint(undefined);
    setAiAnalysis(null);
    setAiError(null);
    setStructureExplainer(null);
    setExplainerError(null);

    // Initialize staged progression
    setStages([
      { id: "1", label: "Validating repository URL", status: "in_progress" },
      { id: "2", label: "Fetching repository metadata & stats", status: "pending" },
      { id: "3", label: "Analyzing language statistics", status: "pending" },
      { id: "4", label: "Reading README documentation", status: "pending" },
      { id: "5", label: "Retrieving open issues (filtering PRs)", status: "pending" },
    ]);

    // Timers for staged UI progression
    const timer1 = setTimeout(() => {
      setStages((prev) =>
        prev.map((s, idx) =>
          idx === 0 ? { ...s, status: "completed" } : idx === 1 ? { ...s, status: "in_progress" } : s
        )
      );
    }, 250);

    const timer2 = setTimeout(() => {
      setStages((prev) =>
        prev.map((s, idx) =>
          idx <= 1 ? { ...s, status: "completed" } : idx === 2 ? { ...s, status: "in_progress" } : s
        )
      );
    }, 600);

    const timer3 = setTimeout(() => {
      setStages((prev) =>
        prev.map((s, idx) =>
          idx <= 2 ? { ...s, status: "completed" } : idx === 3 ? { ...s, status: "in_progress" } : s
        )
      );
    }, 1000);

    const timer4 = setTimeout(() => {
      setStages((prev) =>
        prev.map((s, idx) =>
          idx <= 3 ? { ...s, status: "completed" } : idx === 4 ? { ...s, status: "in_progress" } : s
        )
      );
    }, 1400);

    try {
      const data = await analyzeRepository(trimmed);

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);

      // Complete all stages
      setStages((prev) => prev.map((s) => ({ ...s, status: "completed" })));
      setAnalysisData(data);
      setRepoState("ready");

      // Trigger AI analysis and Structure Explainer
      fetchAiAnalysis(trimmed, data.repository.default_branch);
      fetchStructureExplainer(trimmed, data.repository.default_branch);
    } catch (err: unknown) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);

      if (err instanceof ApiError) {
        setErrorType(err.errorType);
        setErrorMessage(err.message);
        if (err.statusCode === 403) {
          setErrorHint("Tip: To increase rate limits, you can configure GITHUB_TOKEN in backend environment.");
        } else if (err.statusCode === 400) {
          setErrorHint("Format should be https://github.com/owner/repository");
        } else if (err.statusCode === 404) {
          setErrorHint("Please verify the repository is public and spelled correctly.");
        }
      } else {
        setErrorType("invalid_url");
        setErrorMessage("An unexpected error occurred while communicating with the server.");
      }
      setRepoState("error");
    }
  };

  const handleLoadDemoPreview = () => {
    setIsDemoMode(true);
    setAnalysisData(null);
    setAiAnalysis(null);
    setAiError(null);
    setIsAiLoading(false);
    setStructureExplainer(null);
    setExplainerError(null);
    setIsExplainerLoading(false);
    setCurrentUrl("https://github.com/fastapi/fastapi");
    setRepoState("ready");
  };




  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const isLive = !isDemoMode && analysisData !== null;

  return (
    <div className="flex flex-col min-h-screen">
      {/* 1. Hero & Repository Input */}
      <RepositoryInput
        onAnalyze={handleStartAnalysis}
        isAnalyzing={repoState === "analyzing"}
        initialUrl={currentUrl}
      />

      {/* 2. Analysis Progress State (when analyzing) */}
      {repoState === "analyzing" && (
        <AnalysisProgress
          stages={stages}
          repoUrl={currentUrl}
          onCancel={() => setRepoState("idle")}
        />
      )}

      {/* 3. Error State (when error occurs or is previewed) */}
      {repoState === "error" && (
        <ErrorDisplay
          type={errorType}
          customMessage={errorMessage}
          customHint={errorHint}
          onRetry={() => setRepoState("idle")}
        />
      )}

      {/* 4. Empty State (when idle and no repo selected) */}
      {repoState === "idle" && (
        <EmptyState
          onLoadDemo={handleLoadDemoPreview}
          onScrollToTop={() => scrollToSection("analyzer")}
        />
      )}

      {/* 5. Complete Product Dashboard (when ready / loaded) */}
      {repoState === "ready" && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Repository Overview Dashboard */}
          <RepositoryOverview
            repository={analysisData?.repository}
            isLive={isLive}
            onScrollToIssues={() => scrollToSection("issues")}
          />

          {/* AI Architecture Understanding & Grounded Analysis (Phase 5) */}
          <AIAnalysisSection
            analysisResponse={aiAnalysis}
            isLoading={isAiLoading}
            error={aiError}
            isLive={isLive}
            onRetry={() => {
              if (analysisData?.repository) {
                fetchAiAnalysis(currentUrl, analysisData.repository.default_branch);
              }
            }}
            onSelectFile={(filePath) => {
              scrollToSection("structure");
            }}
          />

          {/* Repository Structure Explainer / Understand This Repository */}
          <StructureExplainer
            explainerResponse={structureExplainer}
            isLoading={isExplainerLoading}
            error={explainerError}
            isLive={isLive}
            onRetry={() => {
              if (analysisData?.repository) {
                fetchStructureExplainer(currentUrl, analysisData.repository.default_branch);
              }
            }}
            onSelectFile={(filePath) => {
              scrollToSection("structure");
            }}
          />

          {/* Expandable Repository Tree with Live Ingestion & File Inspector */}
          <RepositoryTree
            owner={analysisData?.repository.owner}
            repo={analysisData?.repository.name}
            branch={analysisData?.repository.default_branch}
            isLive={isLive}
          />


          {/* Detected Technology Stack */}
          <TechnologyStack
            languages={analysisData?.languages}
            isLive={isLive}
          />

          {/* Issues Backlog with Filtering */}
          <IssuesSection
            issues={analysisData?.issues}
            isLive={isLive}
            repoUrl={currentUrl || (analysisData?.source ? `https://github.com/${analysisData.source.owner}/${analysisData.source.repository}` : undefined)}
            branch={analysisData?.repository?.default_branch}
            onScrollToGuide={() => scrollToSection("guide")}
          />

          {/* Developer Skill Profile Settings (Phase 10) */}
          <DeveloperSkillProfileComponent
            onProfileUpdated={(updated) => setDeveloperProfile(updated)}
          />

          {/* Personalized Skill-Matched Recommendations (Phase 10) */}
          <RecommendedIssues
            owner={analysisData?.repository.owner}
            repo={analysisData?.repository.name}
            branch={analysisData?.repository.default_branch}
            profile={developerProfile}
            isLive={isLive}
            onSelectIssue={(issueNum) => setSelectedGuideIssueNumber(issueNum)}
            onScrollToGuide={() => scrollToSection("guide")}
            onScrollToProfile={() => scrollToSection("developer-profile")}
          />

          {/* AI Contribution Guide (Phase 11 Grounded AI Guide) */}
          <ContributionGuide
            owner={analysisData?.repository.owner}
            repo={analysisData?.repository.name}
            branch={analysisData?.repository.default_branch}
            issueNumber={selectedGuideIssueNumber}
            availableIssues={analysisData?.issues}
            profile={developerProfile}
            isLive={isLive}
            onAskAiAboutIssue={() => scrollToSection("chat")}
            onSelectIssue={(num) => setSelectedGuideIssueNumber(num)}
          />

          {/* Repository AI Q&A Chat (Phase 9 Grounded RAG Chat) */}
          <RepositoryChat
            owner={analysisData?.repository.owner}
            repo={analysisData?.repository.name}
            branch={analysisData?.repository.default_branch}
            isLive={isLive}
          />
        </div>
      )}
    </div>
  );
}
