"use client";

import type { Article } from "../lib/api";

function getDomain(url: string | null): string {
  if (!url) return "local";
  try { return new URL(url).hostname.replace("www.", ""); } catch { return "link"; }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function ArticleCard({ article }: { article: Article }) {
  return (
    <div className="group rounded-2xl border border-surface-2/35 bg-surface-1/45 p-4 transition-all duration-200 hover:border-accent/15 hover:bg-surface-1/40">
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-[13px] font-normal leading-snug text-text-primary line-clamp-2">
          {article.title}
        </h3>
        {article.is_read ? (
          <span className="shrink-0 rounded-full bg-mode-query/8 px-1.5 py-[2px] text-[9px] font-medium text-mode-query">read</span>
        ) : (
          <span className="shrink-0 rounded-full bg-surface-2/30 px-1.5 py-[2px] text-[9px] font-medium text-text-tertiary">new</span>
        )}
      </div>
      <div className="flex items-center gap-2 text-[10px] text-text-tertiary">
        <span>{getDomain(article.url)}</span>
        <span className="text-text-tertiary">·</span>
        <span>{article.chunk_count} chunks</span>
        <span className="text-text-tertiary">·</span>
        <span>{formatDate(article.created_at)}</span>
      </div>
      {article.url && (
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1 text-[10px] text-accent transition-colors hover:text-accent"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0">
            <path d="M3.5 1.5h5v5M8.5 1.5l-7 7" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Open source
        </a>
      )}
    </div>
  );
}

export function ArticlesLibrary({ articles }: { articles: Article[] }) {
  if (!articles.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-2xl border border-surface-2/30 bg-surface-1/40">
        <p className="text-[13px] text-text-tertiary">No articles yet. Use /ingest-url to add articles.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {articles.map((a) => (
        <ArticleCard key={a.id} article={a} />
      ))}
    </div>
  );
}
