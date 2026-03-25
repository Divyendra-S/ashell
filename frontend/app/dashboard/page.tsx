"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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
import { StatsBar } from "../../components/stats-bar";
import { KnowledgeGraph } from "../../components/knowledge-graph";
import { ArticlesLibrary } from "../../components/article-card";

type Tab = "graph" | "articles";

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
    <div className="flex h-full flex-col overflow-y-auto bg-surface-0 text-text-primary">
      {/* Header + Stats constrained */}
      <div className="mx-auto w-full max-w-6xl space-y-6 px-6 pt-6">
        <div>
          <h1 className="text-lg font-medium text-text-primary">
            Knowledge Explorer
          </h1>
          <p className="text-sm text-text-tertiary">
            Visualize and browse your knowledge base
          </p>
        </div>
        <StatsBar stats={stats} growth={growth} />
      </div>

      {/* Tabs + Content full-width */}
      <div className="w-full space-y-4 px-6 py-4">
        <div className="flex gap-1 rounded-lg bg-surface-1 p-1 w-fit">
          <button
            onClick={() => setActiveTab("graph")}
            className={`rounded-md px-4 py-2 text-sm transition-colors ${
              activeTab === "graph"
                ? "bg-surface-2 text-text-primary"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            Knowledge Graph
          </button>
          <button
            onClick={() => setActiveTab("articles")}
            className={`rounded-md px-4 py-2 text-sm transition-colors ${
              activeTab === "articles"
                ? "bg-surface-2 text-text-primary"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            Articles ({articleError ? "!" : articles.length})
          </button>
        </div>

        {activeTab === "graph" && <KnowledgeGraph data={graphData} userId={userId} />}
        {activeTab === "articles" && (
          <div className="mx-auto max-w-6xl">
            <ArticlesLibrary articles={articles} />
          </div>
        )}
      </div>
    </div>
  );
}
