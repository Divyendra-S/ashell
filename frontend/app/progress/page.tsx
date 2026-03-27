"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "../../lib/user";
import { getTimeline, getStreak, type TimelineEntry, type StreakData } from "../../lib/api";
import { ActivityHeatmap } from "../../components/activity-heatmap";
import { TimelineFeed } from "../../components/timeline-feed";
import { GoalTracker } from "../../components/goal-tracker";

export default function ProgressPage() {
  const { userId } = useUser();
  const router = useRouter();
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [streak, setStreak] = useState<StreakData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) { router.push("/login"); return; }
    Promise.all([getTimeline(userId, 90), getStreak(userId)])
      .then(([tl, st]) => { setTimeline(tl); setStreak(st); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [userId, router]);

  const handleGoalCompleted = useCallback((goalId: number) => {
    setTimeline((prev) =>
      prev.map((e) =>
        e.type === "goal_set" && (e.data as any).id === goalId
          ? { ...e, data: { ...e.data, completed_at: new Date().toISOString() } }
          : e
      )
    );
  }, []);

  if (!userId) return null;

  const goalEntries = timeline.filter((e) => e.type === "goal_set");
  const pendingGoals = goalEntries
    .filter((e) => !e.data.completed_at)
    .map((e) => ({ id: e.data.id as number, content: e.data.content as string, created_at: e.date }));
  const completedGoals = goalEntries
    .filter((e) => e.data.completed_at)
    .slice(0, 10)
    .map((e) => ({ id: e.data.id as number, content: e.data.content as string, created_at: e.date, completed_at: e.data.completed_at as string }));

  return (
    <div className="gradient-page flex h-full flex-col overflow-y-auto bg-surface-0 text-text-primary">
      <div className="mx-auto w-full max-w-5xl px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-xl font-extralight tracking-tight text-text-primary">Progress</h1>
          <p className="mt-1 text-[13px] text-text-tertiary">Track your learning journey and goals</p>
        </div>

        {/* Streak + Heatmap */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className="flex shrink-0 flex-col items-center rounded-2xl border border-surface-2/35 bg-surface-1/50 px-6 py-5">
            {streak ? (
              <>
                <span className="text-[36px] font-extralight tracking-tight text-accent">{streak.current}</span>
                <span className="text-[11px] text-text-tertiary">day streak</span>
                <div className="mt-2 flex gap-3 text-[10px] text-text-tertiary">
                  <span>Best: {streak.longest}d</span>
                  <span>Total: {streak.total_active_days}d</span>
                </div>
              </>
            ) : (
              <div className="h-16 w-16 animate-pulse rounded-lg bg-surface-2/20" />
            )}
          </div>
          <div className="flex-1 rounded-2xl border border-surface-2/35 bg-surface-1/50 p-5">
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
              Activity (last 90 days)
            </p>
            {loading ? (
              <div className="h-24 animate-pulse rounded-lg bg-surface-2/15" />
            ) : (
              <ActivityHeatmap timeline={timeline} />
            )}
          </div>
        </div>

        {/* Timeline + Goals */}
        <div className="grid gap-8 lg:grid-cols-[1fr_280px]">
          <div>
            <h2 className="mb-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
              Activity Feed
            </h2>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-14 animate-pulse rounded-xl bg-surface-1/40" />
                ))}
              </div>
            ) : (
              <TimelineFeed timeline={timeline} />
            )}
          </div>
          <div>
            <h2 className="mb-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
              Goals
            </h2>
            <GoalTracker
              pendingGoals={pendingGoals}
              completedGoals={completedGoals}
              userId={userId}
              onGoalCompleted={handleGoalCompleted}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
