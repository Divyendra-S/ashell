"use client";

import { completeGoal } from "../lib/api";

interface Goal {
  id: number;
  content: string;
  created_at: string;
  completed_at?: string | null;
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
    <div className="space-y-4">
      {/* Pending */}
      {pendingGoals.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {pendingGoals.map((g) => (
            <label
              key={g.id}
              className="group flex cursor-pointer items-center gap-2 rounded-full border border-surface-2/30 px-3 py-1.5 text-[12px] text-text-secondary transition-all duration-200 hover:border-accent/25 hover:text-text-primary"
            >
              <input
                type="checkbox"
                onChange={() => handleComplete(g.id)}
                className="h-3 w-3 rounded border-surface-3/30 bg-transparent accent-accent"
              />
              <span>{g.content}</span>
            </label>
          ))}
        </div>
      )}

      {/* Completed */}
      {completedGoals.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {completedGoals.map((g) => (
            <div
              key={g.id}
              className="flex items-center gap-2 rounded-full border border-surface-2/20 px-3 py-1.5 text-[12px] text-text-tertiary line-through"
            >
              <input type="checkbox" checked disabled className="h-3 w-3 rounded border-surface-3/20 bg-transparent accent-accent" />
              <span>{g.content}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
