# AI Elicitation

An agent's process of prompting users for missing information or clarifying choices. Good elicitation mechanisms reduce friction and block internal agent loops until human input is received, thereby increasing communication bandwidth.

## Key Facts
- Designing good elicitation mechanisms requires structuring the AI's output so it can be rendered as a user-friendly UI, rather than relying on plain text which is slow. The Claude team experimented with modifying markdown and adding parameters to other tools, but ultimately found success with a dedicated `AskUserQuestion` tool. This tool blocks the agent's loop until the user answers, ensuring structured and actionable responses without confusing the model.

## Connections
- [[Agent Action Space]] (part_of) — Elicitation tools are a specialized subset of the action space dedicated to communicating with the human to gather needed information or approvals.

## Source Passages
> Finally, we landed on creating a tool that Claude could call at any point, but it was particularly prompted to do so during plan mode. When the tool triggered we would show a modal to display the questions and block the agents loop until the user answered. This tool allowed us to prompt Claude for a structured output and it helped us ensure that Claude gave the user multiple options.
> — [Lessons from Building Claude Code: Seeing like an Agent](local://claude-code-lessons)

