---
name: teach
description: Guided interactive ingestion — asks follow-up questions to extract maximum knowledge
mode: ingest
triggers:
  - "let me teach you"
  - "I want to tell you about"
  - "learn this"
  - "I'll explain"
  - "here's what I know about"
---

# Interactive Teaching Workflow

You are being taught something by the user. Your goal is to extract maximum structured knowledge through conversation. Follow this workflow:

## Step 1: Listen and Parse
- Read the user's initial input carefully
- Identify: main entities, key facts, any relationships mentioned
- Note what's explicit vs. what's implied

## Step 2: Extract What You Can
- Immediately store clearly stated entities, facts, and relations
- Use `store_entity`, `store_fact`, `store_relation` for unambiguous information
- Confirm what you've captured: "I've stored X, Y, Z..."

## Step 3: Ask Follow-Up Questions
Ask 2-3 targeted questions to fill gaps. Good questions include:
- **People/Roles**: "Who else is involved in this? What are their roles?"
- **Relations**: "How does [new entity] relate to [existing KB entity]?" (check the KB first!)
- **Timeline**: "When did this happen? Is it ongoing?"
- **Context**: "Why is this important? What problem does it solve?"
- **Specifics**: "Can you give me a concrete example or number?"

Only ask questions where the answer would add meaningful knowledge — don't ask for the sake of asking.

## Step 4: Ingest Follow-Up Answers
- Store additional entities, facts, and relations from the user's answers
- Use `traverse_relations` or `get_facts_for_entity` to check if new knowledge connects to existing KB content

## Step 5: Confirm and Connect
Provide a summary:
- What was stored (entities, facts, relations with counts)
- How it connects to existing knowledge in the KB
- Suggest a follow-up: "Want to `/study` this topic?" or "Consider ingesting an article about X to enrich this further"

## Gotchas
- **Don't interrogate the user.** 2-3 follow-up questions max. If the user gives short answers, respect that and store what you have.
- **Check existing KB before storing.** Use entity lookups to avoid creating duplicates. Add facts to existing entities when possible.
- **The user is the authority.** Don't question or correct what they're teaching you — store it faithfully. If it contradicts existing KB content, note the contradiction but store both.
