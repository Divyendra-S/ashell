"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getDigest, completeGoal, type DigestData } from "../lib/api";

export function DigestCard({ userId }: { userId: string }) {
  const router = useRouter();
  const [digest, setDigest] = useState<DigestData | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDigest(userId).then(setDigest).catch(console.error).finally(() => setLoading(false));
  }, [userId]);

  if (dismissed || loading || !digest) return null;

  const hasContent = digest.recent_entities.length > 0 || digest.recent_articles.length > 0 || digest.pending_goals.length > 0 || digest.study_suggestion;
  if (!hasContent && digest.streak.current === 0) return null;

  async function handleCompleteGoal(goalId: number) {
    await completeGoal(goalId, userId);
    setDigest((prev) => prev ? { ...prev, pending_goals: prev.pending_goals.filter((g) => g.id !== goalId) } : prev);
  }

  return (
    <div className="mx-auto w-full max-w-2xl animate-fade-in rounded-2xl border border-surface-2/35 bg-surface-1/45 p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/10">
            <span className="text-[11px] font-light text-accent">K</span>
          </div>
          <div>
            <h3 className="text-[13px] font-normal text-text-primary">Today&apos;s Digest</h3>
            {digest.streak.current > 0 && (
              <p className="text-[10px] text-mode-query">{digest.streak.current}-day streak</p>
            )}
          </div>
        </div>
        <button onClick={() => setDismissed(true)} className="text-text-tertiary transition-colors hover:text-text-tertiary">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M4 4L12 12M12 4L4 12" />
          </svg>
        </button>
      </div>

      {/* Recent additions */}
      {(digest.recent_entities.length > 0 || digest.recent_articles.length > 0) && (
        <div className="mb-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Recently Added</p>
          <div className="space-y-1.5">
            {digest.recent_entities.slice(0, 3).map((e, i) => (
              <p key={i} className="flex items-center gap-1.5 text-[12px] text-text-secondary">
                <span className="rounded bg-surface-2/30 px-1.5 py-[1px] text-[9px] text-text-tertiary">{e.entity_type}</span>
                {e.name}
              </p>
            ))}
            {digest.recent_articles.map((a, i) => (
              <p key={`a-${i}`} className="flex items-center gap-1.5 text-[12px] text-text-secondary">
                <span className="rounded bg-mode-ingest/8 px-1.5 py-[1px] text-[9px] text-mode-ingest">article</span>
                {a.title}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Pending goals */}
      {digest.pending_goals.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Pending Goals</p>
          <div className="space-y-1.5">
            {digest.pending_goals.map((g) => (
              <label key={g.id} className="flex cursor-pointer items-center gap-2 text-[12px] text-text-secondary transition-colors hover:text-text-primary">
                <input type="checkbox" onChange={() => handleCompleteGoal(g.id)} className="h-3 w-3 rounded border-surface-3/40 bg-transparent accent-accent" />
                {g.content}
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Study suggestion */}
      {digest.study_suggestion && (
        <div className="mb-4">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Study Suggestion</p>
          <p className="text-[12px] text-text-secondary">
            Review <span className="text-accent">{digest.study_suggestion}</span> — it needs attention
          </p>
        </div>
      )}

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        {[
          { href: "/voice", label: "Voice Check-in" },
          { href: "/dashboard", label: "Explore Dashboard" },
          { href: "/progress", label: "View Progress" },
        ].map((action) => (
          <button
            key={action.href}
            onClick={() => router.push(action.href)}
            className="rounded-full border border-surface-2/35 px-3 py-1.5 text-[11px] text-text-tertiary transition-all duration-200 hover:border-accent/20 hover:text-text-secondary"
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
