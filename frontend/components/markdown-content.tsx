"use client";

import { useDeferredValue, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mb-2 mt-4 text-lg font-semibold text-text-primary">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-1.5 mt-3 text-base font-semibold text-text-primary">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-1 mt-2 text-sm font-semibold text-text-primary">{children}</h3>
  ),
  p: ({ children }) => <p className="mb-2 leading-[1.7]">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
  em: ({ children }) => <em className="italic text-text-secondary">{children}</em>,
  code: ({ className, children, ...props }) => {
    const isBlock = className?.startsWith("language-");
    if (isBlock) {
      return (
        <code className={`text-[13px] font-mono text-text-secondary ${className ?? ""}`} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-surface-1 px-1.5 py-0.5 text-[13px] font-mono text-accent" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-surface-1 p-3">{children}</pre>
  ),
  ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-1">{children}</ol>,
  li: ({ children }) => <li className="leading-[1.6]">{children}</li>,
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="min-w-full border-collapse text-[13px]">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-surface-2 px-3 py-1.5 text-left font-medium text-text-secondary">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-surface-2/30 px-3 py-1.5 text-text-primary">{children}</td>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-accent/30 pl-3 italic text-text-secondary">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-accent underline decoration-accent/30 hover:decoration-accent"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
};

export function MarkdownContent({ content, streaming = false }: { content: string; streaming?: boolean }) {
  if (!content) return null;

  const displayContent = useDeferredValue(content);

  const rendered = useMemo(
    () => (
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {displayContent}
      </ReactMarkdown>
    ),
    [displayContent],
  );

  return (
    <div className="text-[14px] leading-[1.7] text-text-primary">
      {rendered}
    </div>
  );
}
