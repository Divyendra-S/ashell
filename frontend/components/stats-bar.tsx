"use client";

import type { Stats, GrowthDay } from "../lib/api";

function Sparkline({ data }: { data: GrowthDay[] }) {
  if (!data.length) return null;
  const values = data.map((d) => d.entities + d.facts + d.articles);
  const max = Math.max(...values, 1);
  const w = 120;
  const h = 32;
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * w},${h - (v / max) * h}`)
    .join(" ");

  return (
    <svg width={w} height={h} className="text-accent">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StatCard({
  label,
  value,
  delta,
}: {
  label: string;
  value: number;
  delta?: number;
}) {
  return (
    <div className="rounded-xl border border-surface-2 bg-surface-1 px-4 py-3">
      <p className="text-xs text-text-tertiary">{label}</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-text-primary">{value}</span>
        {delta !== undefined && delta > 0 && (
          <span className="text-xs font-medium text-mode-query">+{delta}</span>
        )}
      </div>
    </div>
  );
}

function HealthBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "text-mode-query"
      : score >= 50
        ? "text-yellow-400"
        : "text-red-400";

  return (
    <div className="rounded-xl border border-surface-2 bg-surface-1 px-4 py-3">
      <p className="text-xs text-text-tertiary">KB Health</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className={`text-2xl font-semibold ${color}`}>{score}</span>
        <span className="text-xs text-text-tertiary">/ 100</span>
      </div>
    </div>
  );
}

export function StatsBar({
  stats,
  growth,
}: {
  stats: Stats | null;
  growth: GrowthDay[];
}) {
  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-20 animate-pulse rounded-xl border border-surface-2 bg-surface-1"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <StatCard label="Entities" value={stats.entity_count} delta={stats.new_entities_7d} />
      <StatCard label="Facts" value={stats.fact_count} delta={stats.new_facts_7d} />
      <StatCard label="Articles" value={stats.article_count} delta={stats.new_articles_7d} />
      <StatCard label="Relations" value={stats.relation_count} />
      <HealthBadge score={stats.health_score} />
      <div className="flex items-center justify-center rounded-xl border border-surface-2 bg-surface-1 px-4 py-3">
        <div>
          <p className="mb-1 text-xs text-text-tertiary">30d Growth</p>
          <Sparkline data={growth} />
        </div>
      </div>
    </div>
  );
}
