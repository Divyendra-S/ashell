# Agent Context Building

The practice of equipping AI agents with active search tools (like Grep) to independently gather their own context, rather than passively feeding them pre-indexed data. This leverages improving model intelligence to find precise information dynamically.

## Key Facts
- As AI models become more capable, they are better served by tools that let them actively search for context rather than passively receiving pre-indexed RAG results. For example, giving Claude a Grep tool allowed it to explore codebases dynamically. This proved less fragile than a vector database and enabled nested searches across several layers of files to find precise context.

## Connections
- [[Progressive Disclosure (AI)]] (enables) — Context building tools allow an agent to actively explore its environment, which provides the foundation needed to implement progressive disclosure instead of relying on front-loaded context.

## Source Passages
> When Claude Code first came out, we used a RAG vector database to find context for Claude. While RAG was powerful and fast it required indexing and setup and could be fragile across a host of different environments. More importantly, Claude was given this context instead of finding the context itself. But if Claude could search on the web, why not search your codebase? By giving Claude a Grep tool, we could let it search for files and build context itself.
> — [Lessons from Building Claude Code: Seeing like an Agent](local://claude-code-lessons)

