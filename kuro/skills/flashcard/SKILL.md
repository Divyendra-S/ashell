---
name: flashcard
description: Spaced repetition review — surfaces topics you struggled with at optimal intervals
mode: query
triggers:
  - "flashcard"
  - "spaced repetition"
  - "review cards"
  - "what should I review"
---

# Spaced Repetition Flashcard Workflow

You are running a spaced repetition review session. Follow this workflow:

## Step 1: Load History
- Read study session data from skill data (if available via `read_skill_data`)
- Identify topics with: low scores, not reviewed recently, or never reviewed
- If no session history exists, fall back to generating flashcards from the KB's richest topics

## Step 2: Prioritize Topics
Apply spaced repetition logic:
- **Priority 1**: Topics scored < 3/5 in last session (review soon)
- **Priority 2**: Topics not reviewed in the longest time (prevent forgetting)
- **Priority 3**: Recently ingested topics never studied (introduce new material)

## Step 3: Generate Flashcards
Create 5-8 flashcards from the prioritized topics:
- Each card has a **Question** (front) and **Answer** (back)
- Mix question types: definition, relationship, application
- Pull directly from KB entities, facts, and articles
- Cite the source for each answer

Present cards one at a time:
```
📇 Card 1/5 — Topic: [topic name]
Q: [question]
```

Wait for the user's answer before revealing:
```
A: [answer with KB citation]
✅ Correct / ❌ Incorrect / 🔶 Partial
```

## Step 4: Score and Update
- Track results for this session
- Save session data using `append_skill_data` to `review_log.jsonl`:
  - `{"date": "...", "topics": [...], "card_results": [...], "score": "6/8", "improved": [...], "struggling": [...]}`
- Also use `save_memory` to update the user's memory with a summary:
  - name: `flashcard_latest`, type: `context`
  - content: "Flashcard session ({date}): {score}. Improved on {list}. Still struggling with {list}. Next review: {date}."
- Compare to previous sessions: "You improved on X! Still struggling with Y."

## Step 5: Next Review
- Suggest when to review again based on scores:
  - All correct → "Review again in 3-5 days"
  - Mixed → "Review again tomorrow"
  - Mostly wrong → "Consider running `/explain` on these topics first"

## Gotchas
- **Don't repeat the exact same cards from the last session.** Rephrase questions even if testing the same facts.
- **If no study history exists, don't pretend it does.** Start fresh with the KB's richest topics and say "This is your first flashcard session."
- **Keep cards atomic.** Each card tests one fact or concept, not a paragraph of knowledge.
