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
