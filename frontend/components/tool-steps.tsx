"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { ToolStep } from "../lib/api";

const TOOL_LABELS: Record<string, string> = {
  // Query tools
  get_facts_for_entity: "Looking up facts",
  get_relations_for_entity: "Checking relationships",
  traverse_relations: "Exploring connections",
  grep_articles: "Searching articles",
  read_article: "Reading article",
  list_articles: "Listing articles",
  save_memory: "Saving memory",
  list_memories: "Checking memories",
  delete_memory: "Removing memory",
  search_memories: "Searching memories",
  update_profile: "Updating profile",
  // Ingest tools
  store_entity: "Storing concept",
  store_fact: "Storing fact",
  store_relation: "Linking concepts",
  scrape_url: "Fetching page",
  lookup_entity: "Checking knowledge base",
  save_article: "Saving article",
  store_passage: "Storing passage",
  // Skill tools
  read_skill_data: "Loading skill data",
  append_skill_data: "Saving skill data",
  analyze_study_progress: "Analyzing study progress",
  kb_health_report: "Analyzing knowledge base",
};

function getStepLabel(step: ToolStep): string {
  const base = TOOL_LABELS[step.tool] ?? step.tool;
  const entity =
    (step.args.entity_name as string) ??
    (step.args.name as string) ??
    (step.args.source_name as string);
  const pattern = (step.args.pattern as string) ?? (step.args.query as string);
  const url = step.args.url as string;

  if (entity) return `${base}: ${entity}`;
  if (pattern) return `${base}: "${pattern}"`;
  if (url) {
    try {
      return `${base}: ${new URL(url).hostname}`;
    } catch {
      return `${base}: ${url.slice(0, 30)}`;
    }
  }
  return base;
}

export function ToolSteps({ steps, collapsed = false }: { steps?: ToolStep[]; collapsed?: boolean }) {
  if (!steps || steps.length === 0) return null;

  // Deduplicate: keep the latest status for each tool invocation
  const deduplicated: ToolStep[] = [];
  for (const step of steps) {
    const existing = deduplicated.findIndex(
      (s) => s.tool === step.tool && JSON.stringify(s.args) === JSON.stringify(step.args),
    );
    if (existing >= 0) {
      deduplicated[existing] = step;
    } else {
      deduplicated.push(step);
    }
  }

  return (
    <motion.div
      animate={{
        height: collapsed ? 0 : "auto",
        opacity: collapsed ? 0 : 1,
        marginBottom: collapsed ? 0 : 8,
      }}
      transition={{
        height: { duration: 0.35, ease: [0.4, 0, 0.2, 1] },
        opacity: { duration: 0.25 },
      }}
      style={{ overflow: "hidden" }}
    >
      {/* Vertical timeline with connected dots */}
      <div className="relative pl-[14px]">
        {/* Vertical line connecting all dots */}
        {deduplicated.length > 1 && (
          <div
            className="absolute left-[4.5px] top-[6px] w-px bg-surface-2/60"
            style={{ height: `calc(100% - 12px)` }}
          />
        )}

        <AnimatePresence mode="popLayout">
          {deduplicated.map((step, i) => {
            const isDone = step.status === "done";
            const isLast = i === deduplicated.length - 1;
            const stepKey = `${step.tool}-${JSON.stringify(step.args)}`;
            return (
              <motion.div
                key={stepKey}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
                className={`relative flex items-center gap-2.5 text-[12px] ${
                  i < deduplicated.length - 1 ? "pb-2" : ""
                }`}
              >
                {/* Dot */}
                <div className="absolute -left-[14px] flex items-center justify-center">
                  {isDone ? (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 500, damping: 20 }}
                      className="h-[9px] w-[9px] rounded-full bg-text-tertiary/40"
                    />
                  ) : (
                    <span className="relative flex items-center justify-center">
                      <span className="absolute h-[11px] w-[11px] rounded-full bg-accent/30 animate-ping" />
                      <span className="h-[9px] w-[9px] rounded-full bg-accent" />
                    </span>
                  )}
                </div>

                {/* Label */}
                <motion.span
                  animate={{ opacity: isDone ? 0.45 : 1 }}
                  transition={{ duration: 0.3 }}
                  className={isDone ? "text-text-tertiary" : "step-shimmer text-accent"}
                >
                  {getStepLabel(step)}
                </motion.span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
