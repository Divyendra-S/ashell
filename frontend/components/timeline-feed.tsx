"use client";

import React from "react";
import type { TimelineEntry } from "../lib/api";

const TYPE_ICONS: Record<string, { icon: string; color: string; label: string }> = {
  checkin: { icon: "mic", color: "text-accent", label: "Check-in" },
  article: { icon: "doc", color: "text-mode-ingest", label: "Article Ingested" },
  entity: { icon: "node", color: "text-mode-query", label: "Entity Created" },
  goal_set: { icon: "flag", color: "text-yellow-400", label: "Goal Set" },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function EntryIcon({ type }: { type: string }) {
  const config = TYPE_ICONS[type] || { icon: "dot", color: "text-text-tertiary", label: type };

  const iconSvg: Record<string, React.ReactNode> = {
    mic: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="1" width="6" height="11" rx="3" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      </svg>
    ),
    doc: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
    ),
    node: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v4m0 12v4M2 12h4m12 0h4" />
      </svg>
    ),
    flag: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
        <line x1="4" y1="22" x2="4" y2="15" />
      </svg>
    ),
    dot: <div className="h-2 w-2 rounded-full bg-current" />,
  };

  return (
    <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-2 ${config.color}`}>
      {iconSvg[config.icon]}
    </div>
  );
}

function TimelineItem({ entry }: { entry: TimelineEntry }) {
  const config = TYPE_ICONS[entry.type] || { label: entry.type };

  let description = "";
  switch (entry.type) {
    case "checkin":
      description = (entry.data.summary as string) || `Session with ${entry.data.entry_count} entries`;
      break;
    case "article":
      description = entry.data.title as string;
      break;
    case "entity":
      description = `${entry.data.name} (${entry.data.entity_type})`;
      break;
    case "goal_set": {
      const completed = entry.data.completed_at;
      description = entry.data.content as string;
      if (completed) description += " (completed)";
      break;
    }
  }

  return (
    <div className="flex gap-3">
      <EntryIcon type={entry.type} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-text-secondary">
            {config.label}
          </span>
          <span className="text-[10px] text-text-tertiary">
            {formatTime(entry.date)}
          </span>
        </div>
        <p className="mt-0.5 text-sm text-text-primary line-clamp-2">
          {description}
        </p>
      </div>
    </div>
  );
}

export function TimelineFeed({ timeline }: { timeline: TimelineEntry[] }) {
  if (!timeline.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-xl border border-surface-2 bg-surface-1">
        <p className="text-sm text-text-tertiary">No activity yet</p>
      </div>
    );
  }

  // Group by date
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
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-text-tertiary">
            {formatDate(day + "T00:00:00Z")}
          </h3>
          <div className="space-y-3 border-l border-surface-2 pl-4">
            {entries.map((entry, i) => (
              <TimelineItem key={`${day}-${i}`} entry={entry} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
