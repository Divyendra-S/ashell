# Progressive Disclosure (AI)

A design technique where agents incrementally discover relevant context or instructions through exploration, rather than having everything front-loaded in system prompts. It prevents context rot and reduces cognitive load by revealing information only when needed.

## Key Facts
- Progressive disclosure reduces the need to cram all instructions into a system prompt, which can cause context rot and distract the model from its primary job. In Claude Code, instead of adding a new tool or bloated prompt for self-documentation, they gave Claude a Guide subagent and a link to its docs. Claude could then load and search for more information only when asked by the user.

## Connections
- [[Agent Context Building]] (enables) — Context building tools allow an agent to actively explore its environment, which provides the foundation needed to implement progressive disclosure instead of relying on front-loaded context.
- [[Agent Action Space]] (related_to) — Progressive disclosure is a strategy to augment what an agent can do without having to explicitly add more tools to its action space, keeping the tool count manageable.

## Source Passages
> We could have put all of this information in the system prompt, but given that users rarely asked about this, it would have added context rot and interfered with Claude Codes main job: writing code. Instead, we tried a form of progressive disclosure. We gave Claude a link to its docs which it could then load to search for more information. ... So we built the Claude Code Guide subagent which Claude is prompted to call when you ask about itself, the subagent has extensive instructions on how to search docs well and what to return.
> — [Lessons from Building Claude Code: Seeing like an Agent](local://claude-code-lessons)

