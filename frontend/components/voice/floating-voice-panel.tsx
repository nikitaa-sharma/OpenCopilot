"use client";

import React, { useEffect, useRef } from "react";
import {
  Mic,
  MicOff,
  PhoneOff,
  X,
  Sparkles,
  Bot,
  User,
  AlertCircle,
  Loader2,
  Volume2,
  FileCode,
  Radio,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { useVoiceAssistant, VoiceStatus } from "@/context/voice-assistant-context";

export function FloatingVoicePanel() {
  const {
    isOpen,
    toggleOpen,
    status,
    isMuted,
    toggleMute,
    repositoryContext,
    transcripts,
    errorMessage,
    errorType,
    audioLevel,
    startSession,
    endSession,
    clearError,
  } = useVoiceAssistant();

  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [transcripts]);

  if (!isOpen) return null;

  const repoLabel =
    repositoryContext?.owner && repositoryContext?.repo
      ? `${repositoryContext.owner}/${repositoryContext.repo}`
      : null;

  const isConnectedOrBusy =
    status === "connected" ||
    status === "listening" ||
    status === "speaking" ||
    status === "thinking";

  const getStatusBadge = (s: VoiceStatus) => {
    switch (s) {
      case "connecting":
        return (
          <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10 gap-1.5 animate-pulse">
            <Loader2 className="h-2.5 w-2.5 animate-spin" />
            Connecting
          </Badge>
        );
      case "listening":
        return (
          <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 gap-1.5 animate-pulse">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
            Listening
          </Badge>
        );
      case "speaking":
        return (
          <Badge variant="outline" className="text-primary border-primary/30 bg-primary/10 gap-1.5">
            <Radio className="h-2.5 w-2.5 animate-pulse" />
            Speaking
          </Badge>
        );
      case "thinking":
        return (
          <Badge variant="outline" className="text-indigo-400 border-indigo-500/30 bg-indigo-500/10 gap-1.5">
            <Loader2 className="h-2.5 w-2.5 animate-spin" />
            Reasoning
          </Badge>
        );
      case "connected":
        return (
          <Badge variant="outline" className="text-emerald-400 border-emerald-500/30 bg-emerald-500/10 gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Ready
          </Badge>
        );
      case "error":
        return (
          <Badge variant="outline" className="text-destructive border-destructive/30 bg-destructive/10 gap-1.5">
            <span className="h-2 w-2 rounded-full bg-destructive" />
            Error
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-muted-foreground border-border text-[11px]">
            Offline
          </Badge>
        );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Floating Voice Assistant"
      className="fixed bottom-20 right-6 z-50 w-[92vw] sm:w-[380px] md:w-[410px] max-h-[85vh] flex flex-col shadow-2xl rounded-2xl border border-border/80 bg-background/95 backdrop-blur-xl animate-in fade-in slide-in-from-bottom-5 duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/60 bg-secondary/30 rounded-t-2xl">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-primary to-indigo-500 flex items-center justify-center text-primary-foreground shadow-sm">
            <Mic className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight">Copilot Voice</span>
              {getStatusBadge(status)}
            </div>
            <p className="text-[11px] text-muted-foreground font-mono">
              Sarvam AI &bull; LiveKit Realtime
            </p>
          </div>
        </div>

        <Button
          variant="ghost"
          size="icon"
          onClick={toggleOpen}
          aria-label="Minimize voice panel"
          className="h-7 w-7 rounded-full text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Repository Context Scope Indicator */}
      <div className="px-4 py-2 border-b border-border/40 bg-secondary/15 flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 truncate text-muted-foreground">
          <FileCode className="h-3.5 w-3.5 text-primary shrink-0" />
          <span className="truncate">
            {repoLabel ? (
              <>
                Scope: <span className="font-semibold text-foreground">{repoLabel}</span>
                {repositoryContext?.branch && (
                  <span className="text-muted-foreground ml-1">({repositoryContext.branch})</span>
                )}
              </>
            ) : (
              <span>General Copilot Assistant (no repository scoped)</span>
            )}
          </span>
        </div>
        {repoLabel && (
          <Badge variant="secondary" className="text-[10px] uppercase font-mono tracking-wider shrink-0">
            RAG Grounded
          </Badge>
        )}
      </div>

      {/* Main Body */}
      <div className="p-4 flex-1 overflow-y-auto space-y-3 min-h-[220px] max-h-[360px]">
        {/* Error State */}
        {status === "error" && errorMessage && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-xs text-destructive space-y-2.5">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold">
                  {errorType === "permission_denied"
                    ? "Microphone Permission Required"
                    : errorType === "unconfigured"
                    ? "Voice Services Not Configured"
                    : errorType === "unsupported"
                    ? "Browser Not Supported"
                    : "Connection Error"}
                </p>
                <p className="text-destructive/90 leading-relaxed">{errorMessage}</p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={clearError}
                className="h-7 text-xs border-destructive/30 text-destructive hover:bg-destructive/10"
              >
                Dismiss
              </Button>
              <Button
                size="sm"
                onClick={startSession}
                className="h-7 text-xs bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* Disconnected State / Welcome */}
        {status === "disconnected" && (
          <div className="text-center py-6 px-2 space-y-4">
            <div className="relative mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20 shadow-inner">
              <Mic className="h-8 w-8" />
              <span className="absolute -inset-1 rounded-full border border-primary/20 animate-ping opacity-40" />
            </div>

            <div className="space-y-1">
              <h4 className="text-sm font-semibold">Start Voice Conversation</h4>
              <p className="text-xs text-muted-foreground leading-relaxed max-w-[280px] mx-auto">
                Talk directly with your repository. Ask about architecture, functions, testing, or contribution advice.
              </p>
            </div>

            <Button
              onClick={startSession}
              size="default"
              className="w-full gap-2 font-medium shadow-md transition-all hover:scale-[1.01]"
            >
              <Mic className="h-4 w-4" />
              Connect Voice Agent
            </Button>

            <p className="text-[11px] text-muted-foreground">
              Microphone access requested on connect &bull; Grounded in repository code
            </p>
          </div>
        )}

        {/* Connecting State */}
        {status === "connecting" && (
          <div className="text-center py-10 space-y-3">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <div className="space-y-1">
              <p className="text-sm font-medium">Connecting to LiveKit Room...</p>
              <p className="text-xs text-muted-foreground">
                Initializing Sarvam STT (Saaras), LLM (105B), and TTS (Bulbul)...
              </p>
            </div>
          </div>
        )}

        {/* Active Conversation Mode (Connected / Listening / Speaking) */}
        {isConnectedOrBusy && (
          <div className="space-y-3">
            {/* Audio Wave Visualizer Bar */}
            <div className="p-2.5 rounded-xl border border-border/60 bg-secondary/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    isMuted
                      ? "bg-amber-500"
                      : status === "speaking"
                      ? "bg-primary animate-pulse"
                      : "bg-emerald-500 animate-ping"
                  }`}
                />
                <span className="text-xs font-medium">
                  {isMuted
                    ? "Microphone Muted"
                    : status === "speaking"
                    ? "Sarvam Copilot is Speaking..."
                    : status === "thinking"
                    ? "Retrieving context & reasoning..."
                    : "Listening to your voice..."}
                </span>
              </div>

              {/* Dynamic waveform bars based on audio level */}
              <div className="flex items-center gap-0.5 h-4">
                {[1, 2, 3, 4, 5].map((bar) => {
                  const scale = Math.max(
                    0.2,
                    Math.min(1.0, isMuted ? 0.2 : (audioLevel / 100) * (0.5 + bar * 0.15))
                  );
                  return (
                    <div
                      key={bar}
                      style={{ height: `${scale * 100}%` }}
                      className={`w-1 rounded-full transition-all duration-75 ${
                        isMuted
                          ? "bg-muted-foreground/30"
                          : status === "speaking"
                          ? "bg-primary"
                          : "bg-emerald-500"
                      }`}
                    />
                  );
                })}
              </div>
            </div>

            {/* Transcript Messages Container */}
            <div className="space-y-2.5 text-xs pt-1">
              {transcripts.map((item) => (
                <div
                  key={item.id}
                  className={`flex flex-col ${
                    item.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-3 space-y-1.5 shadow-sm ${
                      item.role === "user"
                        ? "bg-primary text-primary-foreground rounded-tr-none"
                        : "bg-secondary/80 border border-border/80 text-foreground rounded-tl-none"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-[10px] opacity-75 font-medium">
                      {item.role === "user" ? (
                        <>
                          <span>You</span>
                          <span>&bull;</span>
                          <span>{item.timestamp}</span>
                        </>
                      ) : (
                        <>
                          <Bot className="h-3 w-3" />
                          <span>Copilot Voice</span>
                          <span>&bull;</span>
                          <span>{item.timestamp}</span>
                        </>
                      )}
                    </div>

                    <p className="leading-relaxed whitespace-pre-wrap">{item.text}</p>

                    {/* Cited sources badges */}
                    {item.sources && item.sources.length > 0 && (
                      <div className="pt-1 flex flex-wrap gap-1 border-t border-border/40 mt-1.5">
                        {item.sources.map((src, i) => (
                          <Badge
                            key={i}
                            variant="secondary"
                            className="text-[10px] font-mono gap-1 bg-background/50 hover:bg-background"
                          >
                            <FileCode className="h-2.5 w-2.5" />
                            {src}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={transcriptEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Footer Controls */}
      {isConnectedOrBusy && (
        <div className="p-3 border-t border-border/60 bg-secondary/30 rounded-b-2xl flex items-center justify-between gap-2">
          <Button
            variant={isMuted ? "destructive" : "outline"}
            size="sm"
            onClick={toggleMute}
            className="flex-1 gap-2 text-xs"
            aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
          >
            {isMuted ? <MicOff className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
            {isMuted ? "Unmute Mic" : "Mute Mic"}
          </Button>

          <Button
            variant="destructive"
            size="sm"
            onClick={endSession}
            className="flex-1 gap-2 text-xs"
            aria-label="End conversation session"
          >
            <PhoneOff className="h-3.5 w-3.5" />
            End Session
          </Button>
        </div>
      )}
    </div>
  );
}
