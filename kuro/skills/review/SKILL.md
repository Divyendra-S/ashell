---
name: review
description: Analyze knowledge base health — find orphan entities, sparse topics, and suggest areas to enrich
triggers:
  - "review my KB"
  - "knowledge health"
  - "KB stats"
  - "what do I know"
  - "knowledge base status"
guards:
  - read_only
---

# Knowledge Base Review Workflow

You are performing a health check on the user's knowledge base. Follow this workflow:

## Step 1: Inventory
- Call `kb_health_report` to get a comprehensive analysis — entity counts, orphans, sparse topics, and suggestions
- Use `list_articles` to get all saved articles for additional context
- Use the health report data to structure your findings

## Step 2: Find Issues
Identify and categorize problems:

### Orphan Pages
- Wiki pages with no meaningful content (just a title, no substance)
- Wiki pages with no [[backlinks]] to or from other pages (isolated)

### Sparse Topics
- Topics with only 1 article
- Concepts mentioned in articles but without a wiki page

### Rich Areas
- Topics with the most detailed wiki pages and articles
- Well-connected pages (many [[backlinks]])

## Step 3: Report
Present a structured KB health report:
- **Overview**: Total articles, wiki pages, and [[backlink]] connections
- **Richest Topics**: Top 3-5 best-covered areas
- **Sparse Areas**: Topics that need more content
- **Orphan Pages**: Pages to either enrich or clean up
- **Suggestions**: 3-5 specific actions to improve KB quality (e.g., "Expand the wiki page for X", "Ingest an article about Y and link it to Z")

## Gotchas
- **Don't suggest removing orphan pages immediately** — the user may plan to enrich them later. Frame as "these could use more detail" rather than "these should be deleted."
- **Keep the report scannable.** Use bullet points and counts, not paragraphs.
- **This is about the KB, not general knowledge.** Don't suggest topics the user "should" know — only surface what's already partially in the KB that could be improved.
