"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "../../lib/user";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

type ConnectionState = "idle" | "connecting" | "connected" | "disconnecting" | "error";

export default function VoicePage() {
  const { userId } = useUser();
  const router = useRouter();
  const [state, setState] = useState<ConnectionState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!userId) {
      router.push("/login");
    }
  }, [userId, router]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clientRef.current?.disconnect();
    };
  }, []);

  const connect = useCallback(async () => {
    if (!userId) return;
    setState("connecting");
    setError(null);

    try {
      const transport = new SmallWebRTCTransport({
        webrtcRequestParams: {
          endpoint: "/api/offer",
          requestData: { user_id: userId },
        },
      });

      const client = new PipecatClient({
        transport,
        enableMic: true,
        enableCam: false,
        callbacks: {
          onConnected: () => setState("connected"),
          onDisconnected: () => {
            setState("idle");
            clientRef.current = null;
          },
          onBotReady: () => setState("connected"),
          onTransportStateChanged: (s: string) => {
            if (s === "error") setState("error");
          },
          onTrackStarted: (track: MediaStreamTrack) => {
            if (track.kind === "audio" && audioRef.current) {
              audioRef.current.srcObject = new MediaStream([track]);
              audioRef.current.play().catch(() => {});
            }
          },
        },
      });

      clientRef.current = client;

      await client.connect();
    } catch (err) {
      console.error("Voice connection error:", err);
      setError(err instanceof Error ? err.message : "Connection failed");
      setState("error");
      clientRef.current = null;
    }
  }, [userId]);

  const disconnect = useCallback(async () => {
    setState("disconnecting");
    try {
      await clientRef.current?.disconnect();
    } catch (err) {
      console.error("Disconnect error:", err);
    }
    clientRef.current = null;
    setState("idle");
  }, []);

  const toggleMute = useCallback(() => {
    if (clientRef.current) {
      const newMuted = !isMuted;
      setIsMuted(newMuted);
      clientRef.current.enableMic(!newMuted);
    }
  }, [isMuted]);

  if (!userId) return null;

  return (
    <div className="flex min-h-screen flex-col bg-surface-0 text-text-primary">
      <audio ref={audioRef} autoPlay />
      {/* Header */}
      <header className="border-b border-surface-2 px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="text-text-tertiary transition-colors hover:text-text-primary"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M12 4L6 10L12 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <h1 className="text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Kuro Voice
            </h1>
          </div>
          <span className="text-xs text-text-tertiary">{userId}</span>
        </div>
      </header>

      {/* Main content */}
      <main className="flex flex-1 flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center gap-8">
          {/* Status */}
          <div className="text-center">
            <h2 className="mb-2 text-xl font-medium text-text-primary">
              {state === "idle" && "Daily Check-in"}
              {state === "connecting" && "Connecting..."}
              {state === "connected" && (isMuted ? "Muted" : "Listening...")}
              {state === "disconnecting" && "Ending session..."}
              {state === "error" && "Connection Error"}
            </h2>
            <p className="text-sm text-text-tertiary">
              {state === "idle" && "Tap the mic to start your voice check-in with Kuro"}
              {state === "connecting" && "Setting up your session"}
              {state === "connected" && (isMuted ? "Tap the mic to unmute" : "Speak naturally \u2014 Kuro is listening")}
              {state === "disconnecting" && "Saving your session..."}
              {state === "error" && (error || "Something went wrong")}
            </p>
          </div>

          {/* Mic button */}
          <div className="relative">
            {state === "connected" && !isMuted && (
              <>
                <div className="absolute inset-0 -m-4 animate-ping rounded-full bg-accent/20" style={{ animationDuration: "2s" }} />
                <div className="absolute inset-0 -m-2 animate-ping rounded-full bg-accent/10" style={{ animationDuration: "2s", animationDelay: "0.5s" }} />
              </>
            )}

            <button
              onClick={state === "idle" || state === "error" ? connect : state === "connected" ? toggleMute : undefined}
              disabled={state === "connecting" || state === "disconnecting"}
              className={`relative z-10 flex h-24 w-24 items-center justify-center rounded-full transition-all duration-300 ${
                state === "connected" && !isMuted
                  ? "bg-accent text-surface-0 shadow-lg shadow-accent/25"
                  : state === "connected" && isMuted
                    ? "bg-surface-2 text-text-tertiary"
                    : state === "connecting"
                      ? "animate-pulse bg-surface-2 text-text-tertiary"
                      : "bg-accent/15 text-accent hover:bg-accent/25"
              } disabled:opacity-50`}
            >
              {isMuted && state === "connected" ? (
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="1" y1="1" x2="23" y2="23" />
                  <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
                  <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .67-.1 1.32-.27 1.93" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                  <line x1="8" y1="23" x2="16" y2="23" />
                </svg>
              ) : (
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="1" width="6" height="11" rx="3" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                  <line x1="8" y1="23" x2="16" y2="23" />
                </svg>
              )}
            </button>
          </div>

          {/* End session button */}
          {state === "connected" && (
            <button
              onClick={disconnect}
              className="rounded-full border border-red-500/30 px-6 py-2 text-sm text-red-400 transition-colors hover:border-red-500/60 hover:bg-red-500/10"
            >
              End Session
            </button>
          )}

          {state === "error" && (
            <button
              onClick={connect}
              className="rounded-full border border-accent/30 px-6 py-2 text-sm text-accent transition-colors hover:border-accent/60 hover:bg-accent/10"
            >
              Try Again
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
