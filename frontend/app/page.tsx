"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { sendMessage, type ChatResponse } from "../lib/api";
import { useUser } from "../lib/user";

interface Message {
  role: "user" | "kuro";
  text: string;
  mode?: "ingest" | "query";
  skill?: string;
}

const suggestions = [
  "What do you know about me?",
  "Summarize my recent notes",
  "Remember this for later",
];

export default function Home() {
  const { userId, logout } = useUser();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!userId) {
      router.push("/login");
    }
  }, [userId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea fallback (Firefox/Safari)
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [input]);

  if (!userId) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    // Detect slash command
    let skill: string | undefined;
    let cleanText = text;
    const slashMatch = text.match(/^\/(\S+)\s*(.*)/s);
    if (slashMatch) {
      skill = slashMatch[1];
      cleanText = slashMatch[2]?.trim() || text;
    }

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text, skill }]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendMessage(text, userId!, skill);
      setMessages((prev) => [
        ...prev,
        { role: "kuro", text: res.response, mode: res.mode, skill: res.skill ?? undefined },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "kuro", text: `Error: ${err}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface-0 text-text-primary">
      {/* Header */}
      <header className="border-b border-surface-2 px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <h1 className="text-xs font-semibold uppercase tracking-[0.2em] text-text-secondary">
            Kuro
          </h1>
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/voice")}
              className="flex items-center gap-1.5 rounded-lg border border-surface-3 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
              title="Voice Check-in"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="1" width="6" height="11" rx="3" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
              Voice
            </button>
            <span className="text-xs text-text-tertiary">{userId}</span>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-surface-3 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.length === 0 && !loading ? (
            /* Empty state */
            <div className="flex animate-fade-in flex-col items-center justify-center pt-24 text-center">
              <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-accent">
                <span className="text-lg font-semibold">K</span>
              </div>
              <h2 className="mb-2 text-xl font-medium text-text-primary">
                What would you like to know?
              </h2>
              <p className="mb-8 text-sm text-text-tertiary">
                Ask a question or share knowledge to remember
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="rounded-full border border-surface-3 px-4 py-2 text-sm text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className="flex animate-message-in items-start gap-3"
                >
                  {/* Avatar */}
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      msg.role === "user"
                        ? "bg-surface-2 text-text-secondary"
                        : "bg-accent/15 text-accent"
                    }`}
                  >
                    {msg.role === "user" ? userId[0].toUpperCase() : "K"}
                  </div>

                  <div className="min-w-0 flex-1">
                    {/* Role label + mode badge */}
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-[11px] font-medium uppercase tracking-wide text-text-tertiary">
                        {msg.role === "user" ? "You" : "Kuro"}
                      </span>
                      {msg.mode && (
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                            msg.mode === "query"
                              ? "bg-mode-query/15 text-mode-query"
                              : "bg-mode-ingest/15 text-mode-ingest"
                          }`}
                        >
                          {msg.mode}
                        </span>
                      )}
                      {msg.skill && (
                        <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                          /{msg.skill}
                        </span>
                      )}
                    </div>
                    <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-text-primary">
                      {msg.text}
                    </p>
                  </div>
                </div>
              ))}

              {/* Loading */}
              {loading && (
                <div className="flex animate-message-in items-start gap-3">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold text-accent">
                    K
                  </div>
                  <div className="flex items-center gap-1.5 pt-2">
                    <span
                      className="inline-block h-1.5 w-1.5 animate-dot-pulse rounded-full bg-text-tertiary"
                      style={{ animationDelay: "0ms" }}
                    />
                    <span
                      className="inline-block h-1.5 w-1.5 animate-dot-pulse rounded-full bg-text-tertiary"
                      style={{ animationDelay: "200ms" }}
                    />
                    <span
                      className="inline-block h-1.5 w-1.5 animate-dot-pulse rounded-full bg-text-tertiary"
                      style={{ animationDelay: "400ms" }}
                    />
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input area */}
      <div className="border-t border-surface-2 bg-surface-0 px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-3 rounded-xl border border-surface-2 bg-surface-1 px-4 py-3 transition-colors focus-within:border-accent/40"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Tell Kuro something or ask a question..."
              rows={1}
              className="max-h-40 flex-1 resize-none bg-transparent text-[15px] text-text-primary placeholder-text-tertiary outline-none"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-surface-0 transition-opacity disabled:opacity-30"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M8 12V4M8 4L4 8M8 4L12 8"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
