"use client";

import { useState } from "react";
import {
  Bot,
  Send,
  Sparkles,
  User,
  FileCode,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Database,
  Search,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage, ChatSourceItem } from "@/types";
import { chatWithRepository, ApiError } from "@/lib/api";

interface RepositoryChatProps {
  owner?: string;
  repo?: string;
  branch?: string;
  isLive?: boolean;
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: "welcome-msg",
    role: "assistant",
    content:
      "Hello! I am your repository-aware Copilot. Ask me questions about the codebase architecture, request routing, testing setup, or specific implementation details. My answers are strictly grounded in retrieved source code.",
    timestamp: "Ready",
  },
];

const SUGGESTED_QUESTIONS = [
  "How does this repository handle incoming HTTP requests?",
  "Where are the main application routes or entrypoints defined?",
  "What testing framework and directory structure are used?",
  "How is configuration or environment settings managed?",
  "Explain the core data flow of this project.",
];

export function RepositoryChat({
  owner = "fastapi",
  repo = "fastapi",
  branch,
  isLive = false,
}: RepositoryChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const effectiveOwner = owner || "fastapi";
  const effectiveRepo = repo || "fastapi";
  const repositoryDisplay = `${effectiveOwner}/${effectiveRepo}`;

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputMessage.trim();
    if (!trimmed || isLoading) return;

    setErrorMessage(null);

    // Create user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setIsLoading(true);

    try {
      // Call Phase 9 backend repository chat API
      const response = await chatWithRepository(
        effectiveOwner,
        effectiveRepo,
        trimmed,
        branch
      );

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        retrievalMode: response.retrieval_mode,
        uncertainties: response.uncertainties,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred while communicating with repository chat.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSuggested = (question: string) => {
    setInputMessage(question);
  };

  const formatRetrievalBadge = (mode?: string) => {
    if (mode === "vector") {
      return (
        <Badge variant="outline" className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 border-emerald-500/30 gap-1 bg-emerald-50/50 dark:bg-emerald-950/20">
          <Database className="h-3 w-3" />
          <span>Vector Search</span>
        </Badge>
      );
    }
    if (mode === "keyword_fallback" || mode === "keyword") {
      return (
        <Badge variant="outline" className="text-[10px] font-mono text-amber-600 dark:text-amber-400 border-amber-500/30 gap-1 bg-amber-50/50 dark:bg-amber-950/20">
          <Search className="h-3 w-3" />
          <span>Keyword Fallback</span>
        </Badge>
      );
    }
    return null;
  };

  return (
    <section id="chat" className="py-12 border-t border-border/40 scroll-mt-16 bg-card/20">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary mb-1">
              <Bot className="h-3.5 w-3.5" />
              <span>Interactive Assistance</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Ask About This Repository
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ask questions grounded directly in the indexed repository code and documentation.
            </p>
          </div>

          <Badge
            variant={isLive ? "success" : "warning"}
            className="text-xs font-medium uppercase tracking-wider self-start sm:self-auto"
          >
            {isLive ? "Live RAG Chat Active" : "Example Preview"}
          </Badge>
        </div>

        {/* Chat Window Container */}
        <Card className="max-w-4xl mx-auto border-border bg-card/90 shadow-xl overflow-hidden flex flex-col h-[650px]">
          {/* Chat Header */}
          <CardHeader className="p-4 sm:p-5 border-b border-border/60 bg-secondary/25 flex flex-row items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-9 w-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold text-foreground">
                  Repository Copilot Chat
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground font-mono">
                  Context: {repositoryDisplay} {branch ? `(${branch})` : ""}
                </CardDescription>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-[10px] font-mono">
                Model: Ollama (Local)
              </Badge>
            </div>
          </CardHeader>

          {/* Error Banner */}
          {errorMessage && (
            <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-2.5 flex items-center justify-between text-xs text-destructive">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button
                type="button"
                onClick={() => setErrorMessage(null)}
                className="text-[11px] font-medium underline hover:text-destructive/80 ml-2"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Message Stream */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msg.id}
                  className={`flex items-start space-x-3 ${isUser ? "flex-row-reverse space-x-reverse" : ""}`}
                >
                  <div
                    className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
                      isUser
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-primary border border-border"
                    }`}
                  >
                    {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                  </div>

                  <div
                    className={`max-w-[85%] rounded-xl p-4 text-xs sm:text-sm leading-relaxed space-y-3 ${
                      isUser
                        ? "bg-primary text-primary-foreground font-medium"
                        : "bg-secondary/70 border border-border/80 text-foreground"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {/* Verified Evidence / Sources Section (Assistant Only) */}
                    {!isUser && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border/60 text-xs space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-foreground/80 flex items-center gap-1.5 text-[11px]">
                            <FileCode className="h-3.5 w-3.5 text-primary" />
                            Verified Evidence ({msg.sources.length}{" "}
                            {msg.sources.length === 1 ? "source" : "sources"})
                          </span>
                          {formatRetrievalBadge(msg.retrievalMode)}
                        </div>

                        <div className="grid grid-cols-1 gap-1.5 pt-1">
                          {msg.sources.map((src, idx) => (
                            <div
                              key={`${src.path}-${idx}`}
                              className="bg-card/80 border border-border/70 rounded-md p-2 text-[11px] font-mono flex flex-col sm:flex-row sm:items-center justify-between gap-1"
                            >
                              <div className="flex items-center gap-1.5 overflow-hidden">
                                <span className="font-semibold text-primary truncate">
                                  {src.path}
                                </span>
                                {src.start_line != null && src.end_line != null && (
                                  <span className="text-muted-foreground text-[10px] shrink-0">
                                    (Lines {src.start_line}–{src.end_line})
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 shrink-0">
                                <Badge variant="outline" className="text-[9px] py-0 px-1.5 font-mono">
                                  {src.category}
                                </Badge>
                                {src.score != null && (
                                  <span className="text-[10px] text-muted-foreground">
                                    score: {typeof src.score === "number" ? src.score.toFixed(2) : src.score}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Caveats / Uncertainties */}
                    {!isUser && msg.uncertainties && msg.uncertainties.length > 0 && (
                      <div className="mt-2 text-[10px] text-muted-foreground border-t border-border/30 pt-1.5 space-y-0.5">
                        <span className="font-medium">Note: </span>
                        {msg.uncertainties.join(" • ")}
                      </div>
                    )}

                    {msg.timestamp && (
                      <span
                        className={`block text-[10px] pt-1 ${
                          isUser ? "text-primary-foreground/70 text-right" : "text-muted-foreground"
                        }`}
                      >
                        {msg.timestamp}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="h-8 w-8 rounded-full flex items-center justify-center shrink-0 bg-secondary text-primary border border-border animate-pulse">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="bg-secondary/70 border border-border/80 rounded-xl p-4 text-xs sm:text-sm text-muted-foreground flex items-center gap-2.5">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span>Searching repository context and generating response with Ollama...</span>
                </div>
              </div>
            )}
          </div>

          {/* Suggested Questions Chips */}
          <div className="p-3 border-t border-border/40 bg-secondary/15">
            <div className="flex items-center space-x-1.5 text-[11px] text-muted-foreground mb-2">
              <Sparkles className="h-3 w-3 text-primary" />
              <span>Suggested questions:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => handleSelectSuggested(q)}
                  disabled={isLoading}
                  className="text-xs bg-secondary hover:bg-secondary/80 border border-border px-2.5 py-1 rounded-md text-foreground/90 transition-colors text-left disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input Box */}
          <div className="p-4 border-t border-border/60 bg-card">
            <form onSubmit={handleSend} className="flex items-center gap-2">
              <Input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  isLoading
                    ? "Generating answer..."
                    : `Ask a question about ${repositoryDisplay}...`
                }
                disabled={isLoading}
                className="flex-1 h-10 bg-secondary/30 text-xs sm:text-sm border-border"
              />
              <Button
                type="submit"
                size="default"
                disabled={isLoading || !inputMessage.trim()}
                className="h-10 px-4 gap-1.5 text-xs"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <span>Send</span>
                    <Send className="h-3.5 w-3.5" />
                  </>
                )}
              </Button>
            </form>
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
              <span>Grounded in PostgreSQL pgvector semantic retrieval with keyword fallback.</span>
              <span className="font-mono">Phase 9 RAG Chat</span>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}
