"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useUser } from "../../lib/user";
import {
  getGraph,
  getStats,
  getGrowth,
  getArticles,
  type GraphData,
  type Stats,
  type GrowthDay,
  type Article,
} from "../../lib/api";
import { KnowledgeGraph } from "../../components/knowledge-graph";
import { ArticlesLibrary } from "../../components/article-card";

type Tab = "graph" | "articles";

const TABS: { key: Tab; label: string }[] = [
  { key: "graph", label: "Graph" },
  { key: "articles", label: "Articles" },
];

export default function DashboardPage() {
  const { userId } = useUser();
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [growth, setGrowth] = useState<GrowthDay[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [articleError, setArticleError] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("graph");

  useEffect(() => {
    if (!userId) {
      router.push("/login");
      return;
    }
    getStats(userId).then(setStats).catch(console.error);
    getGrowth(userId).then(setGrowth).catch(console.error);
    getGraph(userId).then(setGraphData).catch(console.error);
    getArticles(userId).then(setArticles).catch((err) => {
      console.error("Articles fetch failed:", err);
      setArticleError(true);
    });
  }, [userId, router]);

  if (!userId) return null;

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-surface-0 text-text-primary">
      {/* Tab switcher — floating top-center */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2, ease: "easeOut" }}
        className="absolute left-1/2 top-4 z-30 flex -translate-x-1/2 rounded-full border border-surface-2/35 bg-surface-0/60 p-[3px] backdrop-blur-xl"
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`relative z-10 rounded-full px-4 py-1.5 text-[12px] transition-colors duration-200 ${
              activeTab === tab.key
                ? "font-medium text-white"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            {activeTab === tab.key && (
              <motion.div
                layoutId="tab-indicator"
                className="absolute inset-0 rounded-full bg-accent/90"
                style={{ boxShadow: "0 0 16px -4px rgba(129, 140, 248, 0.3)" }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
              />
            )}
            <span className="relative z-10">
              {tab.label}
              {tab.key === "articles" &&
                ` (${articleError ? "!" : articles.length})`}
            </span>
          </button>
        ))}
      </motion.div>

      {/* Content — full height */}
      <AnimatePresence mode="wait">
        {activeTab === "graph" ? (
          <motion.div
            key="graph"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <KnowledgeGraph data={graphData} userId={userId} stats={stats} />
          </motion.div>
        ) : (
          <motion.div
            key="articles"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="h-full overflow-y-auto px-6 pt-16 pb-8"
          >
            <div className="mx-auto max-w-7xl">
              <ArticlesLibrary articles={articles} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
