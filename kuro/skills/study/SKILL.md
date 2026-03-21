---
name: study
description: Generate quiz questions from KB and evaluate answers
triggers:
  - "quiz me"
  - "test me"
  - "study"
  - "practice"
---

# Study / Quiz Workflow

You are running an interactive study session. Follow this workflow:

## Step 1: Load Knowledge
- First, call `analyze_study_progress` to see the user's study history — past scores, weak areas, and trends
- Retrieve all KB content about the requested topic
- Use entity lookups, fact retrieval, article search, and relation traversal
- Build a comprehensive understanding of what the user should know
- Use the progress data to avoid repeating questions from previous sessions and to target weak areas

## Step 2: Generate Questions
- Create 5 questions of varying difficulty:
  - 2 factual recall questions (what, when, who)
  - 2 understanding questions (why, how, explain)
  - 1 application/connection question (relate concepts, apply to scenario)
- Present ALL 5 questions at once, numbered 1-5

## Step 3: Evaluate Answers
- When the user answers, evaluate each answer against the KB content
- For each answer, provide:
  - Correct / Partially Correct / Incorrect
  - The correct answer with KB citation
  - A brief explanation if the user was wrong

## Step 4: Score and Save
- Calculate a score (e.g., 3/5)
- Save detailed session data using `append_skill_data` to `sessions.jsonl`:
  - `{"topic": "...", "score": "3/5", "date": "...", "questions_asked": [...], "weak_areas": [...]}`
- Also use `save_memory` to update the user's memory with a summary:
  - name: `study_{topic}_latest`, type: `context`
  - content: "Scored 3/5 on {topic} ({date}). Weak areas: {list}. Suggest /explain on {weakest}."
  - This ensures the summary is visible in every future session without loading JSONL files
- Suggest what to study next based on weak areas

Present questions in a clear, numbered format. Be encouraging but accurate in evaluation.

## Gotchas
- **Ground every question in the KB.** Do not generate questions from general knowledge — every question must cite a specific entity, fact, or article passage. If the KB has too little content on a topic, reduce the number of questions rather than inventing them.
- **Don't repeat questions across sessions.** If skill data from previous sessions is available (in `study/sessions.jsonl`), read it and avoid re-asking the same questions.
- **Score generously for partial answers** — if the user captures the core idea but misses a detail, mark as "Partially Correct" rather than "Incorrect."
- If the user scores below 3/5, suggest running `/explain` on their weakest topic to build understanding before retrying.
