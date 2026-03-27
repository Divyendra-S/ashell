"use client";

import { completeGoal } from "../lib/api";

interface Goal {
  id: number;
  content: string;
  created_at: string;
  completed_at?: string | null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function GoalTracker({
  pendingGoals,
  completedGoals,
  userId,
  onGoalCompleted,
}: {
  pendingGoals: Goal[];
  completedGoals: Goal[];
  userId: string;
  onGoalCompleted: (goalId: number) => void;
}) {
  async function handleComplete(goalId: number) {
    await completeGoal(goalId, userId);
    onGoalCompleted(goalId);
  }

  return (
    <div className="space-y-5">
      {/* Pending */}
      {pendingGoals.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Pending</p>
          {pendingGoals.map((g) => (
            <label
              key={g.id}
              className="flex cursor-pointer items-start gap-2 text-[12px] text-text-secondary transition-colors hover:text-text-primary"
            >
              <input
                type="checkbox"
                onChange={() => handleComplete(g.id)}
                className="mt-0.5 h-3 w-3 rounded border-surface-3/30 bg-transparent accent-accent"
              />
              <div>
                <span>{g.content}</span>
                <span className="ml-1.5 text-[10px] text-text-tertiary">{formatDate(g.created_at)}</span>
              </div>
            </label>
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-text-tertiary">No pending goals</p>
      )}

      {/* Completed */}
      {completedGoals.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">Completed</p>
          {completedGoals.map((g) => (
            <div key={g.id} className="flex items-start gap-2 text-[12px] text-text-tertiary line-through">
              <input type="checkbox" checked disabled className="mt-0.5 h-3 w-3 rounded border-surface-3/20 bg-transparent accent-accent" />
              <span>{g.content}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
