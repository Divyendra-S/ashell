# Question Types Reference

Use this to vary question types across study sessions. Each type tests a different level of understanding.

## 1. Factual Recall
Tests: Can the user remember specific facts from the KB?
Format: "What is...", "When did...", "Who..."
Example: "What database does Project X use?" (fact: "Project X uses PostgreSQL")
Difficulty: Easy

## 2. Understanding / Explanation
Tests: Can the user explain how or why something works?
Format: "Why does...", "How does...", "Explain the relationship between..."
Example: "Why did Team Alpha choose microservices over a monolith?" (requires connecting multiple facts)
Difficulty: Medium

## 3. Relationship / Connection
Tests: Can the user connect different pieces of knowledge?
Format: "How does X relate to Y?", "What do X and Y have in common?"
Example: "What's the connection between the billing service and the auth middleware?" (requires traversing relations)
Difficulty: Medium-Hard

## 4. Application / Scenario
Tests: Can the user apply knowledge to a new situation?
Format: "If [scenario], what would...", "Given [context], which approach..."
Example: "If you needed to add real-time notifications to Project X, which existing service could you build on?" (requires understanding architecture)
Difficulty: Hard

## 5. Synthesis
Tests: Can the user combine multiple sources to form a new insight?
Format: "Based on what you know about X and Y, what would be the best approach to..."
Example: "Based on the team's experience with Service A and the requirements for Service B, what architecture would you recommend?"
Difficulty: Hardest — use sparingly (1 per session max)

## Distribution Guide
- First session on a topic: 3 Factual, 1 Understanding, 1 Relationship
- Repeat session (user scored well): 1 Factual, 2 Understanding, 1 Application, 1 Synthesis
- Repeat session (user scored poorly): 2 Factual, 2 Understanding, 1 Relationship
