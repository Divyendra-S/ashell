---
name: summarize
description: Comprehensive summary organized by theme with key takeaways
triggers:
  - "summarize"
  - "summary"
  - "overview"
  - "recap"
  - "what do I know about"
---

# Summarization Workflow

You are creating a comprehensive summary. Follow this workflow:

## Step 1: Gather Everything
- Use all available retrieval tools to collect everything the KB has on the topic
- Search for the main entity and related entities
- Use `traverse_relations` to find connected knowledge (depth 2-3)
- Use `grep_articles` to find all article mentions
- Use `list_articles` if needed to find relevant articles by title

## Step 2: Organize by Theme
- Group the retrieved information into 3-6 thematic sections
- Choose themes that emerge naturally from the content, not predetermined categories
- Order themes from most fundamental to most specific

## Step 3: Write Summary
Present a structured summary with:
- **Overview**: 2-3 sentence high-level summary
- **Thematic sections**: Each with a heading and 3-5 key points
- **Key Takeaways**: 3-5 bullet points of the most important things to remember
- **Related Topics**: Other entities/topics in the KB that connect to this one
- **Knowledge Gaps**: Areas where more information could be added

Keep the summary concise but comprehensive. Every claim should trace back to specific KB content.

## Gotchas
- **Chunk retrieval may miss content.** Long articles get split into chunks, and hybrid search may only return a few. Use `read_article` to load full article content when a topic spans a large document.
- **Don't confuse "not in KB" with "not true."** Knowledge Gaps should be framed as "the KB doesn't cover X" not "X is unknown."
- **Avoid restating the same fact under multiple themes.** Deduplicate information across thematic sections.
