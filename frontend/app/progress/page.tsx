"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useUser } from "../../lib/user";
import { useBackend } from "../../lib/backend";
import { getTimeline, getStreak, type TimelineEntry, type StreakData } from "../../lib/api";
import { ActivityHeatmap } from "../../components/activity-heatmap";
import { TimelineFeed } from "../../components/timeline-feed";
import { GoalTracker } from "../../components/goal-tracker";

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35, delay, ease: "easeOut" as const },
});

export default function ProgressPage() {
  const { userId } = useUser();
  const { backend } = useBackend();
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
  }, [userId, backend, router]);

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
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-extralight tracking-tight text-text-primary">Progress</h1>
            {!loading && (
              <motion.div {...fadeUp(0)} className="flex items-center gap-1.5">
                <span className="rounded-full bg-accent/8 px-2 py-[2px] text-[10px] font-medium text-accent">
                  {timeline.length} events
                </span>
                {streak && (
                  <span className="rounded-full bg-mode-query/8 px-2 py-[2px] text-[10px] font-medium text-mode-query">
                    {streak.total_active_days} active days
                  </span>
                )}
              </motion.div>
            )}
          </div>
          <p className="mt-1 text-[13px] text-text-tertiary">Track your learning journey and goals</p>
        </div>

        {loading ? (
          <div className="space-y-8">
            {/* Skeleton: top row */}
            <div className="grid grid-cols-3 gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 skeleton" />
              ))}
            </div>
            <div className="h-28 skeleton" />
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-14 skeleton" />
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Stats — compact inline row */}
            <motion.div {...fadeUp(0)} className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2">
              <div className="flex items-baseline gap-1.5">
                <span className="text-[20px] font-extralight tracking-tight text-accent">{streak?.current ?? 0}</span>
                <span className="text-[11px] text-text-tertiary">day streak</span>
                {streak && streak.current > 0 && (
                  <span className="ml-1 text-[9px] font-medium text-mode-query">· Keep it going!</span>
                )}
              </div>
              <span className="hidden text-surface-2 sm:inline">|</span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-[20px] font-extralight tracking-tight text-text-primary">{streak?.longest ?? 0}</span>
                <span className="text-[11px] text-text-tertiary">best</span>
              </div>
              <span className="hidden text-surface-2 sm:inline">|</span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-[20px] font-extralight tracking-tight text-text-primary">{pendingGoals.length}</span>
                <span className="text-[11px] text-text-tertiary">open goals</span>
              </div>
              <span className="hidden text-surface-2 sm:inline">|</span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-[20px] font-extralight tracking-tight text-text-primary">{streak?.total_active_days ?? 0}</span>
                <span className="text-[11px] text-text-tertiary">active days</span>
              </div>
            </motion.div>

            {/* Heatmap — full width, no card wrapper */}
            <motion.div {...fadeUp(0.05)} className="mb-8">
              <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                Activity (last 90 days)
              </p>
              <ActivityHeatmap timeline={timeline} />
            </motion.div>

            {/* Goals — horizontal, above timeline */}
            {(pendingGoals.length > 0 || completedGoals.length > 0) && (
              <motion.div {...fadeUp(0.1)} className="mb-8">
                <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                  Goals
                </h2>
                <GoalTracker
                  pendingGoals={pendingGoals}
                  completedGoals={completedGoals}
                  userId={userId}
                  onGoalCompleted={handleGoalCompleted}
                />
              </motion.div>
            )}
            {pendingGoals.length === 0 && completedGoals.length === 0 && (
              <motion.div {...fadeUp(0.1)} className="mb-8 flex items-center gap-3">
                <p className="text-[12px] text-text-tertiary">No goals yet</p>
                <button
                  onClick={() => {
                    sessionStorage.setItem("kuro_prefill", "/goal ");
                    router.push("/");
                  }}
                  className="rounded-full border border-accent/20 px-3 py-1.5 text-[11px] text-accent transition-all duration-200 hover:border-accent/35 hover:bg-accent/5"
                >
                  Set a goal
                </button>
              </motion.div>
            )}

            {/* Activity feed — full width */}
            <motion.div {...fadeUp(0.15)}>
              <h2 className="mb-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                Activity Feed
              </h2>
              {timeline.length > 0 ? (
                <TimelineFeed timeline={timeline} />
              ) : (
                <div className="flex flex-col items-center justify-center py-12">
                  <p className="mb-3 text-[13px] text-text-tertiary">No activity yet</p>
                  <button
                    onClick={() => router.push("/voice")}
                    className="rounded-full border border-accent/20 px-4 py-2 text-[12px] text-accent transition-all duration-200 hover:border-accent/35 hover:bg-accent/5"
                  >
                    Start your first check-in
                  </button>
                </div>
              )}
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
