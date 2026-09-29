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

export function MermaidDiagram({ chart, className = "", title }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);
  const [showRawCode, setShowRawCode] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const { resolvedTheme } = useTheme();

  // Unique ID for mermaid render container
  const diagramId = useRef(`mermaid-${Math.random().toString(36).substring(2, 9)}`);

  useEffect(() => {
    let isMounted = true;
    if (!chart || typeof window === "undefined") return;

    const renderChart = async () => {
      setIsRendering(true);
      setError(null);

      try {
        const mermaid = (await import("mermaid")).default;
        const isDark = resolvedTheme === "dark";

        mermaid.initialize({
          startOnLoad: false,
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

        // Clean chart string
        let cleanChart = chart.trim();
        if (cleanChart.startsWith("```mermaid")) {
          cleanChart = cleanChart.replace(/^```mermaid\s*/, "").replace(/\s*```$/, "");
        } else if (cleanChart.startsWith("```")) {
          cleanChart = cleanChart.replace(/^```\s*/, "").replace(/\s*```$/, "");
        }

        const id = diagramId.current;
        const { svg } = await mermaid.render(id, cleanChart);
        if (isMounted) {
          setSvgContent(svg);
          setError(null);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const errMsg = err instanceof Error ? err.message : String(err);
          console.warn("Mermaid rendering error:", errMsg);
          setError(errMsg);
        }
      } finally {
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
      // fallback
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
