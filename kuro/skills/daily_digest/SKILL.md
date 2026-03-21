---
name: daily-digest
description: Generate a digest of recent knowledge additions, connections, and review suggestions
mode: query
triggers:
  - "daily digest"
  - "what's new"
  - "catch me up"
  - "daily summary"
  - "what did I learn"
---

# Daily Digest Workflow

You are generating a daily knowledge digest for the user. Follow this workflow:

## Step 1: Recent Activity
- Use `list_articles` to find recently added articles
- Query entities and facts to identify recent additions
- If study session data exists (in skill data), read it for recent scores

## Step 2: Find Connections
- For recently added knowledge, use `traverse_relations` to find how it connects to existing knowledge
- Highlight any surprising or non-obvious connections between new and old content

## Step 3: Generate Digest
Present a structured daily digest:

### What's New
- List of recently ingested articles and entities (with brief descriptions)
- Key facts and relations added

### Connections Discovered
- How new knowledge links to existing KB content
- Any patterns or themes emerging across recent additions

### Review Suggestions
- Topics from recent study sessions with low scores (if available)
- Topics ingested but not yet studied or explored
- Entities that were recently added but lack relations (good candidates for `/teach`)

### Quick Stats
- Total KB size (articles, entities, facts)
- Growth since last digest (if previous digest data is available)

## Gotchas
- **If there's no recent activity, say so clearly.** Don't pad the digest with old content — suggest the user ingest or teach something new.
- **Keep it brief.** This is a digest, not a deep dive. Each item should be 1-2 lines max.
- **Prioritize actionable suggestions** over passive reporting. "You added 3 articles about React but haven't connected them to your existing Node.js knowledge" is better than "3 articles were added."
