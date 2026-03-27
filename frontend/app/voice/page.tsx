"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useUser } from "../../lib/user";
import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

type ConnectionState = "idle" | "connecting" | "connected" | "disconnecting" | "error";

const TIPS = [
  "Tell Kuro about what you learned today",
  "Reflect on your goals and progress",
  "Share an idea you've been thinking about",
  "Summarize an article you just read",
];

export default function VoicePage() {
  const { userId } = useUser();
  const router = useRouter();
  const [state, setState] = useState<ConnectionState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tipIndex, setTipIndex] = useState(0);
  const clientRef = useRef<PipecatClient | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!userId) router.push("/login");
  }, [userId, router]);

  useEffect(() => {
    return () => { clientRef.current?.disconnect(); };
  }, []);

  // Cycle tips every 4s when idle
  useEffect(() => {
    if (state !== "idle") return;
    const interval = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % TIPS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [state]);

  const connect = useCallback(async () => {
    if (!userId) return;
    setState("connecting");
    setError(null);
    try {
      const transport = new SmallWebRTCTransport({
        webrtcRequestParams: { endpoint: "/api/offer", requestData: { user_id: userId } },
      });
      const client = new PipecatClient({
        transport, enableMic: true, enableCam: false,
        callbacks: {
          onConnected: () => setState("connected"),
          onDisconnected: () => { setState("idle"); clientRef.current = null; },
          onBotReady: () => setState("connected"),
          onTransportStateChanged: (s: string) => { if (s === "error") setState("error"); },
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
      setError(err instanceof Error ? err.message : "Connection failed");
      setState("error");
      clientRef.current = null;
    }
  }, [userId]);

  const disconnect = useCallback(async () => {
    setState("disconnecting");
    try { await clientRef.current?.disconnect(); } catch {}
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

  const isListening = state === "connected" && !isMuted;

  return (
    <div className="gradient-page relative flex h-full flex-col bg-surface-0 text-text-primary">
      <audio ref={audioRef} autoPlay />
      <main className="flex flex-1 flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center gap-10">
          {/* Status */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="text-center"
          >
            <h2 className="text-xl font-extralight tracking-tight text-text-primary">
              {state === "idle" && "Daily Check-in"}
              {state === "connecting" && "Connecting..."}
              {state === "connected" && (isMuted ? "Muted" : "Listening...")}
              {state === "disconnecting" && "Ending session..."}
              {state === "error" && "Connection Error"}
            </h2>
            <p className="mt-2 text-[13px] text-text-tertiary">
              {state === "idle" && "Tap the mic to start your voice check-in with Kuro"}
              {state === "connecting" && "Setting up your session"}
              {state === "connected" && (isMuted ? "Tap the mic to unmute" : "Speak naturally \u2014 Kuro is listening")}
              {state === "disconnecting" && "Saving your session..."}
              {state === "error" && (error || "Something went wrong")}
            </p>
          </motion.div>

          {/* Mic button with decorative rings */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.08, ease: "easeOut" }}
            className="relative flex items-center justify-center"
          >
            {/* Decorative concentric rings */}
            <div className="pointer-events-none absolute h-40 w-40 rounded-full border border-surface-2/10" />
            <div className="pointer-events-none absolute h-60 w-60 rounded-full border border-surface-2/[0.06]" />
            <div className="pointer-events-none absolute h-80 w-80 rounded-full border border-surface-2/[0.03]" />

            {isListening && (
              <>
                <div className="absolute inset-0 -m-5 animate-ping rounded-full bg-accent/15" style={{ animationDuration: "2s" }} />
                <div className="absolute inset-0 -m-2.5 animate-ping rounded-full bg-accent/8" style={{ animationDuration: "2s", animationDelay: "0.5s" }} />
              </>
            )}
            <button
              onClick={state === "idle" || state === "error" ? connect : state === "connected" ? toggleMute : undefined}
              disabled={state === "connecting" || state === "disconnecting"}
              className={`relative z-10 flex h-24 w-24 items-center justify-center rounded-full transition-all duration-300 ${
                isListening
                  ? "bg-accent text-white shadow-[0_0_40px_-8px_rgba(var(--gradient-accent-rgb),0.4)]"
                  : state === "connected" && isMuted
                    ? "bg-surface-1/60 text-text-tertiary"
                    : state === "connecting"
                      ? "animate-pulse bg-surface-1/40 text-text-tertiary"
                      : "bg-accent/10 text-accent hover:bg-accent/15"
              } disabled:opacity-50`}
            >
              {isMuted && state === "connected" ? (
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="1" y1="1" x2="23" y2="23" />
                  <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
                  <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .67-.1 1.32-.27 1.93" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                </svg>
              ) : (
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="1" width="6" height="11" rx="3" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                </svg>
              )}
            </button>
          </motion.div>

          {/* End session / Try again */}
          {state === "connected" && (
            <button
              onClick={disconnect}
              className="rounded-full border border-red-500/20 px-5 py-2 text-[12px] text-red-400/80 transition-all duration-200 hover:border-red-500/40 hover:bg-red-500/5"
            >
              End Session
            </button>
          )}
          {state === "error" && (
            <button
              onClick={connect}
              className="rounded-full border border-accent/20 px-5 py-2 text-[12px] text-accent transition-all duration-200 hover:border-accent/40 hover:bg-accent/5"
            >
              Try Again
            </button>
          )}

          {/* Cycling tips — idle state only */}
          {state === "idle" && (
            <div className="h-6">
              <AnimatePresence mode="wait">
                <motion.p
                  key={tipIndex}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.3 }}
                  className="text-center text-[12px] italic text-text-tertiary"
                >
                  &ldquo;{TIPS[tipIndex]}&rdquo;
                </motion.p>
              </AnimatePresence>
            </div>
          )}
        </div>
      </main>

      {/* Bottom reassurance */}
      <p className="pb-5 text-center text-[10px] text-text-tertiary">
        Sessions are transcribed and added to your knowledge base
      </p>
    </div>
  );
}
