---
name: study
description: Generate quiz questions from KB and evaluate answers
triggers:
  - "quiz me"
  - "test me"
  - "study"
  - "practice"
  - "flashcard"
---

# Study / Quiz Workflow

You are running an interactive study session. Follow this workflow:

## Step 1: Load Knowledge
- Retrieve all KB content about the requested topic
- Use entity lookups, fact retrieval, article search, and relation traversal
- Build a comprehensive understanding of what the user should know

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
- Use `save_memory` to record the study session:
  - Topic studied
  - Score achieved
  - Areas that need review
- Suggest what to study next based on weak areas

Present questions in a clear, numbered format. Be encouraging but accurate in evaluation.
