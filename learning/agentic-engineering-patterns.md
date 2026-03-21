# Agentic Engineering: Deep Dive

## The Big Picture

Modern AI agents like Claude Code are built on a surprisingly simple insight: **give the LLM a computer**. Instead of building hundreds of specialized tools, you give it access to a filesystem and a shell, and it figures out how to use them. Everything else — memory, skills, progressive disclosure — is a pattern built on top of these two primitives.

---

## Concept 1: Why Filesystem Is the Best Database for Agents

A traditional app stores data in PostgreSQL, Redis, etc. But for an agent, the filesystem is better because:

1. **Zero setup** — no connection strings, no migrations, no ORM
2. **Human-readable** — you can open the file and see exactly what the agent stored
3. **Git-friendly** — memories can be version controlled, diffed, rolled back
4. **Crash-proof** — if the agent dies mid-conversation, files persist
5. **Progressive loading** — you read one file at a time, not the whole database
6. **Works offline** — no network dependency

Claude Code stores ALL its memory as plain `.md` files on disk. No database at all.

```
~/.claude/projects/my-project/memory/
├── MEMORY.md              # Index — first 200 lines loaded every session
├── debugging_patterns.md  # Detail file — read on-demand
├── api_conventions.md     # Detail file — read on-demand
└── user_preferences.md    # Detail file — read on-demand
```

Here's how to build this pattern:

```python
# memory.py — Filesystem-backed agent memory (functional style)

from pathlib import Path
import yaml

MEMORY_DIR = Path("~/.kuro/memory").expanduser()


def ensure_memory_dir():
    """Create memory directory if it doesn't exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    index = MEMORY_DIR / "MEMORY.md"
    if not index.exists():
        index.write_text("# Memory Index\n\nNo memories saved yet.\n")


def save_memory(topic: str, content: str, description: str):
    """
    Save a memory to a topic file and update the index.

    The topic file stores the actual content.
    MEMORY.md just stores a one-line pointer to it.
    This way, MEMORY.md stays small (loaded every session),
    and details are read on-demand.
    """
    ensure_memory_dir()

    # Write the topic file with frontmatter
    topic_file = MEMORY_DIR / f"{topic}.md"
    topic_file.write_text(
        f"---\ntopic: {topic}\ndescription: {description}\n---\n\n{content}\n"
    )

    # Update the index — only add if not already there
    index_path = MEMORY_DIR / "MEMORY.md"
    index_text = index_path.read_text()

    pointer = f"- [{topic}.md]({topic}.md) — {description}"
    if f"{topic}.md" not in index_text:
        index_path.write_text(index_text.rstrip() + f"\n{pointer}\n")

    return f"Saved memory: {topic}"


def load_index() -> str:
    """
    Load the memory index. This goes into the system prompt
    at the START of every conversation.

    Only first 200 lines — keeps token usage bounded.
    Claude Code does the exact same thing.
    """
    ensure_memory_dir()
    index_path = MEMORY_DIR / "MEMORY.md"
    lines = index_path.read_text().splitlines()
    return "\n".join(lines[:200])


def read_topic(topic: str) -> str:
    """
    Read a specific topic file. This is a TOOL the agent calls
    when it needs detailed info about something.

    The agent sees "debugging_patterns.md" in the index,
    decides it's relevant, and calls this to get the full content.
    This is progressive disclosure — details loaded on-demand.
    """
    path = MEMORY_DIR / f"{topic}.md"
    if not path.exists():
        return f"No memory found for topic: {topic}"

    text = path.read_text()
    # Strip YAML frontmatter, return just the content
    if text.startswith("---"):
        parts = text.split("---", 2)
        return parts[2].strip() if len(parts) > 2 else ""
    return text


def delete_topic(topic: str) -> str:
    """Delete a memory and remove it from the index."""
    path = MEMORY_DIR / f"{topic}.md"
    if path.exists():
        path.unlink()

    # Remove from index
    index_path = MEMORY_DIR / "MEMORY.md"
    lines = index_path.read_text().splitlines()
    lines = [l for l in lines if f"{topic}.md" not in l]
    index_path.write_text("\n".join(lines) + "\n")

    return f"Deleted memory: {topic}"


def list_topics() -> list[str]:
    """List all memory topic files."""
    ensure_memory_dir()
    return [
        p.stem for p in MEMORY_DIR.glob("*.md")
        if p.name != "MEMORY.md"
    ]
```

**How the agent uses this:**

```python
# At session start — index goes into system prompt (cheap, ~50-100 tokens)
system_prompt = f"""You are Kuro.

## Your Memory
{load_index()}

You can use these tools to manage memory:
- read_topic(topic): Get detailed info on a topic from your memory
- save_memory(topic, content, description): Save something to remember
- delete_topic(topic): Forget something
- list_topics(): See all saved topics
"""

# The LLM sees:
# ## Your Memory
# # Memory Index
# - [debugging_patterns.md](debugging_patterns.md) — Common debugging workflows
# - [user_preferences.md](user_preferences.md) — User likes short answers
#
# It decides "debugging_patterns" is relevant to the current question,
# and calls read_topic("debugging_patterns") to load the full content.
# This is PROGRESSIVE DISCLOSURE.
```

**Why this matters for tokens:**

```
Without progressive disclosure:
  10 topic files x 500 tokens each = 5,000 tokens in system prompt EVERY time

With progressive disclosure:
  Index: ~100 tokens (always loaded)
  + 1-2 relevant topics: ~1,000 tokens (loaded on-demand)
  = ~1,100 tokens total

Savings: 78% fewer tokens per conversation
```

---

## Concept 2: Progressive Disclosure — The Core Pattern

Progressive disclosure means: **show just enough info for the agent to decide what to do next, then load more detail only when needed.**

Think of it like a library:
- **Level 1**: You walk in and see the catalog (book titles + one-line descriptions)
- **Level 2**: You pick a book and read the table of contents (chapter summaries)
- **Level 3**: You open a specific chapter and read the full text

Claude Code applies this to EVERYTHING:

```
SKILLS:
  Level 1: Skill name + description (always in context)     ~100 tokens/skill
  Level 2: Full SKILL.md instructions (loaded when activated) ~500-2000 tokens
  Level 3: Supporting files (read via tools during execution) unlimited

MEMORY:
  Level 1: MEMORY.md index (always loaded, 200 lines max)   ~200 tokens
  Level 2: Topic files (read via tool when needed)           ~500 tokens each

CODEBASE:
  Level 1: Glob/Grep results (file names, line matches)     ~50 tokens
  Level 2: Read specific file sections (offset + limit)      ~500 tokens
  Level 3: Full file read                                    unlimited
```

Here's a complete implementation:

```python
# progressive.py — Three-tier progressive disclosure system

from pathlib import Path
import yaml


# ============================================================
# TIER 1: Metadata — always in system prompt, tiny footprint
# ============================================================

def scan_metadata(skills_dir: Path) -> dict[str, dict]:
    """
    Scan all skills and extract ONLY name + description.
    This is what gets loaded into every single conversation.

    Cost: ~100 tokens per skill. 10 skills = 1,000 tokens.
    """
    metadata = {}
    for skill_dir in skills_dir.iterdir():
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        text = skill_file.read_text()
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue

        meta = yaml.safe_load(parts[1])
        # Store only what's needed for discovery
        metadata[meta["name"]] = {
            "name": meta["name"],
            "description": meta["description"],
            "triggers": meta.get("triggers", []),
            "dir": skill_dir,
        }
    return metadata


def format_skill_index(metadata: dict[str, dict]) -> str:
    """
    Format metadata as a compact index for the system prompt.
    The LLM reads this and decides which skill to activate.
    """
    lines = ["## Available Skills"]
    for m in metadata.values():
        triggers = ", ".join(m["triggers"])
        lines.append(f"- /{m['name']}: {m['description']} (triggers: {triggers})")
    lines.append("")
    lines.append(
        "When the user's request matches a skill, activate it "
        "and follow its workflow."
    )
    return "\n".join(lines)


# ============================================================
# TIER 2: Full instructions — loaded when skill is activated
# ============================================================

def load_skill_body(metadata: dict[str, dict], name: str) -> str:
    """
    Load the full SKILL.md body. Only called when the LLM
    decides to use this skill, or user types /name.

    Cost: ~500-2000 tokens, but only once per conversation.
    """
    meta = metadata.get(name)
    if not meta:
        return ""

    text = (meta["dir"] / "SKILL.md").read_text()
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) > 2 else ""


# ============================================================
# TIER 3: Supporting resources — loaded during execution
# ============================================================

def read_skill_resource(metadata: dict[str, dict], name: str, filename: str) -> str:
    """
    Read a supporting file from the skill directory.
    Called by the agent as a tool during execution.

    Example: The deep-research skill has a reference.md
    with citation format examples. The agent reads it
    ONLY when it's actually writing citations.

    Cost: variable, but only loaded when truly needed.
    """
    meta = metadata.get(name)
    if not meta:
        return "Skill not found"

    resource_path = meta["dir"] / filename
    if not resource_path.exists():
        return f"Resource not found: {filename}"

    return resource_path.read_text()


# ============================================================
# How it all fits into the system prompt
# ============================================================

def build_system_prompt(
    metadata: dict[str, dict],
    memory_index: str,
    active_skill: str | None = None,
) -> str:
    """
    Build the system prompt with progressive disclosure.

    ALWAYS loaded: base prompt + memory index + skill index
    CONDITIONALLY loaded: active skill body
    NEVER pre-loaded: resources (agent reads them via tools)
    """
    parts = [
        "You are Kuro, a knowledge assistant.",
        "",
        "## Your Memory",
        memory_index,           # Tier 1 of memory
        "",
        format_skill_index(metadata),  # Tier 1 of skills
    ]

    # Tier 2: Full skill instructions (only when activated)
    if active_skill:
        body = load_skill_body(metadata, active_skill)
        if body:
            parts.append(f"\n## Active Skill: /{active_skill}")
            parts.append(body)

    return "\n".join(parts)


# ============================================================
# Example: What the LLM sees at each tier
# ============================================================

# TIER 1 (always loaded, ~600 tokens for 6 skills):
#
# ## Available Skills
# - /deep-research: Multi-pass research with citations (triggers: research, deep dive)
# - /compare: Side-by-side comparison (triggers: compare, vs, versus)
# - /summarize: Comprehensive summary (triggers: summarize, overview)
# ...
#
# When the user's request matches a skill, activate it.

# TIER 2 (loaded when user says "research transformers", ~1500 tokens):
#
# ## Active Skill: /deep-research
# # Deep Research Workflow
# ## Pass 1: Decompose
# - Break the question into 3-5 sub-questions...
# ## Pass 2: Retrieve
# - For each sub-question, use retrieval tools...
# ...

# TIER 3 (loaded via tool call during Pass 4, ~300 tokens):
#
# Agent calls: read_skill_resource("deep-research", "citation_format.md")
# Gets: "## Citation Format\n- Use [Article Title] for article refs..."
```

---

## Concept 3: Bash as the Universal Tool

This is the most powerful insight in agentic engineering. Instead of building dozens of tools, you give the agent **one Bash tool** and it can do anything a human can do in a terminal.

**The key quote from the research:** *"Agents that chain actions through code execution save tokens because they don't process intermediate tool results."*

What this means:

```python
# ============================================================
# THE PROBLEM: Sequential tool calls are expensive
# ============================================================

# Without bash, your agent needs separate tools AND pays tokens
# for each intermediate result:

# Step 1: Agent calls list_files("src/")
#   -> LLM receives ["auth.py", "api.py", "utils.py", ...]  (200 tokens)
#   -> LLM thinks about which files matter                    (50 tokens)
#
# Step 2: Agent calls grep_file("auth.py", "TODO")
#   -> LLM receives ["line 42: # TODO fix token refresh"]    (30 tokens)
#   -> LLM thinks about the result                           (50 tokens)
#
# Step 3: Agent calls grep_file("api.py", "TODO")
#   -> LLM receives ["line 15: # TODO add rate limiting"]    (30 tokens)
#   -> LLM thinks about the result                           (50 tokens)
#
# ... repeat for every file. 20 files = 20 round trips.
# Total: ~20 LLM calls, ~6,000 tokens of intermediate results.


# ============================================================
# THE SOLUTION: One bash call does everything
# ============================================================

# With bash, the agent writes a pipeline and gets ONE result:

# Agent calls bash("grep -rn 'TODO' src/ | head -20")
#   -> LLM receives the final aggregated output               (200 tokens)
#   -> Done in 1 round trip.
#
# Total: 1 LLM call, ~200 tokens.
# That's a 30x reduction in LLM calls.
```

Here's how to build it:

```python
# bash_tool.py — Universal execution tool

import subprocess
import os


def execute_bash(
    command: str,
    timeout: int = 120,
    working_dir: str = ".",
) -> dict:
    """
    Execute a shell command and return the result.

    This ONE function replaces dozens of specialized tools:
    - Run tests:        execute_bash("pytest tests/ -v")
    - Install packages: execute_bash("pip install pyyaml")
    - Git operations:   execute_bash("git diff --stat")
    - HTTP requests:    execute_bash("curl -s http://localhost:8000/api/health")
    - Data processing:  execute_bash("cat data.json | python -c 'import json,sys; ...'")
    - Process mgmt:     execute_bash("lsof -ti:8000 | xargs kill")
    - File operations:  execute_bash("find . -name '*.py' -newer yesterday")

    The agent writes the command. We just execute it.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        # Truncate to prevent context blowup
        stdout = result.stdout[-10_000:] if len(result.stdout) > 10_000 else result.stdout
        stderr = result.stderr[-5_000:] if len(result.stderr) > 5_000 else result.stderr

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "exit_code": -1,
        }


# The tool definition the LLM sees:
BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute a shell command and return stdout, stderr, and exit code. "
        "Use for: running tests, git operations, installing packages, "
        "HTTP requests, file search, data processing, process management. "
        "The working directory persists between calls."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 120, max 600)",
            },
        },
        "required": ["command"],
    },
}
```

**Why Claude Code ALSO has dedicated file tools (Read, Edit, Grep, Glob):**

Bash can do everything, but it's not always the safest or most efficient:

```python
# bash_vs_dedicated.py — Why both exist

# SCENARIO 1: Reading a file
#
# Bash way:     execute_bash("cat src/api.py")
#   Problem:    dumps the ENTIRE file into context (could be 2000 lines)
#   Problem:    no line numbers for later editing
#   Problem:    can't read images/PDFs
#
# Read tool:    read_file("src/api.py", offset=40, limit=20)
#   Benefit:    reads only lines 40-60 (saves tokens)
#   Benefit:    shows line numbers (needed for Edit)
#   Benefit:    handles binary files, PDFs, notebooks


# SCENARIO 2: Editing a file
#
# Bash way:     execute_bash("sed -i 's/old_function/new_function/g' api.py")
#   Problem:    sed replaces ALL matches (maybe you only wanted one)
#   Problem:    if the pattern appears in a comment, it gets changed too
#   Problem:    silent failure — you don't know if it worked
#
# Edit tool:    edit_file("api.py", old_string="def old_function", new_string="def new_function")
#   Benefit:    FAILS if old_string appears multiple times (safety)
#   Benefit:    sends only the diff, not the whole file (token efficient)
#   Benefit:    returns clear success/failure


# SCENARIO 3: Finding files
#
# Bash way:     execute_bash("find . -name '*.py' -path '*/agents/*'")
#   Problem:    output is just text, needs parsing
#   Problem:    can hang on huge directories
#
# Glob tool:    glob_files("**/agents/*.py")
#   Benefit:    returns structured list sorted by modification time
#   Benefit:    fast, never hangs


# SCENARIO 4: Complex multi-step operations
#
# This is where Bash WINS over dedicated tools:
#
# "Find all Python files changed in the last commit,
#  check if they have TODO comments, and count them"
#
# With dedicated tools: 3 tool calls, 3 LLM round trips
# With bash: 1 call
execute_bash(
    "git diff --name-only HEAD~1 -- '*.py' | "
    "xargs grep -c 'TODO' 2>/dev/null | "
    "grep -v ':0$'"
)
```

---

## Concept 4: Dedicated File Tools (Read, Write, Edit, Glob, Grep)

Claude Code separates file operations into dedicated tools instead of routing everything through Bash. Here's why and how:

```python
from pathlib import Path
import re


# ---- READ: Targeted file reading with line control ----
def read_file(path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read a file with optional line range. Better than cat because:
    - Shows line numbers (for precise editing later)
    - Supports offset/limit for large files
    - Can read images, PDFs, notebooks
    """
    p = Path(path)
    lines = p.read_text().splitlines()
    selected = lines[offset:offset + limit]
    return "\n".join(f"{i + offset + 1}\t{line}" for i, line in enumerate(selected))


# ---- EDIT: Surgical string replacement ----
def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace exact string in file. Better than sed/awk because:
    - Fails if old_string isn't unique (prevents wrong edits)
    - Only sends the diff, not the whole file
    - Works with multi-line replacements
    """
    content = Path(path).read_text()
    count = content.count(old_string)
    if count == 0:
        return "ERROR: old_string not found in file"
    if count > 1:
        return "ERROR: old_string appears multiple times — add more context"
    new_content = content.replace(old_string, new_string, 1)
    Path(path).write_text(new_content)
    return "OK"


# ---- GLOB: Fast file discovery ----
def glob_files(pattern: str, base_dir: str = ".") -> list[str]:
    """Find files by name pattern. Better than find because:
    - Returns sorted by modification time
    - Understands ** patterns natively
    - Doesn't need shell escaping
    """
    return sorted(Path(base_dir).glob(pattern), key=lambda p: p.stat().st_mtime)


# ---- GREP: Content search ----
def grep_files(pattern: str, path: str = ".", file_type: str = None) -> list[dict]:
    """Search file contents with regex. Better than grep because:
    - Returns structured results (file, line_number, content)
    - Supports file type filtering
    - Multiple output modes (files_only, content, count)
    """
    results = []
    regex = re.compile(pattern, re.IGNORECASE)
    for p in Path(path).rglob("*"):
        if not p.is_file():
            continue
        if file_type and not p.suffix.endswith(file_type):
            continue
        try:
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if regex.search(line):
                    results.append({"file": str(p), "line": i, "content": line.strip()})
        except (UnicodeDecodeError, PermissionError):
            continue
    return results
```

---

## Concept 5: Context Offloading to Filesystem

This is a critical pattern for long-running agents. As the conversation grows, old tool results eat up the context window. The solution: **write results to files, then reference the file path instead of keeping the data in context.**

```python
# offloading.py — Write tool results to files to free context

from pathlib import Path
import hashlib

SCRATCH_DIR = Path("/tmp/kuro_scratch")


def offload_to_file(data: str, label: str) -> str:
    """
    Save a large tool result to a file instead of keeping it in context.
    Return a short reference the agent can use later.

    Manus (another agent) does exactly this:
    "writes old tool results to files and only applies
     summarization once there is diminishing returns from offloading."
    """
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    # Create a unique filename
    file_id = hashlib.md5(data.encode()).hexdigest()[:8]
    filename = f"{label}_{file_id}.txt"
    filepath = SCRATCH_DIR / filename
    filepath.write_text(data)

    # Return a SHORT reference instead of the full data
    line_count = len(data.splitlines())
    char_count = len(data)
    return (
        f"[Saved to {filepath}] "
        f"({line_count} lines, {char_count} chars). "
        f"Use read_file('{filepath}') to access."
    )


def smart_tool_result(name: str, result: str, threshold: int = 2000) -> str:
    """
    If a tool result is small, return it directly.
    If it's large, offload it to a file and return a reference.

    This keeps the context window lean without losing information.
    """
    if len(result) <= threshold:
        return result  # Small enough to keep in context

    # Too big — offload
    summary_lines = result.splitlines()[:5]
    summary = "\n".join(summary_lines)

    ref = offload_to_file(result, name)
    return f"{ref}\n\nPreview (first 5 lines):\n{summary}\n..."


# WHAT THE AGENT SEES IN CONTEXT:
#
# Without offloading (context fills up fast):
#   Tool result: [5000 lines of code pasted directly in context]
#
# With offloading (context stays lean):
#   Tool result: [Saved to /tmp/kuro_scratch/bash_output_a1b2c3d4.txt]
#   (5000 lines, 128000 chars). Use read_file() to access.
#   Preview (first 5 lines):
#   import logging
#   from pathlib import Path
#   ...
```

---

## Concept 6: Plans Tracked via Filesystem

Long-running agents track their progress by writing a plan file and periodically re-reading it. This solves the problem of losing track of what they're doing as context gets compressed.

```python
# plan_tracking.py — Filesystem-based plan for long tasks

from pathlib import Path


PLAN_FILE = Path("/tmp/kuro_plan.md")


def create_plan(goal: str, steps: list[str]) -> str:
    """
    Agent creates a plan at the start of a complex task.
    Writes it to a file so it survives context compression.
    """
    lines = [f"# Plan: {goal}", ""]
    for i, step in enumerate(steps, 1):
        lines.append(f"- [ ] Step {i}: {step}")
    lines.append("")
    lines.append("## Progress Notes")
    lines.append("")

    PLAN_FILE.write_text("\n".join(lines))
    return f"Plan created with {len(steps)} steps. Saved to {PLAN_FILE}"


def mark_step_done(step_num: int, notes: str = "") -> str:
    """
    Agent marks a step as done and adds notes.
    This way, even if the context window compresses,
    the agent can re-read the plan and know where it left off.
    """
    content = PLAN_FILE.read_text()
    old = f"- [ ] Step {step_num}:"
    new = f"- [x] Step {step_num}:"
    content = content.replace(old, new, 1)

    if notes:
        content += f"\n**Step {step_num}**: {notes}\n"

    PLAN_FILE.write_text(content)
    return f"Step {step_num} marked done."


def read_plan() -> str:
    """
    Agent re-reads the plan to remember what it's doing.
    Called after context compression or at start of a new turn.

    Claude Code does this: "Plans are stored on disk.
    Agents write plans to files and periodically read them
    back into context to reinforce objectives."
    """
    if not PLAN_FILE.exists():
        return "No active plan."
    return PLAN_FILE.read_text()


# EXAMPLE FLOW:
#
# 1. User: "Refactor the auth module to use JWT"
#
# 2. Agent calls create_plan("Refactor auth to JWT", [
#        "Read current auth implementation",
#        "Install pyjwt dependency",
#        "Create JWT token utilities",
#        "Update login endpoint",
#        "Update middleware",
#        "Run tests",
#    ])
#
# 3. Agent works through steps, calling mark_step_done() after each
#
# 4. Context gets compressed after step 3...
#    Agent calls read_plan() and sees:
#    - [x] Step 1: Read current auth implementation
#    - [x] Step 2: Install pyjwt dependency
#    - [x] Step 3: Create JWT token utilities
#    - [ ] Step 4: Update login endpoint      <- pick up here
#    - [ ] Step 5: Update middleware
#    - [ ] Step 6: Run tests
```

---

## Concept 7: Sub-Agent Context Isolation

When a task is complex, the main agent spawns child agents that work in isolated context windows. Each child agent:
- Gets its own fresh context (not polluted by the parent's history)
- Gets specific tools and instructions for its subtask
- Returns a short summary to the parent

```python
# sub_agents.py — Isolated child agents for parallel work

import concurrent.futures


def spawn_sub_agent(
    task: str,
    system_prompt: str,
    tools: list[dict],
    tool_executor,
) -> str:
    """
    Spawn a sub-agent with its own isolated context.

    The sub-agent gets:
    - Its own system prompt (can be different from parent)
    - Its own tools (can be restricted)
    - Its own conversation history (starts fresh)
    - No access to parent's conversation

    Returns only a short summary — parent doesn't see
    intermediate tool calls or reasoning.
    """
    # Fresh context — no parent history
    messages = [{"role": "user", "parts": [{"text": task}]}]

    # Run the agent loop (same function, different context)
    result = run_agent_loop(
        messages,
        tools,
        tool_executor,
        system_instruction=system_prompt,
    )

    return result  # Only the final answer goes back to parent


def parallel_sub_agents(tasks: list[dict]) -> list[str]:
    """
    Run multiple sub-agents in parallel.

    Claude Code does this for:
    - /batch: spawns 5-30 agents, each in its own git worktree
    - /simplify: spawns 3 review agents checking different things
    - Code review: each agent checks for a different issue type
    """
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(
                spawn_sub_agent,
                task["prompt"],
                task["system_prompt"],
                task["tools"],
                task["tool_executor"],
            ): task["name"]
            for task in tasks
        }

        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            result = future.result()
            results.append({"name": name, "result": result})

    return results


# EXAMPLE: Parallel code review
#
# Parent agent receives: "Review this PR"
# Parent spawns 3 sub-agents:
#
# Sub-agent 1: "Check for security vulnerabilities"
#   -> Gets: Read, Grep tools only (read-only)
#   -> Returns: "Found 2 issues: SQL injection in login.py:42, XSS in template.html:15"
#
# Sub-agent 2: "Check for performance issues"
#   -> Gets: Read, Grep, Bash(time python) tools
#   -> Returns: "N+1 query in users.py:88, unnecessary loop in data.py:120"
#
# Sub-agent 3: "Check test coverage"
#   -> Gets: Read, Grep, Bash(pytest --cov) tools
#   -> Returns: "Coverage: 73%. Missing tests for auth module"
#
# Parent agent combines all 3 results into one review.
# Each sub-agent used ~4K tokens of context.
# Without sub-agents, parent would need ~12K tokens for all the code.
```

---

## Concept 8: Infrastructure vs Tools — Two Layers of an Agent

Not everything in an agent is a "tool". There are two distinct layers, and confusing them is a common mistake.

```
+-----------------------------------------------------+
|  LAYER 1: INFRASTRUCTURE (runs BEFORE agent loop)    |
|                                                      |
|  scan_metadata()      <- called at startup           |
|  format_skill_index() <- called when building prompt |
|  load_skill_body()    <- called when skill activated  |
|  load_index()         <- called when building prompt |
|  build_system_prompt()<- called before agent loop     |
|                                                      |
|  These are YOUR code. The agent never sees them.     |
|  They shape what goes INTO the system prompt.        |
+------------------------------------------------------+
|  LAYER 2: TOOLS (called BY the agent during loop)    |
|                                                      |
|  read_file()          <- agent decides to call this  |
|  edit_file()          <- agent decides to call this  |
|  bash()               <- agent decides to call this  |
|  grep()               <- agent decides to call this  |
|  save_memory()        <- agent decides to call this  |
|  read_memory()        <- agent decides to call this  |
|  read_skill_resource()<- agent decides to call this  |
|  read_plan()          <- agent decides to call this  |
|                                                      |
|  These are in make_tools(). The agent calls them     |
|  via tool_use in the LLM response.                   |
+------------------------------------------------------+
```

Here's the full flow showing both layers in action:

```python
# The full flow when user types: "/deep-research transformers"

def run_conversation(user_message: str, user_id: str = "default"):

    # ============================================================
    # PHASE 1: BEFORE the agent loop (your code runs, not tools)
    # ============================================================

    # Step 1: scan_metadata() runs at startup
    # This is YOUR code reading the filesystem, not a tool call.
    # The agent doesn't even exist yet.
    skills_dir = Path("kuro/skills")
    metadata = scan_metadata(skills_dir)
    # metadata = {
    #   "deep-research": {"name": "deep-research", "description": "Multi-pass...", ...},
    #   "compare": {"name": "compare", "description": "Side-by-side...", ...},
    #   ...
    # }

    # Step 2: Detect slash command (your code, not a tool)
    skill_name = None
    clean_message = user_message
    if user_message.startswith("/"):
        parts = user_message.split(None, 1)
        cmd = parts[0][1:]  # "deep-research"
        if cmd in metadata:
            skill_name = cmd           # "deep-research"
            clean_message = parts[1]   # "transformers"

    # Step 3: Build system prompt (your code, not a tool)
    # This is where infrastructure functions get called:

    memory_index = load_index()
    # Returns: "# Memory Index\n- [user_prefs.md](...) - User preferences"

    skill_index = format_skill_index(metadata)
    # Returns: "## Available Skills\n- /deep-research: Multi-pass...\n- /compare: ..."

    skill_body = load_skill_body(metadata, "deep-research")
    # Returns: "# Deep Research Workflow\n## Pass 1: Decompose\n..."

    system_prompt = f"""You are Kuro.

## Your Memory
{memory_index}

{skill_index}

## Active Skill: /deep-research
{skill_body}
"""
    # The system prompt is now ~2000 tokens with everything injected.
    # The agent will SEE the skill instructions, but it didn't CALL
    # any function to get them — we built the prompt for it.


    # ============================================================
    # PHASE 2: Build the tool registry
    # ============================================================

    # These are functions the agent CAN call during the loop.
    # The agent sees their names + descriptions in the API request.
    tools = {
        "read_file": read_file,
        "edit_file": edit_file,
        "glob": glob_files,
        "grep": grep_files,
        "bash": execute_bash,
        "save_memory": save_memory,
        "read_memory": read_topic,         # Agent calls this to load detail
        "list_memories": list_topics,
        "read_skill_resource": lambda name, file: read_skill_resource(metadata, name, file),
        "create_plan": create_plan,
        "mark_done": mark_step_done,
        "read_plan": read_plan,
    }

    # Notice: scan_metadata, format_skill_index, load_skill_body,
    # build_system_prompt are NOT in this dict.
    # The agent can't call them — they already ran.


    # ============================================================
    # PHASE 3: The agent loop (LLM decides what tools to call)
    # ============================================================

    messages = [{"role": "user", "content": clean_message}]

    while True:
        # Send system_prompt + messages + tool definitions to LLM
        response = call_llm(system_prompt, messages, tool_definitions=tools)

        # LLM response might be:
        # "I'll use the deep-research workflow. Let me decompose this..."
        # tool_calls: [
        #   {"name": "grep", "args": {"pattern": "transformer", "path": "."}},
        # ]

        if not response.tool_calls:
            return response.text  # Final answer

        for call in response.tool_calls:
            # The agent chose to call grep — WE execute it
            tool_fn = tools[call.name]
            result = tool_fn(**call.args)
            messages.append({"role": "tool", "content": str(result)})

        # Loop back — LLM sees the tool result and decides next action
```

**Key takeaway:**

```python
# INFRASTRUCTURE functions (called by YOUR code):
# - Run before or around the agent loop
# - Shape the system prompt
# - The agent never knows they exist
# - Examples: scan_metadata, format_skill_index, load_skill_body, load_index

# TOOL functions (called by THE AGENT via LLM):
# - Registered in make_tools / tool registry
# - Agent sees their name + description
# - Agent decides when to call them
# - Examples: read_file, bash, grep, save_memory, read_plan
```

---

## Concept 9: The Meta-Tool Pattern (How Agents Auto-Activate Skills)

There's an important problem with the infrastructure-only approach to skills: **what if the agent wants to load a skill body itself, without a slash command?**

### The Problem: Simple Approach Can't Auto-Activate

With infrastructure-only skill loading, skill activation ONLY happens through your code:

```python
# Simple approach — skill body loaded ONLY via slash command

def run_conversation(user_message, user_id="default"):

    # YOUR code detects /slash command
    skill_name = None
    if user_message.startswith("/"):
        cmd = user_message.split()[0][1:]
        if cmd in metadata:
            skill_name = cmd   # skill activated HERE, by YOUR code

    # YOUR code loads the body into the prompt
    system_prompt = build_system_prompt(active_skill=skill_name)

    # Agent loop starts — skill body already in prompt (or not)
    return agent_loop(system_prompt, user_message, tools)
```

What happens when the user says "compare React and Vue" (no slash command)?

```
System prompt contains:
  ## Available Skills
  - /compare: Side-by-side comparison (triggers: compare, vs)

  When the user's request matches a skill, follow its workflow.

User says: "compare React and Vue"

Agent thinks: "This matches /compare."
Agent responds: "Using /compare skill..."

BUT — the agent only has the ONE LINE description.
It does NOT have the full workflow (Step 1: Identify Subjects, Step 2: Parallel Retrieval, etc.)
It's IMPROVISING based on "side-by-side comparison."
The structured multi-step workflow is never loaded.
```

### The Solution: Make Skill a Tool the Agent Can Call

Claude Code solves this by making `Skill` itself a tool in the agent's tool registry. The agent can call it when it decides a skill is relevant:

```python
# Meta-tool approach — agent can load skills itself

def activate_skill(skill_name: str) -> str:
    """
    META-TOOL: The agent calls this when it auto-detects a skill.

    This is NOT a regular tool — it doesn't do work directly.
    Instead, it returns the skill's full instructions,
    which get added to the conversation as a tool result.
    The agent then follows those instructions.
    """
    skill_data = get_skill(skill_name)
    if not skill_data:
        return json.dumps({"error": f"Unknown skill: {skill_name}"})

    return json.dumps({
        "status": "activated",
        "skill": skill_name,
        "instructions": skill_data["body"],  # Full workflow returned here
    })


# Register it as a tool the agent can call:
def make_tools(user_id, metadata):
    return {
        "read_file": read_file,
        "bash": execute_bash,
        "grep": grep_files,
        "save_memory": save_memory,

        # THE META-TOOL — agent calls this itself
        "activate_skill": activate_skill,
    }
```

### The Full Auto-Detection Flow

```python
# STEP 1: System prompt has the skill index + activate_skill tool
system_prompt = """You are Kuro.

Available tools: read_file, bash, grep, save_memory, activate_skill

## Available Skills
- /deep-research: Multi-pass research with citations (triggers: research, deep dive)
- /compare: Side-by-side comparison (triggers: compare, vs)
- /summarize: Comprehensive summary (triggers: summarize, overview)

When the user's request matches a skill, call activate_skill to load
the full workflow, then follow it.
"""

# STEP 2: User says something (no slash command)
user_message = "compare React and Vue"

# STEP 3: LLM decides to activate a skill (LLM's own choice)
llm_response = {
    "text": "",
    "tool_calls": [
        {
            "name": "activate_skill",        # Agent chose to call this
            "args": {"skill_name": "compare"} # Agent picked which skill
        }
    ]
}

# STEP 4: Your code executes the tool
result = activate_skill("compare")
# result = {
#   "status": "activated",
#   "skill": "compare",
#   "instructions": "# Comparison Workflow\n## Step 1: Identify Subjects\n..."
# }

# STEP 5: Result goes back as a tool response
messages.append({
    "role": "tool",
    "content": result   # Full skill body is now in context
})

# STEP 6: LLM sees the full instructions and follows them
# Now it has Step 1: Identify Subjects, Step 2: Parallel Retrieval, etc.
# It follows the structured workflow, not improvising.
```

### The Critical Difference

```
WITHOUT META-TOOL:
  /compare X Y  -> YOUR code loads body -> agent has full workflow  (GOOD)
  "compare X Y" -> agent improvises from one-line description      (BAD)

WITH META-TOOL:
  /compare X Y  -> YOUR code loads body -> agent has full workflow  (GOOD)
  "compare X Y" -> AGENT calls activate_skill -> gets full workflow (GOOD)

  Both paths end up the same! The agent always gets the full body.
```

### How Claude Code Actually Does It

Claude Code has a `Skill` tool that works exactly this way. When Claude sees the available skills list and decides one matches, it calls the Skill tool:

```python
# Claude Code's Skill tool (simplified)

# The tool definition:
SKILL_TOOL = {
    "name": "Skill",
    "description": "Activate a skill to get detailed workflow instructions.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Name of the skill to activate",
            },
        },
        "required": ["command"],
    },
}


# What happens when agent calls Skill(command="pdf"):
def handle_skill_tool(command: str) -> dict:
    skill_data = load_skill(command)

    # Returns two things:
    return {
        # 1. The instructions (injected as a hidden message)
        "instructions": skill_data["body"],

        # 2. A context modifier that pre-approves tools for this skill
        #    e.g., the pdf skill needs Bash(python) pre-approved
        "allowed_tools": skill_data.get("allowed_tools", []),
    }
```

The meta-tool pattern is what makes progressive disclosure truly agent-driven. Without it, progressive disclosure only works when YOUR code can detect what's needed. With it, the agent itself decides when to load more information — which is the whole point of progressive disclosure.

---

## Concept 10: Putting It All Together

Here's a complete minimal agent using all the patterns:

```python
# agent.py — Complete agent with all patterns

from pathlib import Path


# ---- Tool registry ----
# Few atomic tools + bash for everything else
# This is Claude Code's approach: ~12 tools total

def make_tools(user_id: str, skills_metadata: dict) -> dict:
    """
    Build the tool registry. Notice how FEW tools there are.
    Bash handles everything that doesn't need a dedicated tool.
    """
    return {
        # Dedicated file tools (safe, structured)
        "read_file": lambda path, offset=0, limit=2000: read_file(path, offset, limit),
        "edit_file": lambda path, old, new: edit_file(path, old, new),
        "glob": lambda pattern: glob_files(pattern),
        "grep": lambda pattern, path=".": grep_files(pattern, path),

        # Universal execution (anything goes)
        "bash": lambda command, timeout=120: execute_bash(command, timeout),

        # Memory tools (filesystem-backed, progressive)
        "save_memory": lambda topic, content, desc: save_memory(topic, content, desc),
        "read_memory": lambda topic: read_topic(topic),
        "list_memories": lambda: list_topics(),

        # Skill resources (tier 3 progressive disclosure)
        "read_skill_resource": lambda name, file: read_skill_resource(skills_metadata, name, file),

        # Plan tracking (filesystem-backed)
        "create_plan": lambda goal, steps: create_plan(goal, steps),
        "mark_done": lambda step, notes="": mark_step_done(step, notes),
        "read_plan": lambda: read_plan(),
    }


def run_conversation(user_message: str, user_id: str = "default"):
    """
    One conversation turn demonstrating all patterns:
    1. Load memory index (filesystem)
    2. Load skill index (progressive disclosure tier 1)
    3. Detect and activate skill (progressive disclosure tier 2)
    4. Agent uses bash + dedicated tools
    5. Large results get offloaded (context management)
    6. Plan tracked on filesystem
    """
    # Load skills metadata (tier 1 — lightweight)
    skills_dir = Path("kuro/skills")
    metadata = scan_metadata(skills_dir)

    # Detect slash command
    skill_name = None
    clean_message = user_message
    if user_message.startswith("/"):
        parts = user_message.split(None, 1)
        cmd = parts[0][1:]  # strip /
        if cmd in metadata:
            skill_name = cmd
            clean_message = parts[1] if len(parts) > 1 else user_message

    # Build system prompt with progressive disclosure
    system = build_system_prompt(
        metadata=metadata,
        memory_index=load_index(),       # Tier 1 memory
        active_skill=skill_name,          # Tier 2 skill (if activated)
    )

    # Set up tools
    tools = make_tools(user_id, metadata)

    # Run agent loop
    messages = [{"role": "user", "content": clean_message}]

    while True:
        response = call_llm(system, messages)

        if not response.tool_calls:
            return response.text

        for call in response.tool_calls:
            tool_fn = tools.get(call.name)
            if not tool_fn:
                result = f"Unknown tool: {call.name}"
            else:
                raw_result = tool_fn(**call.args)
                # Offload large results to filesystem
                result = smart_tool_result(call.name, str(raw_result))

            messages.append({"role": "tool", "content": result})
```

---

## Summary: The 9 Patterns

| # | Pattern | What | Token Impact |
|---|---------|------|-------------|
| 1 | **Filesystem as Memory** | Store memories as .md files, index always loaded, details on-demand | ~80% fewer tokens vs loading everything |
| 2 | **Progressive Disclosure** | 3 tiers: metadata -> instructions -> resources | Scales to unlimited skills/resources |
| 3 | **Bash as Universal Tool** | One tool that composes any shell action | ~30x fewer LLM round trips for complex tasks |
| 4 | **Dedicated File Tools** | Read/Edit/Glob/Grep with safety guarantees | Prevents corruption, sends minimal diffs |
| 5 | **Context Offloading** | Write large results to files, keep short references in context | Context window never fills up |
| 6 | **Plan Tracking** | Write plans to filesystem, re-read after compression | Agent never loses track of multi-step tasks |
| 7 | **Sub-Agent Isolation** | Child agents with fresh context for parallel subtasks | Linear context scaling instead of quadratic |
| 8 | **Infrastructure vs Tools** | Infrastructure shapes prompts before the loop; tools are called by the agent during the loop | Clear separation prevents architectural confusion |
| 9 | **Meta-Tool Pattern** | Make Skill a tool the agent can call to load its own instructions | Auto-detection works as well as explicit slash commands |

The fundamental insight: **the filesystem IS the database, Bash IS the API, and progressive disclosure IS the scaling strategy.**

---

## Sources

- [Claude Code Memory Docs](https://code.claude.com/docs/en/memory)
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Agent Design Patterns](https://rlancemartin.github.io/2026/01/09/agent_design/)
- [Equipping Agents with Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
