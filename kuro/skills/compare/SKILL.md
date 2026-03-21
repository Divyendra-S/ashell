---
name: compare
description: Side-by-side comparison with dimensions and tradeoffs
triggers:
  - "compare"
  - "vs"
  - "versus"
  - "difference between"
  - "differences between"
  - "X or Y"
---

# Comparison Workflow

You are performing a structured comparison. Follow this workflow:

## Step 1: Identify Subjects
- Extract the two (or more) subjects being compared
- Confirm them with the user if ambiguous

## Step 2: Parallel Retrieval
- Retrieve knowledge about each subject independently
- Use `get_facts_for_entity` and `get_relations_for_entity` for each subject
- Use `grep_articles` to find article content mentioning each subject
- Use `read_article` for full context when needed

## Step 3: Identify Dimensions
- From the retrieved knowledge, identify the most relevant comparison dimensions
- Common dimensions: purpose, architecture, performance, ecosystem, learning curve, use cases, tradeoffs
- Only include dimensions where the KB has information about both subjects

## Step 4: Build Comparison Table
Present a markdown table with:
- Rows = comparison dimensions
- Columns = subjects being compared
- Each cell contains a concise factual summary

## Step 5: Analysis
After the table, provide:
- **Key Tradeoffs**: The most important differences and what they mean in practice
- **When to Choose Each**: Practical recommendations based on use case
- **What's Missing**: Dimensions where the KB lacks information

Keep all claims grounded in retrieved knowledge. Do not fill in cells with general knowledge if the KB doesn't have the information — mark them as "Not in KB" instead.

## Gotchas
- **Flag data imbalance.** If the KB has 20 facts about subject A but only 2 about subject B, say so upfront. Don't pad subject B with vague statements to make the table look balanced.
- **"Not in KB" is a valid and important cell value.** Resist the urge to fill gaps with general knowledge — the user trusts this as their personal KB, not Wikipedia.
- **Don't force dimensions.** If the KB only supports 2-3 meaningful comparison dimensions, that's fine. A 3-row table with solid data beats a 10-row table with mostly "Not in KB."
