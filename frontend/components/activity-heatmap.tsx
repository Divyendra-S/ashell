"use client";

import type { TimelineEntry } from "../lib/api";

const DAYS = 91;
const COLS = 13;
const ROWS = 7;

function getActivityMap(timeline: TimelineEntry[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const entry of timeline) {
    const day = entry.date.slice(0, 10);
    map.set(day, (map.get(day) || 0) + 1);
  }
  return map;
}

function getColor(count: number): string {
  if (count === 0) return "bg-surface-2/30";
  if (count === 1) return "bg-accent/20";
  if (count <= 3) return "bg-accent/35";
  if (count <= 6) return "bg-accent/55";
  return "bg-accent/75";
}

export function ActivityHeatmap({ timeline }: { timeline: TimelineEntry[] }) {
  const activityMap = getActivityMap(timeline);
  const today = new Date();

  const cells: { date: string; count: number }[] = [];
  for (let i = DAYS - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    cells.push({ date: dateStr, count: activityMap.get(dateStr) || 0 });
  }

  return (
    <div className="flex gap-[3px]">
      {Array.from({ length: COLS }).map((_, col) => (
        <div key={col} className="flex flex-col gap-[3px]">
          {Array.from({ length: ROWS }).map((_, row) => {
            const idx = col * ROWS + row;
            const cell = cells[idx];
            if (!cell) return <div key={row} className="h-3 w-3" />;
            return (
              <div
                key={row}
                className={`h-3 w-3 rounded-sm transition-colors ${getColor(cell.count)}`}
                title={`${cell.date}: ${cell.count} activities`}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}
