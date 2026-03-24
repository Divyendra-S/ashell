"use client";

import type { Article } from "../lib/api";

function getDomain(url: string | null): string {
  if (!url) return "local";
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return "link";
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function ArticleCard({ article }: { article: Article }) {
  return (
    <div className="group rounded-xl border border-surface-2 bg-surface-1 p-4 transition-colors hover:border-accent/30">
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-text-primary line-clamp-2">
          {article.title}
        </h3>
        {article.is_read ? (
          <span className="shrink-0 rounded-full bg-mode-query/15 px-2 py-0.5 text-[10px] font-medium text-mode-query">
            read
          </span>
        ) : (
          <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-text-tertiary">
            unread
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 text-xs text-text-tertiary">
        <span>{getDomain(article.url)}</span>
        <span>{article.chunk_count} chunks</span>
        <span>{formatDate(article.created_at)}</span>
      </div>
      {article.url && (
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-xs text-accent hover:underline"
        >
          Open source
        </a>
      )}
    </div>
  );
}

export function ArticlesLibrary({ articles }: { articles: Article[] }) {
  if (!articles.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-xl border border-surface-2 bg-surface-1">
        <p className="text-sm text-text-tertiary">
          No articles yet. Use /ingest-url to add articles.
        </p>
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
