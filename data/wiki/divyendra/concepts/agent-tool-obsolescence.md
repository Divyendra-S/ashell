# Agent Tool Obsolescence

The phenomenon where tools that once helped a weaker AI model stay on track become limiting bottlenecks as the model's capabilities increase. It requires developers to frequently revisit and replace assumptions about necessary guardrails.

## Key Facts
- As models improve in reasoning and capability, previously helpful tools can become constraining and need to be redesigned. For instance, the Claude team originally used a strict `TodoWrite` tool with frequent reminders to keep the model on track. However, as the Opus model improved, these reminders artificially constrained it, leading the team to replace Todos with a flexible `Task` tool that better supported subagent coordination.

## Connections
- [[Agent Action Space]] (related_to) — Understanding when a tool becomes obsolete is critical for continuously shaping a capable agent's action space so it isn't constrained by guardrails meant for weaker models.

## Source Passages
> As models improved, they not only did not need to be reminded of the Todo List but could find it limiting. Being sent reminders of the todo list made Claude think that it had to stick to the list instead of modifying it. ... Seeing this, we replaced TodoWrite with the Task Tool. Whereas Todos were about keeping the model on track, Tasks were more about helping agents communicate with each other. ... As model capabilities increase, the tools that your models once needed might now be constraining them.
> — [Lessons from Building Claude Code: Seeing like an Agent](local://claude-code-lessons)

