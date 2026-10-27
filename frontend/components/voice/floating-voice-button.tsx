"use client";

import React from "react";
import { Mic, Radio, Volume2, X } from "lucide-react";
import { useVoiceAssistant } from "@/context/voice-assistant-context";
import { FloatingVoicePanel } from "./floating-voice-panel";

export function FloatingVoiceButton() {
  const { isOpen, toggleOpen, status } = useVoiceAssistant();

  const isConnectedOrBusy =
    status === "connected" ||
    status === "listening" ||
    status === "speaking" ||
    status === "thinking";

  return (
    <>
      {/* Floating Assistant Circular Trigger Button */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
        <button
          onClick={toggleOpen}
          aria-label={isOpen ? "Close voice assistant" : "Open voice assistant"}
          aria-expanded={isOpen}
          className={`group relative flex items-center justify-center h-14 w-14 rounded-full shadow-2xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
            isOpen
              ? "bg-secondary text-foreground border border-border"
              : isConnectedOrBusy
              ? "bg-gradient-to-tr from-primary to-emerald-500 text-primary-foreground scale-105"
              : "bg-gradient-to-tr from-primary to-indigo-600 text-primary-foreground hover:scale-105 hover:shadow-primary/25"
          }`}
        >
          {/* Active status pulsating aura */}
          {isConnectedOrBusy && (
            <span className="absolute -inset-1 rounded-full bg-emerald-500/30 animate-ping opacity-75 pointer-events-none" />
          )}

          {/* Icon */}
          {isOpen ? (
            <X className="h-6 w-6 transition-transform group-hover:rotate-90 duration-200" />
          ) : status === "speaking" ? (
            <Radio className="h-6 w-6 animate-pulse" />
          ) : isConnectedOrBusy ? (
            <Volume2 className="h-6 w-6 animate-bounce" />
          ) : (
            <Mic className="h-6 w-6 transition-transform group-hover:scale-110 duration-200" />
          )}

          {/* Active Status Dot */}
          {isConnectedOrBusy && (
            <span className="absolute top-0 right-0 h-3.5 w-3.5 rounded-full bg-emerald-500 border-2 border-background animate-pulse" />
          )}

          {/* Tooltip on hover when closed */}
          {!isOpen && (
            <span className="absolute right-16 px-3 py-1.5 rounded-lg bg-popover text-popover-foreground text-xs font-medium shadow-md border border-border/80 whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150">
              {isConnectedOrBusy ? "Voice Assistant Active" : "Ask with Voice (Sarvam AI)"}
            </span>
          )}
        </button>
      </div>

      {/* Floating Dialog Panel */}
      <FloatingVoicePanel />
    </>
  );
}
