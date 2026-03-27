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
    <div className="group rounded-2xl border border-surface-2/35 bg-surface-05 p-4 transition-all duration-200 hover:border-accent/15 hover:bg-surface-1">
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
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-surface-2/40 py-16">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-mode-ingest/8">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="text-mode-ingest">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
        </div>
        <p className="mb-1 text-[13px] text-text-secondary">No articles yet</p>
        <p className="mb-4 text-[11px] text-text-tertiary">Use /ingest-url in chat to add your first article</p>
        <button
          onClick={() => {
            sessionStorage.setItem("kuro_prefill", "/ingest-url ");
            window.location.href = "/";
          }}
          className="rounded-full border border-accent/20 bg-accent/5 px-4 py-2 text-[12px] text-accent transition-all duration-200 hover:border-accent/35 hover:bg-accent/10"
        >
          Ingest a URL
        </button>
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
