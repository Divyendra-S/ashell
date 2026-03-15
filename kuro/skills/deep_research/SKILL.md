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
- Use `get_facts_for_entity`, `get_relations_for_entity`, and `traverse_relations` to explore the knowledge graph
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
