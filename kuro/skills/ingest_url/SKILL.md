---
name: ingest-url
description: Enhanced URL ingestion with thorough entity and fact extraction
triggers:
  - "save this article"
  - "ingest this"
  - "save this url"
  - "read and save"
---

# Enhanced URL Ingestion Workflow

You are performing thorough knowledge extraction from a URL. Follow this workflow:

## Step 1: Scrape
- Use `scrape_url` to fetch the content
- If the scrape fails, report the error clearly

## Step 2: Save Article
- Use `save_article` to store the full content
- Choose an appropriate topic category

## Step 3: Deep Extraction
Extract ALL of the following from the article content and create wiki pages:

### Concepts & Topics
- Focus on extracting study-worthy concepts, techniques, methodologies, and ideas
- Extract the main topic, sub-topics, and related theoretical ideas
- Only create pages for people/companies if they ARE the subject of study (not just mentioned)
- Examples of good concepts: "Prompt Caching", "Graph Regularization", "Force-Directed Layout", "Command Validation"
- Examples of bad extractions: "Google" (company mentioned in passing), "John Smith" (person referenced)

### Write Wiki Pages
- Use `write_wiki_page` for each major concept extracted
- Each page should contain: a brief definition, key facts (3-5 for major concepts, 1-2 for minor ones), and `[[backlinks]]` to related concept pages
- Build concept hierarchies via backlinks (e.g. the "Batch Normalization" page links to `[[Neural Network Training]]`)
- Use backlinks for relationships: subtopic, related, requires, enables, builds_on, contrasts_with
- Include context for non-obvious relationships inline on the page

## Step 4: Confirm
Provide a summary of everything extracted:
- Article title and topic
- Number of wiki pages created
- List of key concepts extracted
- Any notable connections discovered via backlinks

Be thorough — the goal is to make every piece of knowledge in this article retrievable later.

## Gotchas
- **Some sites block scraping.** If `scrape_url` returns an error or empty content, tell the user to paste the article content directly instead of retrying.
- **Don't create duplicate pages.** Before calling `write_wiki_page`, check if the page already exists using `read_wiki_page`. If it does, merge new content into the existing page rather than overwriting it.
- **Quality over quantity for facts.** Extract meaningful, specific facts — not trivial ones like "X is a company" when the article is about X's product launch.
