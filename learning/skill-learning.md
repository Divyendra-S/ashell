# Skills: Lessons from Building Claude Code

## How Kuro Currently Stores User Progress

Skill data is stored as **JSONL files on disk** at `data/skill_data/{user_id}/{skill_name}/`:

```
data/skill_data/
├── div/
│   ├── study/sessions.jsonl        # quiz scores, weak areas
│   ├── flashcard/review_log.jsonl  # spaced repetition state
│   └── deep_research/research_log.jsonl
├── divyendra/
│   └── study/sessions.jsonl
```

Each record is one JSON line appended to the file. The agents use `read_skill_data` / `append_skill_data` tools.

**Is this good?** It's the simplest approach and matches what the article recommends — "anything as simple as an append-only text log file or JSON files." However, since the rest of the data (entities, facts, articles, memories) lives in **Supabase**, having skill data on disk creates a split:
- Disk data doesn't survive server migration
- Can't query across skill data easily (e.g., "show me all study scores across all topics")
- No backup/sync with the rest of the DB

Moving to a Supabase `skill_data` table would be more consistent but adds complexity. For now, disk JSONL is fine for an MVP.

---

## Three Key Concepts from the Article

### 1. Store Data (Skill Memory)

**What:** Skills can persist data between sessions — logs, configs, progress. The agent reads its own history next time it runs.

**Article example:** A standup-post skill keeps `standups.log` with every post. Next run, Claude reads the log and knows what changed since yesterday.

**How Kuro does it:**
```python
# Agent reads past study sessions
records = read_skill_data("study", "sessions.jsonl", user_id="div")
# → [{"topic": "React", "score": 3, "weak_areas": ["hooks"]}, ...]

# Agent saves new session result
append_skill_data("study", "sessions.jsonl", {
    "topic": "React", "score": 4, "date": "2026-03-21"
}, user_id="div")
```

The flashcard skill uses this to implement spaced repetition — it reads past scores and timestamps to decide which topics to resurface.

### 2. Store Scripts & Generate Code ("Give It Code")

**What:** Instead of making the agent write everything from scratch, include helper scripts/libraries in the skill folder that the agent can **compose and call**.

**Article example:** A data science skill includes a Python library with functions like `fetch_events()`, `get_user_journey()`. The agent imports these and writes a small script to answer "What happened on Tuesday?" — it spends time on logic, not boilerplate.

**How you'd use it in Kuro:**
```
kuro/skills/deep_research/
├── SKILL.md
├── report_template.md          # ← template the agent copies
├── scripts/
│   ├── fetch_kb_stats.py       # helper: get entity/fact counts
│   └── graph_visualizer.py     # helper: generate a graph diagram
└── examples/
    └── good_report.md          # ← reference example
```

The SKILL.md would say: "Use `scripts/fetch_kb_stats.py` to gather statistics. Use `report_template.md` as your output format." The agent reads and executes the scripts rather than reinventing the logic each time.

We partially do this already with progressive disclosure (report_template.md, question_types.md), but haven't added executable scripts yet.

### 3. On-Demand Hooks

**What:** Hooks are shell commands that run automatically before/after tool calls. **On-demand hooks** are hooks that only activate when a specific skill is invoked, not all the time.

**Article examples:**
- `/careful` — blocks `rm -rf`, `DROP TABLE`, force-push via a PreToolUse hook on Bash. Only active when you're touching prod.
- `/freeze` — blocks any file Edit/Write outside a specific directory. Useful when debugging so you don't accidentally "fix" unrelated code.

**How they work (Claude Code specific):**

In a skill's config, you register hooks:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "command": "python scripts/check_dangerous.py \"$TOOL_INPUT\""
    }]
  }
}
```

When the skill is active and the agent tries to use Bash, the hook script runs first. If it exits non-zero, the tool call is blocked.

**For Kuro:** This is a Claude Code-specific feature (hooks run in the CLI harness). Since Kuro is a web API with Gemini, the equivalent would be **middleware in the agent loop** — checking tool calls before executing them:

```python
# In run_agent_loop, before executing a tool:
def safe_executor(name, args, blocked_tools=None):
    if blocked_tools and name in blocked_tools:
        return json.dumps({"error": f"Tool {name} is blocked by active skill policy"})
    return base_executor(name, args)
```

---

## Core Concepts Summary

1. **Skills are folders, not just files** — Include scripts, data, templates, examples. The file system is a form of context engineering.

2. **9 skill categories** — Library/API reference, Product verification, Data fetching, Business process, Code scaffolding, Code quality, CI/CD, Runbooks, Infrastructure ops. Most orgs should have skills in several categories.

3. **Gotchas are the highest-signal content** — Build them from real failure modes. Update over time as the agent hits new edge cases.

4. **Progressive disclosure** — Don't dump everything in one file. Point to sub-files; the agent reads them when needed.

5. **Don't state the obvious** — Focus on what pushes the model out of its default behavior. Don't repeat what it already knows.

6. **Don't railroad** — Give information and flexibility, not rigid step-by-step scripts. Let the agent adapt.

7. **Description field is for the model** — It's a trigger condition ("when should this skill activate?"), not a human-readable summary.

8. **Skill composition** — Skills can reference other skills by name. No formal dependency system needed — just mention them.

9. **Measure and curate** — Track which skills trigger, which are popular, which are redundant. Quality > quantity.

10. **Start simple, iterate** — Most good skills started as a few lines + one gotcha, then grew as edge cases appeared.

---

## 9 Skill Categories (with examples)

| Category | What It Does | Example |
|---|---|---|
| Library & API Reference | How to use a library/SDK correctly | `billing-lib` — edge cases, footguns |
| Product Verification | Test/verify code is working | `signup-flow-driver` — headless browser testing |
| Data Fetching & Analysis | Connect to data/monitoring stacks | `funnel-query` — event joins for signup→activation→paid |
| Business Process | Automate repetitive workflows | `standup-post` — aggregate activity → formatted standup |
| Code Scaffolding | Generate framework boilerplate | `new-migration` — migration template + gotchas |
| Code Quality & Review | Enforce code quality | `adversarial-review` — spawn critic subagent |
| CI/CD & Deployment | Fetch, push, deploy code | `babysit-pr` — monitor PR → retry CI → auto-merge |
| Runbooks | Symptom → investigation → report | `oncall-runner` — fetch alert → check usual suspects |
| Infrastructure Ops | Routine maintenance with guardrails | `dependency-management` — org approval workflow |

## Kuro's 10 Skills (mapped to categories)

| Skill | Category | Mode |
|---|---|---|
| `/study` | Product Verification (self-testing) | query |
| `/explain` | Library & API Reference | query |
| `/summarize` | Data Fetching | query |
| `/compare` | Data Fetching | query |
| `/deep-research` | Runbooks | query |
| `/review` | Data Fetching | query |
| `/daily-digest` | Business Process | query |
| `/teach` | Code Scaffolding (knowledge scaffolding) | ingest |
| `/flashcard` | Product Verification (self-testing) | query |
| `/ingest-url` | Data Fetching | ingest |
