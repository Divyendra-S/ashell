---
name: ingest-url
description: Enhanced URL ingestion with thorough entity and fact extraction
mode: ingest
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
Extract ALL of the following from the article content:

### Entities
- Identify every notable entity mentioned (people, companies, projects, technologies, concepts)
- Store each with `store_entity` and an appropriate type and summary

### Facts
- Extract key facts about each entity
- Store each with `store_fact`, linking to the correct entity
- Aim for 3-5 facts per major entity, 1-2 for minor ones

### Relations
- Identify relationships between entities (works_at, created_by, competes_with, etc.)
- Store each with `store_relation`
- Include context for non-obvious relationships

## Step 4: Confirm
Provide a summary of everything extracted:
- Article title and topic
- Number of entities, facts, and relations stored
- List of key entities extracted
- Any notable connections discovered

Be thorough — the goal is to make every piece of knowledge in this article retrievable later.
