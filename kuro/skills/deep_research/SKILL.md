---
name: deep-research
description: Multi-pass deep research with cross-referencing and structured report
triggers:
  - "research"
  - "deep dive"
  - "deep research"
  - "investigate"
  - "thorough analysis"
---

# Deep Research Workflow

You are performing a deep research task. Follow this multi-pass workflow:

## Pass 1: Decompose
- Break the user's question into 3-5 sub-questions that cover different angles
- List these sub-questions before proceeding

## Pass 2: Retrieve
- For each sub-question, perform a separate retrieval using available tools
- Use `grep_wiki` to search across wiki pages, then `read_wiki_page` to load relevant pages and follow `[[backlinks]]`
- Use `grep_articles` and `read_article` to find relevant article content
- Cast a wide net — retrieve more than you think you need

## Pass 3: Cross-Reference
- Identify where sources agree, disagree, or complement each other
- Note any gaps in the knowledge base
- Flag contradictions explicitly

## Pass 4: Synthesize
- Produce a structured report with:
  - **Executive Summary**: 2-3 sentence answer
  - **Detailed Findings**: organized by sub-question, with citations
  - **Connections**: how different pieces of knowledge relate
  - **Gaps**: what the knowledge base doesn't cover
  - **Sources**: list all articles and entities referenced

Always cite which article or entity each claim comes from. If the KB lacks information, say so clearly rather than speculating.

## Save Research Log
After completing the report:
- Save detailed log using `append_skill_data` to `research_log.jsonl`:
  - `{"query": "...", "date": "...", "sub_questions": [...], "sources_used": [...], "gaps_found": [...]}`
- Also use `update_memories` to update the user's memory with a summary:
  - name: `research_{topic}_latest`, type: `context`
  - content: "Researched {topic} ({date}). Key findings: {summary}. Gaps: {list}. Sources: {count} articles, {count} entities."
  - This helps future research sessions build on past findings without re-reading logs

## Gotchas
- **Never fabricate connections.** If two topics aren't linked via wiki backlinks, don't invent a relationship. State "no direct connection found in KB" instead.
- **Sparse wikis are normal.** If the KB only has 1-2 sources on a sub-question, say so in the Gaps section rather than over-interpreting thin data.
- **Use `read_article` for depth.** Chunk-based retrieval may miss important context. When a chunk looks relevant, load the full article before synthesizing.
- For the report format, see `report_template.md` in this skill folder.
