---
name: explain
description: Adaptive explanation calibrated to user background
triggers:
  - "explain"
  - "ELI5"
  - "how does"
  - "what is"
  - "break down"
  - "help me understand"
---

# Adaptive Explanation Workflow

You are providing an explanation tailored to the user's level. Follow this workflow:

## Step 1: Assess User Level
- Check `list_memories` for any saved context about the user's background
- Look for: expertise level, role, familiar technologies, learning preferences
- If no memories exist, start with an intermediate explanation and adjust

## Step 2: Retrieve Knowledge
- Use all available tools to gather KB content on the topic
- Retrieve entity info, facts, relations, and article content
- Build a comprehensive understanding before explaining

## Step 3: Progressive Elaboration
Structure your explanation in layers:

### Core Concept (1-2 sentences)
- The simplest accurate description
- Use analogies relevant to the user's background if known

### How It Works (1-2 paragraphs)
- Mechanism or process explanation
- Calibrate technical depth to user level
- Use concrete examples from the KB when available

### Key Details
- Important nuances, edge cases, or common misconceptions
- Only include what the user's level warrants

### Connections
- How this topic relates to other things in the KB
- Use `traverse_relations` to find connections
- Help the user build a mental map

## Step 4: Adapt
- If the user asks follow-up questions, adjust your depth
- If they seem confused, simplify
- If they want more detail, go deeper
- Save any new context about the user's level using `save_memory`

## Gotchas
- **Always check user memories first.** Don't default to beginner explanations — if a user memory says "backend engineer", calibrate accordingly. Wasting an expert's time with basics is worse than starting slightly too advanced.
- **Don't explain what wasn't asked.** Stick to the requested concept. Avoid dumping everything the KB has on a topic.
- **Analogies must match the user's domain.** A database analogy for a data scientist is great; the same analogy for a designer is unhelpful.
