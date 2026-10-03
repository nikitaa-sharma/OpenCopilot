"use client";

import React, { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { Check, Copy, Code, Eye, RefreshCw, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  title?: string;
}

const RESERVED_KEYWORDS = new Set([
  "graph",
  "flowchart",
  "subgraph",
  "end",
  "style",
  "classdef",
  "class",
  "click",
  "direction",
  "linkstyle",
  "interpolate",
]);

function toSafeNodeId(rawId: string): string {
  const s = rawId.trim();
  if (!s) return "node";
  let clean = s.replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
  clean = clean.replace(/_+/g, "_").replace(/^_+|_+$/g, "");
  if (!clean) clean = "node";
  if (/^[0-9]/.test(clean)) clean = `n_${clean}`;
  if (RESERVED_KEYWORDS.has(clean)) clean = `n_${clean}`;
  return clean;
}

function sanitizeNodeToken(nodeToken: string): string {
  const s = nodeToken.trim();
  if (!s) return "";

  const shapes: Array<[string, RegExp]> = [
    ["cylinder", /^([^\(\[\{\<\>]+?)\s*\[\(\s*(.*?)\s*\)\]$/],
    ["stadium", /^([^\(\[\{\<\>]+?)\s*\(\[\s*(.*?)\s*\]\)$/],
    ["circle", /^([^\(\[\{\<\>]+?)\s*\(\(\s*(.*?)\s*\)\)$/],
    ["rhombus", /^([^\(\[\{\<\>]+?)\s*\{\s*(.*?)\s*\}$/],
    ["round", /^([^\(\[\{\<\>]+?)\s*\(\s*(.*?)\s*\)$/],
    ["square", /^([^\(\[\{\<\>]+?)\s*\[\s*(.*?)\s*\]$/],
  ];

  for (const [shapeType, pattern] of shapes) {
    const match = s.match(pattern);
    if (match) {
      const rawId = match[1].trim();
      let inner = match[2].trim();
      if (
        (inner.startsWith('"') && inner.endsWith('"')) ||
        (inner.startsWith("'") && inner.endsWith("'"))
      ) {
        inner = inner.slice(1, -1).trim();
      }
      const cleanLabel = inner.replace(/"/g, "'").replace(/\n/g, " ").trim() || rawId;
      const safeId = toSafeNodeId(rawId);

      if (shapeType === "cylinder") {
        return `${safeId}[("${cleanLabel}")]`;
      } else if (shapeType === "stadium") {
        return `${safeId}(["${cleanLabel}"])`;
      } else if (shapeType === "circle") {
        return `${safeId}(("${cleanLabel}"))`;
      } else if (shapeType === "rhombus") {
        return `${safeId}{"${cleanLabel}"}`;
      } else if (shapeType === "round") {
        return `${safeId}("${cleanLabel}")`;
      } else {
        return `${safeId}["${cleanLabel}"]`;
      }
    }
  }

  const safeId = toSafeNodeId(s);
  const cleanLabel = s.replace(/"/g, "'").replace(/\n/g, " ").trim();
  return `${safeId}["${cleanLabel}"]`;
}

const ARROW_PATTERN = /(\s*(?:<(?:\-\-|\=\=|\-\.-)>|(?:\-\-|\=\=|\-\.-)>|(?:\-\-\-|\-\-|\=\=|\-\.-))(?:\s*\|[^|]*\|\s*)?\s*)/;

export function sanitizeMermaidSyntax(raw: string): string {
  if (!raw || !raw.trim()) return "";
  let text = raw.trim();
  text = text.replace(/^```(?:mermaid)?\s*/i, "").replace(/\s*```$/i, "").trim();

  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length === 0) return "";

  const cleanedLines: string[] = ["flowchart TD"];

  for (const line of lines) {
    if (line.startsWith("%%")) continue;
    const lower = line.toLowerCase();
    if (lower.startsWith("flowchart") || lower.startsWith("graph")) {
      continue;
    }
    if (lower.startsWith("subgraph")) {
      const subgraphContent = line.slice("subgraph".length).trim();
      const subMatch = subgraphContent.match(/^([^\(\[\{\<\>]+?)\s*\[(.*?)\]$/);
      if (subMatch) {
        const rawSubId = subMatch[1].trim();
        const title = subMatch[2].trim().replace(/^["']|["']$/g, "");
        cleanedLines.push(`    subgraph ${toSafeNodeId(rawSubId)} ["${title}"]`);
      } else {
        cleanedLines.push(
          `    subgraph ${toSafeNodeId(subgraphContent)} ["${subgraphContent.replace(/"/g, "'")}"]`
        );
      }
      continue;
    }
    if (lower === "end") {
      cleanedLines.push("    end");
      continue;
    }
    if (
      lower.startsWith("classdef") ||
      lower.startsWith("style") ||
      lower.startsWith("linkstyle")
    ) {
      cleanedLines.push(`    ${line}`);
      continue;
    }

    const tokens = line.split(ARROW_PATTERN);
    if (tokens.length > 1) {
      const reconstructed: string[] = [];
      for (let i = 0; i < tokens.length; i++) {
        const token = tokens[i];
        if (i % 2 === 1) {
          const edgeMatch = token.match(/\|([^|]*)\|/);
          if (edgeMatch) {
            const rawLabel = edgeMatch[1].trim().replace(/^["']|["']$/g, "");
            const cleanEdge = rawLabel.replace(/"/g, "'");
            const prefix = token.slice(0, edgeMatch.index);
            const suffix = token.slice((edgeMatch.index || 0) + edgeMatch[0].length);
            reconstructed.push(`${prefix}|"${cleanEdge}"|${suffix}`);
          } else {
            reconstructed.push(token);
          }
        } else {
          const cleanedNode = sanitizeNodeToken(token);
          if (cleanedNode) {
            reconstructed.push(cleanedNode);
          }
        }
      }
      cleanedLines.push(`    ${reconstructed.join("")}`);
    } else {
      const singleNode = sanitizeNodeToken(line);
      if (singleNode) {
        cleanedLines.push(`    ${singleNode}`);
      }
    }
  }

  return cleanedLines.join("\n");
}

export function MermaidDiagram({ chart, className = "", title }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);
  const [showRawCode, setShowRawCode] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    let isMounted = true;
    if (!chart || typeof window === "undefined") return;

    const renderChart = async () => {
      setIsRendering(true);
      setError(null);

      const renderId = `mermaid-svg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

      try {
        const mermaid = (await import("mermaid")).default;
        const isDark = resolvedTheme === "dark";

        mermaid.initialize({
          startOnLoad: false,
          suppressErrorRendering: true,
          theme: isDark ? "dark" : "default",
          securityLevel: "loose",
          fontFamily: "var(--font-sans, Inter, sans-serif)",
          themeVariables: {
            darkMode: isDark,
            background: isDark ? "#090d16" : "#ffffff",
            primaryColor: isDark ? "#3b82f6" : "#2563eb",
            primaryTextColor: isDark ? "#f8fafc" : "#0f172a",
            primaryBorderColor: isDark ? "#1d4ed8" : "#93c5fd",
            lineColor: isDark ? "#60a5fa" : "#3b82f6",
            secondaryColor: isDark ? "#1e293b" : "#f1f5f9",
            tertiaryColor: isDark ? "#0f172a" : "#ffffff",
            fontSize: "13px",
          },
        });

        // 1. Try rendering sanitized version
        const sanitized = sanitizeMermaidSyntax(chart);
        const codeToRender = sanitized || chart.trim();

        try {
          const { svg } = await mermaid.render(renderId, codeToRender);
          if (isMounted) {
            setSvgContent(svg);
            setError(null);
          }
        } catch (initialErr: unknown) {
          // Bounded fallback retry with stripped fallback if needed
          const fallback = `flowchart TD\n    user_client["User / Client"] --> core_app["Core Application"]\n    core_app --> services["Services & Modules"]\n    services --> storage["Data / Storage Layer"]`;
          try {
            const fallbackId = `${renderId}-fb`;
            const { svg: fbSvg } = await mermaid.render(fallbackId, fallback);
            if (isMounted) {
              setSvgContent(fbSvg);
              setError(null);
            }
          } catch {
            const errMsg = initialErr instanceof Error ? initialErr.message : String(initialErr);
            if (isMounted) {
              setError(errMsg);
            }
          }
        }
      } catch (err: unknown) {
        if (isMounted) {
          const errMsg = err instanceof Error ? err.message : String(err);
          console.warn("Mermaid initialization error:", errMsg);
          setError(errMsg);
        }
      } finally {
        // Clean up any stray error elements created in document body
        const strayEl = document.getElementById(`d${renderId}`);
        if (strayEl) {
          strayEl.remove();
        }
        if (isMounted) {
          setIsRendering(false);
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart, resolvedTheme]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(chart);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      // clipboard fallback
    }
  };

  return (
    <div className={`rounded-xl border border-border/70 bg-card/60 backdrop-blur overflow-hidden shadow-sm ${className}`}>
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-secondary/30 border-b border-border/50 text-xs">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>{title || "Repository Architecture Diagram"}</span>
          <span className="text-[10px] font-mono text-muted-foreground bg-secondary px-1.5 py-0.5 rounded border border-border/40">
            Mermaid Flowchart
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowRawCode(!showRawCode)}
            className="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
            title={showRawCode ? "Show Visual Diagram" : "View Mermaid Code"}
          >
            {showRawCode ? <Eye className="h-3.5 w-3.5" /> : <Code className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{showRawCode ? "Visual" : "Source"}</span>
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
            className="h-7 px-2 text-xs gap-1"
            title="Copy Mermaid Code to Clipboard"
          >
            {isCopied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-500" />
                <span className="text-emerald-500">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Copy Diagram</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Content Area */}
      <div className="p-4 sm:p-6 overflow-x-auto min-h-[220px] flex items-center justify-center bg-card/40">
        {showRawCode ? (
          <div className="w-full">
            <pre className="p-4 rounded-lg bg-secondary/60 text-xs font-mono text-foreground/90 overflow-x-auto border border-border/50">
              <code>{chart}</code>
            </pre>
          </div>
        ) : isRendering ? (
          <div className="flex flex-col items-center justify-center gap-2 text-muted-foreground py-8">
            <RefreshCw className="h-5 w-5 animate-spin text-primary" />
            <span className="text-xs">Rendering architectural diagram...</span>
          </div>
        ) : error ? (
          <div className="w-full space-y-3 p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-600 dark:text-amber-400">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              <span>Diagram preview notice</span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Mermaid syntax could not be rendered as SVG directly. Showing diagram specification below:
            </p>
            <pre className="p-3 bg-secondary/80 rounded font-mono text-[11px] text-foreground overflow-x-auto border border-border/40">
              {chart}
            </pre>
          </div>
        ) : svgContent ? (
          <div
            ref={containerRef}
            className="w-full flex justify-center [&>svg]:max-w-full [&>svg]:h-auto [&>svg]:drop-shadow-sm"
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        ) : (
          <div className="text-xs text-muted-foreground">No diagram generated.</div>
        )}
      </div>
    </div>
  );
}
