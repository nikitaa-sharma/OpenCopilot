"use client";

import { Cpu, Terminal, ShieldCheck, Box, CheckCircle, Code2, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TechnologyItem } from "@/types";

interface TechnologyStackProps {
  languages?: Record<string, number>;
  isLive?: boolean;
  technologies?: TechnologyItem[];
}

const DEFAULT_TECHNOLOGIES: TechnologyItem[] = [
  {
    name: "Python",
    role: "Core Language",
    category: "Language",
    description: "Modern asynchronous Python 3.8+ with standard typing support.",
    iconName: "terminal",
  },
  {
    name: "FastAPI",
    role: "Web Framework",
    category: "Framework",
    description: "High-performance API framework on ASGI standard with OpenAPI documentation.",
    iconName: "cpu",
  },
  {
    name: "Pydantic",
    role: "Data Validation",
    category: "Library",
    description: "Schema enforcement, serialization, and type-hint validation engine.",
    iconName: "shield",
  },
  {
    name: "Starlette",
    role: "ASGI Toolkit",
    category: "Framework",
    description: "Lightweight ASGI framework providing core HTTP request and response primitives.",
    iconName: "box",
  },
  {
    name: "Pytest",
    role: "Testing Suite",
    category: "Testing",
    description: "Test execution runner, async fixtures, and regression coverage automation.",
    iconName: "check",
  },
];

const LANGUAGE_COLORS: Record<string, string> = {
  python: "bg-blue-500",
  javascript: "bg-amber-400",
  typescript: "bg-sky-500",
  html: "bg-orange-500",
  css: "bg-indigo-500",
  rust: "bg-amber-600",
  go: "bg-cyan-500",
  java: "bg-red-500",
  c: "bg-neutral-500",
  "c++": "bg-pink-500",
  ruby: "bg-red-600",
  php: "bg-violet-500",
  shell: "bg-emerald-500",
};

export function TechnologyStack({
  languages,
  isLive = false,
  technologies = DEFAULT_TECHNOLOGIES,
}: TechnologyStackProps) {
  const getIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case "python":
        return <Terminal className="h-5 w-5 text-amber-600 dark:text-amber-400" />;
      case "fastapi":
        return <Cpu className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />;
      case "pydantic":
        return <ShieldCheck className="h-5 w-5 text-rose-600 dark:text-rose-400" />;
      case "starlette":
        return <Box className="h-5 w-5 text-sky-600 dark:text-sky-400" />;
      case "pytest":
        return <CheckCircle className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />;
      default:
        return <Code2 className="h-5 w-5 text-primary" />;
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1024 * 1024) {
      return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }
    if (bytes >= 1024) {
      return (bytes / 1024).toFixed(1) + " KB";
    }
    return bytes + " B";
  };

  const hasLiveLanguages = isLive && languages && Object.keys(languages).length > 0;

  // Calculate live language percentages from byte counts
  const totalBytes = hasLiveLanguages
    ? Object.values(languages).reduce((sum, count) => sum + count, 0)
    : 0;

  const liveLanguageList = hasLiveLanguages
    ? Object.entries(languages)
        .sort(([, a], [, b]) => b - a)
        .map(([lang, bytes]) => {
          const percent = totalBytes > 0 ? (bytes / totalBytes) * 100 : 0;
          return {
            name: lang,
            bytes,
            percentage: percent.toFixed(1),
            colorClass: LANGUAGE_COLORS[lang.toLowerCase()] || "bg-primary",
          };
        })
    : [];

  return (
    <section className="py-12 border-t border-border/40 bg-card/20">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Cpu className="h-3.5 w-3.5" />
              <span>Dependencies & Languages</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Technology Stack
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {hasLiveLanguages
                ? "Breakdown of programming languages detected by GitHub based on repository byte count."
                : "Detected frameworks, libraries, and runtime tools powering this codebase."}
            </p>
          </div>

          {hasLiveLanguages ? (
            <Badge variant="success" className="text-xs font-medium uppercase tracking-wider self-start sm:self-auto">
              Live GitHub Data
            </Badge>
          ) : (
            <Badge variant="warning" className="text-xs font-medium uppercase tracking-wider self-start sm:self-auto">
              Example Preview • Demo Data
            </Badge>
          )}
        </div>

        {/* Live Language Multi-segment Progress Bar */}
        {hasLiveLanguages && (
          <div className="mb-8 space-y-2">
            <div className="h-3 w-full rounded-full overflow-hidden flex bg-secondary/80 border border-border/60">
              {liveLanguageList.map((item) => (
                <div
                  key={item.name}
                  style={{ width: `${item.percentage}%` }}
                  className={`${item.colorClass} transition-all duration-500`}
                  title={`${item.name}: ${item.percentage}% (${formatBytes(item.bytes)})`}
                />
              ))}
            </div>

            <div className="flex flex-wrap gap-x-5 gap-y-2 pt-1 text-xs text-muted-foreground">
              {liveLanguageList.map((item) => (
                <div key={item.name} className="flex items-center gap-1.5">
                  <span className={`h-2.5 w-2.5 rounded-full ${item.colorClass}`} />
                  <span className="font-medium text-foreground">{item.name}</span>
                  <span className="font-mono text-muted-foreground">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stack Cards Grid */}
        {hasLiveLanguages ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {liveLanguageList.map((lang) => (
              <Card
                key={lang.name}
                className="border-border/80 bg-card/70 hover:border-primary/40 transition-colors shadow-sm flex flex-col justify-between"
              >
                <CardHeader className="p-5 pb-3">
                  <div className="flex items-center justify-between mb-3">
                    <div className="h-10 w-10 rounded-lg bg-secondary/80 border border-border flex items-center justify-center">
                      {getIcon(lang.name)}
                    </div>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      Language
                    </Badge>
                  </div>
                  <CardTitle className="text-base font-bold text-foreground">
                    {lang.name}
                  </CardTitle>
                  <span className="text-xs font-semibold text-primary/90 font-mono">
                    {lang.percentage}% of codebase
                  </span>
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <p className="text-xs text-muted-foreground leading-relaxed font-mono">
                    {formatBytes(lang.bytes)} source bytes
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {technologies.map((tech) => (
              <Card
                key={tech.name}
                className="border-border/80 bg-card/70 hover:border-primary/40 transition-colors shadow-sm flex flex-col justify-between"
              >
                <CardHeader className="p-5 pb-3">
                  <div className="flex items-center justify-between mb-3">
                    <div className="h-10 w-10 rounded-lg bg-secondary/80 border border-border flex items-center justify-center">
                      {getIcon(tech.name)}
                    </div>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {tech.category}
                    </Badge>
                  </div>
                  <CardTitle className="text-base font-bold text-foreground">
                    {tech.name}
                  </CardTitle>
                  <span className="text-xs font-medium text-primary/90">
                    {tech.role}
                  </span>
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {tech.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
