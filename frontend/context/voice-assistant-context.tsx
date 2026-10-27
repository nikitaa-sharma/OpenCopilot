"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Room,
  RoomEvent,
  Track,
  RemoteTrack,
  RemoteTrackPublication,
  RemoteParticipant,
  LocalAudioTrack,
  DataPacket_Kind,
} from "livekit-client";
import { fetchVoiceToken, ApiError } from "@/lib/api";

export type VoiceStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "listening"
  | "thinking"
  | "speaking"
  | "error";

export type VoiceErrorType =
  | "permission_denied"
  | "unsupported"
  | "unconfigured"
  | "connection_failed"
  | null;

export interface VoiceTranscriptItem {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: string;
  sources?: string[];
}

export interface VoiceRepositoryContext {
  owner?: string;
  repo?: string;
  branch?: string;
}

interface VoiceAssistantContextValue {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  toggleOpen: () => void;
  status: VoiceStatus;
  isMuted: boolean;
  toggleMute: () => Promise<void>;
  repositoryContext: VoiceRepositoryContext | null;
  setRepositoryContext: (ctx: VoiceRepositoryContext | null) => void;
  transcripts: VoiceTranscriptItem[];
  errorMessage: string | null;
  errorType: VoiceErrorType;
  audioLevel: number;
  startSession: () => Promise<void>;
  endSession: () => Promise<void>;
  clearError: () => void;
}

const VoiceAssistantContext = createContext<VoiceAssistantContextValue | undefined>(undefined);

export function VoiceAssistantProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<VoiceStatus>("disconnected");
  const [isMuted, setIsMuted] = useState(false);
  const [transcripts, setTranscripts] = useState<VoiceTranscriptItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<VoiceErrorType>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [repositoryContext, setRepositoryContext] = useState<VoiceRepositoryContext | null>(null);

  const roomRef = useRef<Room | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const clearError = useCallback(() => {
    setErrorMessage(null);
    setErrorType(null);
    if (status === "error") {
      setStatus("disconnected");
    }
  }, [status]);

  // Clean up audio nodes & visualizer
  const stopAudioAnalysis = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  }, []);

  // Teardown everything
  const teardownSession = useCallback(async () => {
    stopAudioAnalysis();

    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }

    if (roomRef.current) {
      try {
        await roomRef.current.disconnect();
      } catch {
        // ignore
      }
      roomRef.current = null;
    }

    if (audioElementRef.current) {
      audioElementRef.current.srcObject = null;
    }

    setIsMuted(false);
  }, [stopAudioAnalysis]);

  const endSession = useCallback(async () => {
    await teardownSession();
    setStatus("disconnected");
  }, [teardownSession]);

  // Start Voice Session
  const startSession = useCallback(async () => {
    clearError();
    setStatus("connecting");

    // 1. Check browser media support
    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setErrorType("unsupported");
      setErrorMessage("Your browser does not support audio capture. Please try an updated modern browser.");
      return;
    }

    // 2. Request token from backend
    let tokenData;
    try {
      tokenData = await fetchVoiceToken({
        repository_owner: repositoryContext?.owner,
        repository_name: repositoryContext?.repo,
        branch: repositoryContext?.branch,
      });
    } catch (err: unknown) {
      setStatus("error");
      if (err instanceof ApiError) {
        if (err.statusCode === 503) {
          setErrorType("unconfigured");
          setErrorMessage(
            err.message ||
              "LiveKit or Sarvam AI is not configured. Please set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and SARVAM_API_KEY in the backend environment."
          );
        } else {
          setErrorType("connection_failed");
          setErrorMessage(err.message || "Failed to initialize voice session.");
        }
      } else {
        setErrorType("connection_failed");
        setErrorMessage("Could not reach backend voice service. Please make sure the backend server is running.");
      }
      return;
    }

    // 3. Request user microphone permission
    let userStream: MediaStream;
    try {
      userStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micStreamRef.current = userStream;
    } catch (err: unknown) {
      const error = err as Error;
      setStatus("error");
      setErrorType("permission_denied");
      if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
        setErrorMessage(
          "Microphone access was denied. Please allow microphone permissions in your browser address bar to talk with the Copilot."
        );
      } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
        setErrorMessage("No microphone detected. Please plug in or enable an audio input device.");
      } else {
        setErrorMessage(`Microphone error: ${error.message || "Failed to access audio device."}`);
      }
      return;
    }

    // 4. Set up audio visualizer analyser
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      const source = audioCtx.createMediaStreamSource(userStream);
      source.connect(analyser);
      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
    } catch {
      // Visualizer is optional
    }

    // 5. Connect to LiveKit Room
    try {
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });
      roomRef.current = room;

      // Ensure hidden audio element exists for playback
      if (!audioElementRef.current) {
        const audio = document.createElement("audio");
        audio.autoplay = true;
        audio.style.display = "none";
        document.body.appendChild(audio);
        audioElementRef.current = audio;
      }

      // Handle remote audio from Sarvam voice agent
      room.on(
        RoomEvent.TrackSubscribed,
        (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio && audioElementRef.current) {
            track.attach(audioElementRef.current);
            setStatus("speaking");
          }
        }
      );

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        if (track.kind === Track.Kind.Audio && audioElementRef.current) {
          track.detach(audioElementRef.current);
          setStatus("connected");
        }
      });

      // Handle speaking status
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        if (!room) return;
        const agentSpeaking = speakers.some((s) => s.identity !== tokenData.participant_identity);
        const userSpeaking = speakers.some((s) => s.identity === tokenData.participant_identity);

        if (agentSpeaking) {
          setStatus("speaking");
        } else if (userSpeaking) {
          setStatus("listening");
        } else {
          setStatus("connected");
        }
      });

      // Handle transcripts / data packets from agent
      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
        try {
          const str = new TextDecoder().decode(payload);
          const data = JSON.parse(str);
          if (data && data.text) {
            const role = data.role || (participant?.identity === tokenData.participant_identity ? "user" : "assistant");
            setTranscripts((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
                role: role,
                text: data.text,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                sources: data.sources || [],
              },
            ]);
          }
        } catch {
          // ignore malformed data packet
        }
      });

      room.on(RoomEvent.Reconnecting, () => {
        setStatus("connecting");
      });

      room.on(RoomEvent.Reconnected, () => {
        setStatus("connected");
      });

      room.on(RoomEvent.Disconnected, () => {
        setStatus("disconnected");
      });

      // Connect to LiveKit server
      await room.connect(tokenData.server_url, tokenData.participant_token);

      // Publish local microphone audio track
      await room.localParticipant.setMicrophoneEnabled(true);

      setStatus("connected");

      // Add session start banner message in transcript
      const repoLabel = repositoryContext?.owner && repositoryContext?.repo
        ? `${repositoryContext.owner}/${repositoryContext.repo}${repositoryContext.branch ? ` (${repositoryContext.branch})` : ""}`
        : "General Mode";

      setTranscripts([
        {
          id: `sys-${Date.now()}`,
          role: "assistant",
          text: `Voice session started (${repoLabel}). Speak naturally — I can answer questions grounded in the repository.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err: unknown) {
      const error = err as Error;
      await teardownSession();
      setStatus("error");
      setErrorType("connection_failed");
      setErrorMessage(`LiveKit connection failed: ${error.message || "Could not establish real-time audio connection."}`);
    }
  }, [clearError, repositoryContext, teardownSession]);

  // Toggle microphone mute/unmute
  const toggleMute = useCallback(async () => {
    if (!roomRef.current) return;
    try {
      const nextMuted = !isMuted;
      await roomRef.current.localParticipant.setMicrophoneEnabled(!nextMuted);
      setIsMuted(nextMuted);
    } catch (err) {
      console.error("Failed to toggle microphone mute:", err);
    }
  }, [isMuted]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      teardownSession();
    };
  }, [teardownSession]);

  return (
    <VoiceAssistantContext.Provider
      value={{
        isOpen,
        setIsOpen,
        toggleOpen,
        status,
        isMuted,
        toggleMute,
        repositoryContext,
        setRepositoryContext,
        transcripts,
        errorMessage,
        errorType,
        audioLevel,
        startSession,
        endSession,
        clearError,
      }}
    >
      {children}
    </VoiceAssistantContext.Provider>
  );
}

export function useVoiceAssistant() {
  const context = useContext(VoiceAssistantContext);
  if (!context) {
    throw new Error("useVoiceAssistant must be used within a VoiceAssistantProvider");
  }
  return context;
}
