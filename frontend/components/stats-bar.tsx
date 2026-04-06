"use client";

import { motion } from "framer-motion";
import type { Stats, GrowthDay } from "../lib/api";

function StatCard({
  label,
  value,
  delta,
  index,
}: {
  label: string;
  value: number;
  delta?: number;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.45, ease: "easeOut" }}
      whileHover={{ y: -2, transition: { type: "spring", stiffness: 400, damping: 20 } }}
      className="glow-card group relative overflow-hidden rounded-2xl border border-surface-2/40 bg-surface-1/40 px-5 py-5 backdrop-blur-sm"
    >
      {/* Subtle top gradient wash */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-b from-accent/[0.03] to-transparent" />

      <p className="relative text-[11px] font-medium uppercase tracking-[0.12em] text-text-tertiary">
        {label}
      </p>
      <div className="relative mt-2 flex items-baseline gap-2.5">
        <span className="text-[32px] font-extralight leading-none tracking-tight text-text-primary">
          {value}
        </span>
        {delta !== undefined && delta > 0 && (
          <span className="rounded-full bg-mode-query/8 px-2 py-0.5 text-[10px] font-medium text-mode-query">
            +{delta}
          </span>
        )}
      </div>
    </motion.div>
  );
}

function HealthRing({
  score,
  index,
}: {
  score: number;
  index: number;
}) {
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color =
    score >= 80 ? "#34d399" : score >= 50 ? "#fbbf24" : "#f87171";

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.45, ease: "easeOut" }}
      whileHover={{ y: -2, transition: { type: "spring", stiffness: 400, damping: 20 } }}
      className="glow-card group relative flex items-center gap-4 overflow-hidden rounded-2xl border border-surface-2/40 bg-surface-1/40 px-5 py-5 backdrop-blur-sm"
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-b from-accent/[0.03] to-transparent" />

      <svg width="58" height="58" viewBox="0 0 58 58" className="relative shrink-0">
        <circle
          cx="29"
          cy="29"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          className="text-surface-2/60"
        />
        <motion.circle
          cx="29"
          cy="29"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.2, delay: 0.3, ease: "easeOut" }}
          transform="rotate(-90 29 29)"
          style={{ filter: `drop-shadow(0 0 4px ${color}40)` }}
        />
        <text
          x="29"
          y="31"
          textAnchor="middle"
          className="text-[12px] font-light"
          fill={color}
        >
          {score}
        </text>
      </svg>
      <div className="relative">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-tertiary">
          KB Health
        </p>
        <p className="mt-0.5 text-[10px] text-text-tertiary">/ 100</p>
      </div>
    </motion.div>
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
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-[96px] animate-pulse rounded-2xl border border-surface-2/35 bg-surface-1/50"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      <StatCard
        label="Concepts"
        value={stats.concept_count}
        delta={stats.new_concepts_7d}
        index={0}
      />
      <StatCard
        label="Links"
        value={stats.backlink_count}
        index={1}
      />
      <StatCard
        label="Articles"
        value={stats.article_count}
        delta={stats.new_articles_7d}
        index={2}
      />
      <HealthRing score={stats.health_score} index={3} />
    </div>
  );
}
