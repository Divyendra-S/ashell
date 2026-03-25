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

### Concepts & Topics
- Focus on extracting study-worthy concepts, techniques, methodologies, and ideas
- Use entity_type "topic" for all concepts
- Extract the main topic, sub-topics, and related theoretical ideas
- Only create person/company entities if they ARE the subject of study (not just mentioned)
- Examples of good concepts: "Prompt Caching", "Graph Regularization", "Force-Directed Layout", "Command Validation"
- Examples of bad extractions: "Google" (company mentioned in passing), "John Smith" (person referenced)

### Facts
- Extract key facts about each concept
- Store each with `store_fact`, linking to the correct concept
- Aim for 3-5 facts per major concept, 1-2 for minor ones
- Focus on facts useful for studying and understanding

### Relations (Concept Hierarchy)
- Use "subtopic_of" to build concept hierarchies (e.g. "Batch Normalization" subtopic_of "Neural Network Training")
- Use "related_to" for lateral connections between concepts
- Use "requires", "enables", "builds_on" for dependency relationships
- Use "contrasts_with" for opposing approaches
- Include context for non-obvious relationships

## Step 4: Confirm
Provide a summary of everything extracted:
- Article title and topic
- Number of entities, facts, and relations stored
- List of key entities extracted
- Any notable connections discovered

Be thorough — the goal is to make every piece of knowledge in this article retrievable later.

## Gotchas
- **Some sites block scraping.** If `scrape_url` returns an error or empty content, tell the user to paste the article content directly instead of retrying.
- **Don't create duplicate entities.** Before calling `store_entity`, check if the entity might already exist in the KB using `get_facts_for_entity`. If it does, add new facts/relations to the existing entity rather than creating a duplicate.
- **Quality over quantity for facts.** Extract meaningful, specific facts — not trivial ones like "X is a company" when the article is about X's product launch.
