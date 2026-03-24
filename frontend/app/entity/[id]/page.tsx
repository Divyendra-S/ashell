"use client";

import { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "../../../lib/user";
import {
  getEntityDetail,
  type EntityDetail,
  type GraphRelation,
} from "../../../lib/api";

const TYPE_COLORS: Record<string, string> = {
  person: "bg-[#818cf8]/15 text-[#818cf8]",
  company: "bg-[#f472b6]/15 text-[#f472b6]",
  project: "bg-[#34d399]/15 text-[#34d399]",
  topic: "bg-[#fbbf24]/15 text-[#fbbf24]",
  place: "bg-[#60a5fa]/15 text-[#60a5fa]",
  event: "bg-[#fb923c]/15 text-[#fb923c]",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function RelationCard({
  relation,
  entityId,
  onNavigate,
}: {
  relation: GraphRelation;
  entityId: number;
  onNavigate: (id: number) => void;
}) {
  const isSource = relation.source_id === entityId;
  const otherName = isSource ? relation.target_name : relation.source_name;
  const otherId = isSource ? relation.target_id : relation.source_id;
  const direction = isSource ? "to" : "from";

  return (
    <button
      onClick={() => onNavigate(otherId)}
      className="flex items-center gap-2 rounded-lg border border-surface-2 bg-surface-1 px-3 py-2 text-left text-sm transition-colors hover:border-accent/30"
    >
      <span className="text-text-tertiary">{relation.relation_type}</span>
      <span className="text-[10px] text-text-tertiary">{direction}</span>
      <span className="font-medium text-accent">{otherName}</span>
    </button>
  );
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
    if (!userId) {
      router.push("/login");
      return;
    }
    setLoading(true);
    getEntityDetail(entityId, userId)
      .then(setEntity)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [entityId, userId, router]);

  const navigateToEntity = useCallback(
    (id: number) => {
      router.push(`/entity/${id}`);
    },
    [router]
  );

  const prefillChat = useCallback(
    (skill: string, topic: string) => {
      // Store in sessionStorage so chat page can pick it up
      sessionStorage.setItem("kuro_prefill", `/${skill} ${topic}`);
      router.push("/");
    },
    [router]
  );

  if (!userId) return null;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-0">
        <div className="space-y-4 text-center">
          <div className="mx-auto h-8 w-48 animate-pulse rounded bg-surface-2" />
          <div className="mx-auto h-4 w-32 animate-pulse rounded bg-surface-2" />
        </div>
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="flex h-full items-center justify-center bg-surface-0">
        <div className="text-center">
          <p className="text-text-tertiary">{error || "Entity not found"}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="mt-4 text-sm text-accent hover:underline"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const typeBadge = TYPE_COLORS[entity.entity_type] || "bg-surface-2 text-text-tertiary";

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface-0 text-text-primary">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-6 py-6">
        {/* Back link */}
        <button
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-1 text-xs text-text-tertiary transition-colors hover:text-text-primary"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M10 4L6 8L10 12" />
          </svg>
          Dashboard
        </button>

        {/* Header */}
        <div>
          <div className="mb-2 flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-text-primary">
              {entity.name}
            </h1>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${typeBadge}`}>
              {entity.entity_type}
            </span>
          </div>
          {entity.summary && (
            <p className="text-sm text-text-secondary">{entity.summary}</p>
          )}
          <p className="mt-1 text-xs text-text-tertiary">
            Created {formatDate(entity.created_at)}
          </p>
        </div>

        {/* Facts */}
        <div>
          <h2 className="mb-3 text-sm font-medium text-text-primary">
            Facts ({entity.facts.length})
          </h2>
          {entity.facts.length > 0 ? (
            <div className="space-y-2">
              {entity.facts.map((fact) => (
                <div
                  key={fact.id}
                  className="rounded-lg border border-surface-2 bg-surface-1 px-4 py-3"
                >
                  <p className="text-sm text-text-primary">{fact.content}</p>
                  <div className="mt-1 flex gap-3 text-[10px] text-text-tertiary">
                    <span>Source: {fact.source}</span>
                    <span>{formatDate(fact.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-tertiary">No facts recorded yet.</p>
          )}
        </div>

        {/* Relations */}
        <div>
          <h2 className="mb-3 text-sm font-medium text-text-primary">
            Relations ({entity.relations.length})
          </h2>
          {entity.relations.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {entity.relations.map((rel) => (
                <RelationCard
                  key={rel.id}
                  relation={rel}
                  entityId={entityId}
                  onNavigate={navigateToEntity}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-tertiary">No relations yet.</p>
          )}
        </div>

        {/* Actions */}
        <div>
          <h2 className="mb-3 text-sm font-medium text-text-primary">
            Actions
          </h2>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => prefillChat("study", entity.name)}
              className="rounded-full border border-surface-3 px-4 py-2 text-sm text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
            >
              Study this topic
            </button>
            <button
              onClick={() => prefillChat("explain", entity.name)}
              className="rounded-full border border-surface-3 px-4 py-2 text-sm text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
            >
              Explain in depth
            </button>
            <button
              onClick={() => prefillChat("deep-research", entity.name)}
              className="rounded-full border border-surface-3 px-4 py-2 text-sm text-text-secondary transition-colors hover:border-accent/40 hover:text-text-primary"
            >
              Deep research
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
