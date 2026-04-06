---
name: daily-digest
description: Generate a digest of recent knowledge additions, connections, and review suggestions
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
- Use `grep_wiki` to identify recently added or updated wiki pages
- If study session data exists (in skill data), read it for recent scores

## Step 2: Find Connections
- For recently added knowledge, use `grep_wiki` to search for related pages and follow `[[backlinks]]` to find how it connects to existing knowledge
- Use `read_wiki_page` to load pages and check their backlinks
- Highlight any surprising or non-obvious connections between new and old content

## Step 3: Generate Digest
Present a structured daily digest:

### What's New
- List of recently ingested articles and wiki pages (with brief descriptions)
- Key concepts and connections added

### Connections Discovered
- How new knowledge links to existing KB content
- Any patterns or themes emerging across recent additions

### Review Suggestions
- Topics from recent study sessions with low scores (if available)
- Topics ingested but not yet studied or explored
- Wiki pages that were recently added but have few backlinks (good candidates for `/teach`)

### Quick Stats
- Total KB size (articles, wiki pages)
- Growth since last digest (if previous digest data is available)

## Gotchas
- **If there's no recent activity, say so clearly.** Don't pad the digest with old content — suggest the user ingest or teach something new.
- **Keep it brief.** This is a digest, not a deep dive. Each item should be 1-2 lines max.
- **Prioritize actionable suggestions** over passive reporting. "You added 3 articles about React but haven't connected them to your existing Node.js knowledge" is better than "3 articles were added."
