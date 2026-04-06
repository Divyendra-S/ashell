"use client";

import { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useUser } from "../../../lib/user";
import { getConceptDetail, type ConceptDetail } from "../../../lib/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export default function EntityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: slug } = use(params);
  const { userId } = useUser();
  const router = useRouter();
  const [concept, setConcept] = useState<ConceptDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) { router.push("/login"); return; }
    setLoading(true);
    getConceptDetail(slug, userId)
      .then(setConcept)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [slug, userId, router]);

  const navigateToConcept = useCallback((s: string) => router.push(`/entity/${s}`), [router]);

  const prefillChat = useCallback((skill: string, topic: string) => {
    sessionStorage.setItem("kuro_prefill", `/${skill} ${topic}`);
    router.push("/");
  }, [router]);

  if (!userId) return null;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-0">
        <div className="space-y-3 text-center">
          <div className="mx-auto h-6 w-40 skeleton" />
          <div className="mx-auto h-3 w-24 skeleton" />
        </div>
      </div>
    );
  }

  if (error || !concept) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-0">
        <div className="text-center">
          <p className="text-[13px] text-text-tertiary">{error || "Concept not found"}</p>
          <button onClick={() => router.push("/dashboard")} className="mt-4 text-[12px] text-accent transition-colors hover:text-accent">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Parse markdown content into sections
  const sections = concept.content.split(/^## /m).filter(Boolean);
  const keyFacts: string[] = [];
  const connections: string[] = [];
  const notes: string[] = [];

  for (const section of sections) {
    const lines = section.split("\n");
    const heading = lines[0]?.replace(/^#+ /, "").trim();
    const bullets = lines.slice(1).filter((l) => l.startsWith("- ")).map((l) => l.slice(2));
    if (heading === "Key Facts") keyFacts.push(...bullets);
    else if (heading === "Connections") connections.push(...bullets);
    else if (heading === "Notes") notes.push(...bullets);
  }

  const handleQuickAsk = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const input = form.elements.namedItem("question") as HTMLInputElement;
    const q = input.value.trim();
    if (!q) return;
    sessionStorage.setItem("kuro_prefill", q);
    router.push("/");
  };

  return (
    <div className="gradient-page flex h-full flex-col overflow-y-auto bg-surface-0 text-text-primary">
      <div className="mx-auto w-full max-w-5xl px-6 py-8">
        {/* Back */}
        <button
          onClick={() => router.push("/dashboard")}
          className="mb-6 flex items-center gap-1 text-[11px] text-text-tertiary transition-colors duration-200 hover:text-text-secondary"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M10 4L6 8L10 12" />
          </svg>
          Dashboard
        </button>

        <div className="grid gap-8 lg:grid-cols-[1fr_260px]">
          {/* Main content */}
          <div className="space-y-8">
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            >
              <h1 className="mb-2 text-2xl font-extralight tracking-tight text-text-primary">{concept.name}</h1>
              {concept.summary && (
                <p className="text-[13px] leading-[1.7] text-text-secondary">{concept.summary}</p>
              )}
            </motion.div>

            {/* Key Facts */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.06, ease: "easeOut" }}
            >
              <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                Key Facts ({keyFacts.length})
              </h2>
              {keyFacts.length > 0 ? (
                <ul className="space-y-2">
                  {keyFacts.map((fact, i) => (
                    <li key={i} className="flex gap-2.5 text-[13px] leading-[1.65] text-text-secondary">
                      <span className="mt-[9px] h-[3px] w-[3px] shrink-0 rounded-full bg-accent/40" />
                      <span>{fact.replace(/\[\[([^\]]+)\]\]/g, "$1")}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12px] text-text-tertiary">No facts recorded yet.</p>
              )}
            </motion.div>

            {/* Connections — pills */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.12, ease: "easeOut" }}
            >
              <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                Connections ({concept.backlinks.length})
              </h2>
              {concept.backlinks.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {concept.backlinks.map((bl) => (
                    <button
                      key={bl.slug}
                      onClick={() => navigateToConcept(bl.slug)}
                      className="flex items-center gap-1.5 rounded-full border border-surface-2/35 px-3 py-[5px] text-[11px] text-text-secondary transition-all duration-200 hover:border-accent/25 hover:text-accent/90"
                    >
                      <span className="font-medium">{bl.name}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-tertiary">No connections yet.</p>
              )}
            </motion.div>

            {/* Notes */}
            {notes.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.15, ease: "easeOut" }}
              >
                <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Notes</h2>
                <ul className="space-y-2">
                  {notes.map((note, i) => (
                    <li key={i} className="flex gap-2.5 text-[13px] leading-[1.65] text-text-secondary">
                      <span className="mt-[7px] text-[10px] text-mode-ingest/40">~</span>
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}

            {/* Actions */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.18, ease: "easeOut" }}
            >
              <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Actions</h2>
              <div className="flex flex-wrap gap-2">
                {[
                  { skill: "study", label: "Study this topic" },
                  { skill: "explain", label: "Explain in depth" },
                  { skill: "deep-research", label: "Deep research" },
                ].map((action) => (
                  <button
                    key={action.skill}
                    onClick={() => prefillChat(action.skill, concept.name)}
                    className="rounded-full border border-surface-2/35 px-4 py-2 text-[12px] text-text-tertiary transition-all duration-200 hover:border-accent/25 hover:text-text-secondary"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </motion.div>

            {/* Quick ask */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.24, ease: "easeOut" }}
            >
              <form onSubmit={handleQuickAsk} className="flex gap-2">
                <input
                  name="question"
                  type="text"
                  placeholder={`Ask about ${concept.name}...`}
                  className="flex-1 rounded-xl border border-surface-2/30 bg-surface-05 px-4 py-2.5 text-[13px] text-text-primary placeholder-text-tertiary outline-none transition-all duration-200 focus:border-accent/30 focus:bg-surface-1"
                />
                <button
                  type="submit"
                  className="shrink-0 rounded-xl bg-accent/10 px-4 py-2.5 text-[12px] font-medium text-accent transition-all duration-200 hover:bg-accent/20"
                >
                  Ask Kuro
                </button>
              </form>
            </motion.div>
          </div>

          {/* Sidebar — metadata card */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
            className="hidden lg:block"
          >
            <div className="sticky top-8 space-y-5 rounded-2xl border border-surface-2/30 bg-surface-05 p-5">
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Created</p>
                <p className="text-[12px] text-text-secondary">{formatDate(concept.created_at)}</p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Key Facts</p>
                <p className="text-[18px] font-extralight text-text-primary">{keyFacts.length}</p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Connections</p>
                <p className="text-[18px] font-extralight text-text-primary">{concept.backlinks.length}</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
