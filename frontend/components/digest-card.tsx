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
    getDigest(userId)
      .then(setDigest)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [userId]);

  if (dismissed || loading || !digest) return null;

  const hasContent =
    digest.recent_entities.length > 0 ||
    digest.recent_articles.length > 0 ||
    digest.pending_goals.length > 0 ||
    digest.study_suggestion;

  if (!hasContent && digest.streak.current === 0) return null;

  async function handleCompleteGoal(goalId: number) {
    await completeGoal(goalId, userId);
    setDigest((prev) =>
      prev
        ? { ...prev, pending_goals: prev.pending_goals.filter((g) => g.id !== goalId) }
        : prev
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl animate-fade-in rounded-xl border border-surface-2 bg-surface-1 p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-accent">
            <span className="text-sm font-semibold">K</span>
          </div>
          <div>
            <h3 className="text-sm font-medium text-text-primary">
              Today&apos;s Digest
            </h3>
            {digest.streak.current > 0 && (
              <p className="text-xs text-mode-query">
                {digest.streak.current}-day streak
              </p>
            )}
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-text-tertiary hover:text-text-secondary"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 4L12 12M12 4L4 12" />
          </svg>
        </button>
      </div>

      {/* Recent additions */}
      {(digest.recent_entities.length > 0 || digest.recent_articles.length > 0) && (
        <div className="mb-4">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-text-tertiary">
            Recently Added
          </p>
          <div className="space-y-1">
            {digest.recent_entities.slice(0, 3).map((e, i) => (
              <p key={i} className="text-sm text-text-secondary">
                <span className="mr-1.5 inline-block rounded bg-surface-2 px-1.5 py-0.5 text-[10px] text-text-tertiary">
                  {e.entity_type}
                </span>
                {e.name}
              </p>
            ))}
            {digest.recent_articles.map((a, i) => (
              <p key={`a-${i}`} className="text-sm text-text-secondary">
                <span className="mr-1.5 inline-block rounded bg-mode-ingest/15 px-1.5 py-0.5 text-[10px] text-mode-ingest">
                  article
                </span>
                {a.title}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Pending goals */}
      {digest.pending_goals.length > 0 && (
        <div className="mb-4">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-text-tertiary">
            Pending Goals
          </p>
          <div className="space-y-1.5">
            {digest.pending_goals.map((g) => (
              <label
                key={g.id}
                className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
              >
                <input
                  type="checkbox"
                  onChange={() => handleCompleteGoal(g.id)}
                  className="h-3.5 w-3.5 rounded border-surface-3 bg-surface-0 text-accent accent-accent"
                />
                {g.content}
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Study suggestion */}
      {digest.study_suggestion && (
        <div className="mb-4">
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-text-tertiary">
            Study Suggestion
          </p>
          <p className="text-sm text-text-secondary">
            Review <span className="text-accent">{digest.study_suggestion}</span> — it needs attention
          </p>
        </div>
      )}

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => router.push("/voice")}
          className="rounded-full border border-surface-3 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
        >
          Voice Check-in
        </button>
        <button
          onClick={() => router.push("/dashboard")}
          className="rounded-full border border-surface-3 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
        >
          Explore Dashboard
        </button>
        <button
          onClick={() => router.push("/progress")}
          className="rounded-full border border-surface-3 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
        >
          View Progress
        </button>
      </div>
    </div>
  );
}
