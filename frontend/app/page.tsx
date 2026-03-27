"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { streamMessage, getSkills, type SkillInfo, type ToolStep } from "../lib/api";
import { useUser } from "../lib/user";
import { DigestCard } from "../components/digest-card";
import { MarkdownContent } from "../components/markdown-content";
import { ToolSteps } from "../components/tool-steps";

interface Message {
  role: "user" | "kuro";
  text: string;
  mode?: "ingest" | "query";
  skill?: string;
  steps?: ToolStep[];
  streaming?: boolean;
}

const suggestions = [
  "What do you know about me?",
  "Summarize my recent notes",
  "Remember this for later",
];

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function Home() {
  const { userId } = useUser();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const deltaBufferRef = useRef("");
  const rafRef = useRef<number>(0);
  const greeting = useMemo(() => getGreeting(), []);

  useEffect(() => {
    if (!userId) router.push("/login");
  }, [userId, router]);

  useEffect(() => {
    getSkills().then(setSkills).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const prefill = sessionStorage.getItem("kuro_prefill");
    if (prefill) { setInput(prefill); sessionStorage.removeItem("kuro_prefill"); }

    const handlePrefill = (e: Event) => {
      const text = (e as CustomEvent).detail;
      if (text) setInput(text);
    };
    window.addEventListener("kuro:prefill", handlePrefill);
    return () => window.removeEventListener("kuro:prefill", handlePrefill);
  }, []);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [input]);

  if (!userId) return null;

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    let skill: string | undefined;
    const slashMatch = text.match(/^\/(\S+)\s*([\s\S]*)/);
    if (slashMatch) { skill = slashMatch[1]; }

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", text, skill },
      { role: "kuro", text: "", steps: [], streaming: true },
    ]);
    setLoading(true);

    const updateLastMessage = (updater: (msg: Message) => Message) => {
      setMessages((prev) => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = updater({ ...msgs[msgs.length - 1] });
        return msgs;
      });
    };

    abortRef.current = streamMessage(text, userId!, skill, {
      onStep: (step) => {
        updateLastMessage((msg) => ({
          ...msg,
          steps: [...(msg.steps ?? []), step],
        }));
      },
      onDelta: (delta) => {
        deltaBufferRef.current += delta;
        if (!rafRef.current) {
          rafRef.current = requestAnimationFrame(() => {
            const buffered = deltaBufferRef.current;
            deltaBufferRef.current = "";
            rafRef.current = 0;
            updateLastMessage((msg) => ({ ...msg, text: msg.text + buffered }));
          });
        }
      },
      onDone: (meta) => {
        if (deltaBufferRef.current) {
          cancelAnimationFrame(rafRef.current);
          const remaining = deltaBufferRef.current;
          deltaBufferRef.current = "";
          rafRef.current = 0;
          updateLastMessage((msg) => ({ ...msg, text: msg.text + remaining }));
        }
        setTimeout(() => {
          updateLastMessage((msg) => ({
            ...msg,
            streaming: false,
            mode: meta.mode as "ingest" | "query",
            skill: meta.skill ?? undefined,
          }));
          setLoading(false);
          abortRef.current = null;
        }, 0);
      },
      onError: (message) => {
        updateLastMessage((msg) => ({
          ...msg,
          text: msg.text || `Error: ${message}`,
          streaming: false,
        }));
        setLoading(false);
        abortRef.current = null;
      },
    });
  }, [input, loading, userId]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
  }

  return (
    <div className="gradient-page flex h-full flex-col bg-surface-0 text-text-primary">
      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-3xl space-y-5">
          {messages.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center pt-10 text-center">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="mb-8 w-full"
              >
                <DigestCard userId={userId} />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.35, delay: 0.05, ease: "easeOut" }}
                className="mb-5 flex h-11 w-11 items-center justify-center rounded-full bg-accent/10"
              >
                <span className="text-base font-light text-accent">K</span>
              </motion.div>
              <motion.h2
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.1, ease: "easeOut" }}
                className="mb-1.5 text-lg font-extralight tracking-tight text-text-primary"
              >
                {greeting}
              </motion.h2>
              <motion.p
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.15, ease: "easeOut" }}
                className="mb-8 text-[13px] text-text-tertiary"
              >
                Ask a question or share knowledge to remember
              </motion.p>
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.2, ease: "easeOut" }}
                className="flex flex-wrap justify-center gap-2"
              >
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="rounded-full border border-surface-2/30 px-4 py-2 text-[13px] text-text-tertiary transition-all duration-200 hover:border-accent/25 hover:text-text-secondary"
                  >
                    {s}
                  </button>
                ))}
              </motion.div>

              {/* Skill shortcuts */}
              {skills.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: 0.25, ease: "easeOut" }}
                  className="mt-8 w-full max-w-lg"
                >
                  <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                    Skills
                  </p>
                  <div className="flex flex-wrap justify-center gap-1.5">
                    {skills.map((s) => (
                      <button
                        key={s.name}
                        onClick={() => setInput(`/${s.name} `)}
                        className="rounded-full border border-accent/15 bg-accent/5 px-3 py-1.5 text-[11px] text-accent transition-all duration-200 hover:border-accent/30 hover:bg-accent/10"
                      >
                        /{s.name}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Keyboard hint */}
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, delay: 0.35 }}
                className="mt-10 text-[10px] text-text-tertiary"
              >
                Enter to send · Shift+Enter for new line
              </motion.p>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div key={i} className="flex animate-message-in items-start gap-3">
                  <div
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-medium ${
                      msg.role === "user"
                        ? "bg-surface-2/50 text-text-tertiary"
                        : "bg-accent/10 text-accent"
                    }`}
                  >
                    {msg.role === "user" ? userId[0].toUpperCase() : "K"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-0.5 flex items-center gap-2">
                      <span className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary">
                        {msg.role === "user" ? "You" : "Kuro"}
                      </span>
                      {msg.mode && (
                        <span className={`rounded-full px-1.5 py-[1px] text-[9px] font-medium ${
                          msg.mode === "query"
                            ? "bg-mode-query/10 text-mode-query"
                            : "bg-mode-ingest/10 text-mode-ingest"
                        }`}>
                          {msg.mode}
                        </span>
                      )}
                      {msg.skill && (
                        <span className="rounded-full bg-accent/8 px-1.5 py-[1px] text-[9px] font-medium text-accent">
                          /{msg.skill}
                        </span>
                      )}
                    </div>
                    {msg.role === "kuro" && (
                      <ToolSteps steps={msg.steps} collapsed={!!msg.text} />
                    )}
                    {msg.role === "user" ? (
                      <p className="whitespace-pre-wrap text-[14px] leading-[1.7] text-text-primary">
                        {msg.text}
                      </p>
                    ) : (
                      <>
                        <MarkdownContent content={msg.text} streaming={msg.streaming} />
                        {msg.streaming && !msg.text && (
                          <span className="step-shimmer text-[13px]">
                            {msg.steps && msg.steps.length > 0 ? "Searching..." : "Thinking..."}
                          </span>
                        )}
                        {msg.streaming && msg.text && (
                          <span className="inline-block h-4 w-0.5 animate-pulse bg-accent/60" />
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input area */}
      <div className="border-t border-surface-2/30 bg-surface-0 px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-3 rounded-2xl border border-surface-2/35 bg-surface-05 px-4 py-3 transition-all duration-200 focus-within:border-accent/25 focus-within:bg-surface-1"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Tell Kuro something or ask a question..."
              rows={1}
              className="max-h-40 flex-1 resize-none bg-transparent text-[14px] text-text-primary placeholder-text-tertiary outline-none"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/90 text-white transition-all duration-200 hover:bg-accent disabled:opacity-20"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M8 12V4M8 4L4 8M8 4L12 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
