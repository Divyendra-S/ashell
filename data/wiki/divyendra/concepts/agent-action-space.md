# Agent Action Space

The specific set of tools and capabilities provided to an AI agent to solve problems in its environment. Effective action spaces balance tool count and complexity, matching them exactly to the underlying model's reasoning abilities.

## Key Facts
- Designing an agent's action space is like choosing between paper, a calculator, or a computer for a math problem; it must fit the user's specific skills. If tools are too complex, the agent may not understand how to call them, but if too constrained, they limit the agent's potential. The optimal action space is discovered through continuous experimentation, reading model outputs, and adapting to the agent's evolving capabilities.

## Connections
- [[Agent Tool Obsolescence]] (related_to) — Understanding when a tool becomes obsolete is critical for continuously shaping a capable agent's action space so it isn't constrained by guardrails meant for weaker models.
- [[AI Elicitation]] (part_of) — Elicitation tools are a specialized subset of the action space dedicated to communicating with the human to gather needed information or approvals.
- [[Progressive Disclosure (AI)]] (related_to) — Progressive disclosure is a strategy to augment what an agent can do without having to explicitly add more tools to its action space, keeping the tool count manageable.

## Source Passages
> Given all these options, how do you design the tools of your agent? ... To put myself in the mind of the model I like to imagine being given a difficult math problem. What tools would you want in order to solve it? It would depend on your own skills! ... You want to give it tools that are shaped to its own abilities. But how do you know what those abilities are? You pay attention, read its outputs, experiment. You learn to see like an agent.
> — [Lessons from Building Claude Code: Seeing like an Agent](local://claude-code-lessons)

