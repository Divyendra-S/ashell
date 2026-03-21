---
name: review
description: Analyze knowledge base health — find orphan entities, sparse topics, and suggest areas to enrich
mode: query
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

### Orphan Entities
- Entities with 0 facts stored about them (just a name, no substance)
- Entities with 0 relations (isolated nodes in the graph)

### Sparse Topics
- Topics with only 1 article
- Entities mentioned in articles but never formally stored

### Rich Areas
- Topics with the most facts, relations, and articles
- Well-connected entities (many relations)

## Step 3: Report
Present a structured KB health report:
- **Overview**: Total articles, entities, facts, relations
- **Richest Topics**: Top 3-5 best-covered areas
- **Sparse Areas**: Topics that need more content
- **Orphan Entities**: Entities to either enrich or clean up
- **Suggestions**: 3-5 specific actions to improve KB quality (e.g., "Add facts about X", "Ingest an article about Y to connect it to Z")

## Gotchas
- **Don't suggest removing orphans immediately** — the user may plan to enrich them later. Frame as "these could use more detail" rather than "these should be deleted."
- **Keep the report scannable.** Use bullet points and counts, not paragraphs.
- **This is about the KB, not general knowledge.** Don't suggest topics the user "should" know — only surface what's already partially in the KB that could be improved.
