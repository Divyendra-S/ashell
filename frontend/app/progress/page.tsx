"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "../../lib/user";
import {
  getTimeline,
  getStreak,
  type TimelineEntry,
  type StreakData,
} from "../../lib/api";
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
    if (!userId) {
      router.push("/login");
      return;
    }
    Promise.all([getTimeline(userId, 90), getStreak(userId)])
      .then(([tl, st]) => {
        setTimeline(tl);
        setStreak(st);
      })
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

  // Extract goals from timeline
  const goalEntries = timeline.filter((e) => e.type === "goal_set");
  const pendingGoals = goalEntries
    .filter((e) => !e.data.completed_at)
    .map((e) => ({
      id: e.data.id as number,
      content: e.data.content as string,
      created_at: e.date,
    }));
  const completedGoals = goalEntries
    .filter((e) => e.data.completed_at)
    .slice(0, 10)
    .map((e) => ({
      id: e.data.id as number,
      content: e.data.content as string,
      created_at: e.date,
      completed_at: e.data.completed_at as string,
    }));

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface-0 text-text-primary">
      <div className="mx-auto w-full max-w-5xl px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-lg font-medium text-text-primary">Progress</h1>
          <p className="text-sm text-text-tertiary">
            Track your learning journey and goals
          </p>
        </div>

        {/* Streak + Heatmap */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start">
          {/* Streak card */}
          <div className="flex shrink-0 flex-col items-center rounded-xl border border-surface-2 bg-surface-1 px-6 py-4">
            {streak ? (
              <>
                <span className="text-4xl font-bold text-accent">
                  {streak.current}
                </span>
                <span className="text-xs text-text-tertiary">day streak</span>
                <div className="mt-2 flex gap-3 text-[10px] text-text-tertiary">
                  <span>Best: {streak.longest}d</span>
                  <span>Total: {streak.total_active_days}d</span>
                </div>
              </>
            ) : (
              <div className="h-16 w-16 animate-pulse rounded bg-surface-2" />
            )}
          </div>

          {/* Heatmap */}
          <div className="flex-1 rounded-xl border border-surface-2 bg-surface-1 p-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-tertiary">
              Activity (last 90 days)
            </p>
            {loading ? (
              <div className="h-24 animate-pulse rounded bg-surface-2" />
            ) : (
              <ActivityHeatmap timeline={timeline} />
            )}
          </div>
        </div>

        {/* Timeline + Goals */}
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          {/* Timeline */}
          <div>
            <h2 className="mb-3 text-sm font-medium text-text-primary">
              Activity Feed
            </h2>
            {loading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-16 animate-pulse rounded-xl bg-surface-1"
                  />
                ))}
              </div>
            ) : (
              <TimelineFeed timeline={timeline} />
            )}
          </div>

          {/* Goal tracker */}
          <div>
            <h2 className="mb-3 text-sm font-medium text-text-primary">
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
