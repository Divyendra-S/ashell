"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { sendMessage, type ChatResponse } from "../lib/api";
import { useUser } from "../lib/user";
import { DigestCard } from "../components/digest-card";

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
  const { userId } = useUser();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!userId) router.push("/login");
  }, [userId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const prefill = sessionStorage.getItem("kuro_prefill");
    if (prefill) { setInput(prefill); sessionStorage.removeItem("kuro_prefill"); }
  }, []);

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

    let skill: string | undefined;
    let cleanText = text;
    const slashMatch = text.match(/^\/(\S+)\s*([\s\S]*)/);
    if (slashMatch) { skill = slashMatch[1]; cleanText = slashMatch[2]?.trim() || text; }

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
      setMessages((prev) => [...prev, { role: "kuro", text: `Error: ${err}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
  }

  return (
    <div className="flex h-full flex-col bg-surface-0 text-text-primary">
      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-3xl space-y-5">
          {messages.length === 0 && !loading ? (
            <div className="flex animate-fade-in flex-col items-center justify-center pt-10 text-center">
              <div className="mb-8 w-full">
                <DigestCard userId={userId} />
              </div>

              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-full bg-accent/10">
                <span className="text-base font-light text-accent">K</span>
              </div>
              <h2 className="mb-1.5 text-lg font-extralight tracking-tight text-text-primary">
                What would you like to know?
              </h2>
              <p className="mb-8 text-[13px] text-text-tertiary">
                Ask a question or share knowledge to remember
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="rounded-full border border-surface-2/30 px-4 py-2 text-[13px] text-text-tertiary transition-all duration-200 hover:border-accent/25 hover:text-text-secondary"
                  >
                    {s}
                  </button>
                ))}
              </div>
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
                    <p className="whitespace-pre-wrap text-[14px] leading-[1.7] text-text-primary">
                      {msg.text}
                    </p>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex animate-message-in items-start gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-[10px] font-medium text-accent">
                    K
                  </div>
                  <div className="flex items-center gap-1.5 pt-1.5">
                    {[0, 200, 400].map((delay) => (
                      <span key={delay} className="inline-block h-1 w-1 animate-dot-pulse rounded-full bg-text-tertiary/70" style={{ animationDelay: `${delay}ms` }} />
                    ))}
                  </div>
                </div>
              )}
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
            className="flex items-end gap-3 rounded-2xl border border-surface-2/35 bg-surface-1/50 px-4 py-3 transition-all duration-200 focus-within:border-accent/25 focus-within:bg-surface-1/50"
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
