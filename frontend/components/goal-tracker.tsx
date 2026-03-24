"use client";

import { completeGoal } from "../lib/api";

interface Goal {
  id: number;
  content: string;
  created_at: string;
  completed_at?: string | null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
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
    <div className="rounded-xl border border-surface-2 bg-surface-1 p-4">
      <h3 className="mb-3 text-sm font-medium text-text-primary">Goals</h3>

      {/* Pending */}
      {pendingGoals.length > 0 ? (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-text-tertiary">
            Pending
          </p>
          {pendingGoals.map((g) => (
            <label
              key={g.id}
              className="flex cursor-pointer items-start gap-2 text-sm text-text-secondary hover:text-text-primary"
            >
              <input
                type="checkbox"
                onChange={() => handleComplete(g.id)}
                className="mt-0.5 h-3.5 w-3.5 rounded border-surface-3 bg-surface-0 accent-accent"
              />
              <div>
                <span>{g.content}</span>
                <span className="ml-2 text-[10px] text-text-tertiary">
                  {formatDate(g.created_at)}
                </span>
              </div>
            </label>
          ))}
        </div>
      ) : (
        <p className="mb-4 text-xs text-text-tertiary">No pending goals</p>
      )}

      {/* Completed */}
      {completedGoals.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-text-tertiary">
            Completed
          </p>
          {completedGoals.map((g) => (
            <div
              key={g.id}
              className="flex items-start gap-2 text-sm text-text-tertiary line-through"
            >
              <input
                type="checkbox"
                checked
                disabled
                className="mt-0.5 h-3.5 w-3.5 rounded border-surface-3 bg-surface-0 accent-accent"
              />
              <span>{g.content}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
