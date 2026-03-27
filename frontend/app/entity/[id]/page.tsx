"use client";

import { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "../../../lib/user";
import { getEntityDetail, type EntityDetail, type GraphRelation } from "../../../lib/api";

const TYPE_COLORS: Record<string, string> = {
  person: "bg-[#818cf8]/10 text-[#818cf8]/80",
  company: "bg-[#f472b6]/10 text-[#f472b6]/80",
  project: "bg-[#34d399]/10 text-[#34d399]/80",
  topic: "bg-[#fbbf24]/10 text-[#fbbf24]/80",
  place: "bg-[#60a5fa]/10 text-[#60a5fa]/80",
  event: "bg-[#fb923c]/10 text-[#fb923c]/80",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export default function EntityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: idStr } = use(params);
  const entityId = parseInt(idStr, 10);
  const { userId } = useUser();
  const router = useRouter();
  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) { router.push("/login"); return; }
    setLoading(true);
    getEntityDetail(entityId, userId)
      .then(setEntity)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [entityId, userId, router]);

  const navigateToEntity = useCallback((id: number) => router.push(`/entity/${id}`), [router]);

  const prefillChat = useCallback((skill: string, topic: string) => {
    sessionStorage.setItem("kuro_prefill", `/${skill} ${topic}`);
    router.push("/");
  }, [router]);

  if (!userId) return null;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-0">
        <div className="space-y-3 text-center">
          <div className="mx-auto h-6 w-40 animate-pulse rounded-lg bg-surface-2/20" />
          <div className="mx-auto h-3 w-24 animate-pulse rounded bg-surface-2/15" />
        </div>
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-0">
        <div className="text-center">
          <p className="text-[13px] text-text-tertiary">{error || "Entity not found"}</p>
          <button onClick={() => router.push("/dashboard")} className="mt-4 text-[12px] text-accent transition-colors hover:text-accent">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const typeBadge = TYPE_COLORS[entity.entity_type] || "bg-surface-2/30 text-text-tertiary";

  return (
    <div className="gradient-page flex h-full flex-col overflow-y-auto bg-surface-0 text-text-primary">
      <div className="mx-auto w-full max-w-4xl space-y-8 px-6 py-8">
        {/* Back */}
        <button
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-1 text-[11px] text-text-tertiary transition-colors duration-200 hover:text-text-secondary"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M10 4L6 8L10 12" />
          </svg>
          Dashboard
        </button>

        {/* Header */}
        <div>
          <div className="mb-2 flex items-center gap-3">
            <h1 className="text-2xl font-extralight tracking-tight text-text-primary">{entity.name}</h1>
            <span className={`rounded-full px-2.5 py-[3px] text-[10px] font-medium ${typeBadge}`}>
              {entity.entity_type}
            </span>
          </div>
          {entity.summary && (
            <p className="text-[13px] leading-[1.7] text-text-secondary">{entity.summary}</p>
          )}
          <p className="mt-1.5 text-[11px] text-text-tertiary">Created {formatDate(entity.created_at)}</p>
        </div>

        {/* Facts — bullet list */}
        <div>
          <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
            Facts ({entity.facts.length})
          </h2>
          {entity.facts.length > 0 ? (
            <ul className="space-y-2">
              {entity.facts.map((fact) => (
                <li key={fact.id} className="flex gap-2.5 text-[13px] leading-[1.65] text-text-secondary">
                  <span className="mt-[9px] h-[3px] w-[3px] shrink-0 rounded-full bg-accent/40" />
                  <div>
                    <span>{fact.content}</span>
                    <span className="ml-2 text-[10px] text-text-tertiary">{fact.source} · {formatDate(fact.created_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[12px] text-text-tertiary">No facts recorded yet.</p>
          )}
        </div>

        {/* Relations — pills */}
        <div>
          <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
            Relations ({entity.relations.length})
          </h2>
          {entity.relations.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {entity.relations.map((rel) => {
                const isSource = rel.source_id === entityId;
                const otherName = isSource ? rel.target_name : rel.source_name;
                const otherId = isSource ? rel.target_id : rel.source_id;
                return (
                  <button
                    key={rel.id}
                    onClick={() => navigateToEntity(otherId)}
                    className="flex items-center gap-1.5 rounded-full border border-surface-2/35 px-3 py-[5px] text-[11px] text-text-secondary transition-all duration-200 hover:border-accent/25 hover:text-accent/90"
                  >
                    <span className="text-text-tertiary">{rel.relation_type}</span>
                    <span className="text-text-tertiary">·</span>
                    <span className="font-medium">{otherName}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-[12px] text-text-tertiary">No relations yet.</p>
          )}
        </div>

        {/* Actions */}
        <div>
          <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Actions</h2>
          <div className="flex flex-wrap gap-2">
            {[
              { skill: "study", label: "Study this topic" },
              { skill: "explain", label: "Explain in depth" },
              { skill: "deep-research", label: "Deep research" },
            ].map((action) => (
              <button
                key={action.skill}
                onClick={() => prefillChat(action.skill, entity.name)}
                className="rounded-full border border-surface-2/35 px-4 py-2 text-[12px] text-text-tertiary transition-all duration-200 hover:border-accent/25 hover:text-text-secondary"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
