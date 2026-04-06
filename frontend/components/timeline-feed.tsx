"use client";

import React from "react";
import type { TimelineEntry } from "../lib/api";

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  checkin: { color: "bg-accent/15 text-accent", label: "Check-in" },
  article: { color: "bg-mode-ingest/15 text-mode-ingest", label: "Article" },
  concept: { color: "bg-mode-query/15 text-mode-query", label: "Concept" },
  goal_set: { color: "bg-amber-500/12 text-amber-600 dark:text-amber-400", label: "Goal" },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function TimelineItem({ entry }: { entry: TimelineEntry }) {
  const config = TYPE_CONFIG[entry.type] || { color: "bg-surface-2/30 text-text-tertiary", label: entry.type };

  let description = "";
  switch (entry.type) {
    case "checkin": description = (entry.data.summary as string) || `Session with ${entry.data.entry_count} entries`; break;
    case "article": description = entry.data.title as string; break;
    case "concept": description = entry.data.name as string; break;
    case "goal_set": {
      description = entry.data.content as string;
      if (entry.data.completed_at) description += " (completed)";
      break;
    }
  }

  return (
    <div className="flex gap-3">
      <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${config.color}`}>
        <div className="h-1.5 w-1.5 rounded-full bg-current" />
      </div>
      <div className="min-w-0 flex-1 pb-0.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium text-text-secondary">{config.label}</span>
          <span className="text-[9px] text-text-tertiary">{formatTime(entry.date)}</span>
        </div>
        <p className="mt-0.5 text-[13px] leading-snug text-text-primary line-clamp-2">{description}</p>
      </div>
    </div>
  );
}

export function TimelineFeed({ timeline }: { timeline: TimelineEntry[] }) {
  if (!timeline.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-2xl border border-surface-2/30">
        <p className="text-[13px] text-text-tertiary">No activity yet</p>
      </div>
    );
  }

  const groups: Map<string, TimelineEntry[]> = new Map();
  for (const entry of timeline) {
    const day = entry.date.slice(0, 10);
    if (!groups.has(day)) groups.set(day, []);
    groups.get(day)!.push(entry);
  }

  return (
    <div className="space-y-6">
      {Array.from(groups.entries()).map(([day, entries]) => (
        <div key={day}>
          <h3 className="mb-3 text-[10px] font-medium uppercase tracking-wider text-text-tertiary">
            {formatDate(day + "T00:00:00Z")}
          </h3>
          <div className="space-y-3 border-l border-surface-2/30 pl-4">
            {entries.map((entry, i) => (
              <TimelineItem key={`${day}-${i}`} entry={entry} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
