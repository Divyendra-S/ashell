# Plan: Add Proper Sandboxing to ashell Agent

## Context

Our agent (`agent.py`) currently has a **weak allowlist-based** approach to safety:

```python
SAFE_COMMANDS = {"ls", "cat", "echo", "python", "pip", "pytest", "git"}
```

This is easily bypassed. The model can:
- `python -c "import os; os.system('rm -rf /')"` — allowed because first word is `python`
- `git push --force` — allowed because first word is `git`
- `read_file("/etc/passwd")` — no path restrictions at all
- `edit_file("/etc/hosts", ...)` — can write anywhere on disk

**This is NOT how industry tools do it.** Here's what they actually do:

### How Codex Does It
- Runs the agent inside a **Docker container / microVM** with its own filesystem
- **Network disabled** during task execution (can't exfiltrate data)
- Agent has full access *inside* the container, but the container itself is isolated
- Two-phase: setup scripts run with internet, then agent runs without

### How Claude Code Does It
- Uses **OS-level sandboxing** (Linux bubblewrap, macOS seatbelt)
- **Filesystem isolation**: read/write only in the working directory, blocked outside
- **Network isolation**: only allowed through a controlled proxy
- **User approval**: dangerous actions prompt the user for confirmation
- Reduces permission prompts by 84% compared to ask-every-time

### What Our Agent Has (Current)
- Command allowlist (first-word check) — easily bypassed
- Timeout on shell commands — good but not enough
- No filesystem path restrictions
- No network isolation
- No user confirmation for dangerous actions

---

## Recommended Approach: Layered Security (Practical for Learning)

Since we're building a learning project, we won't set up Docker/microVMs. Instead, we'll implement **3 layers** that teach the same concepts:

### Layer 1: Working Directory Restriction (like Claude Code's filesystem isolation)
- All file operations (`read_file`, `edit_file`, `create_file`) restricted to the project directory
- Resolve paths and check they don't escape via `../` tricks
- Block access to sensitive files (`.env`, `.git/config`, etc.)

### Layer 2: Smarter Shell Safety (like Codex's restricted execution)
- Parse full command, not just first word
- Block dangerous subcommands: `rm -rf`, `git push --force`, `curl | sh`, etc.
- Block shell tricks: pipes to `sh`, backticks, `$(...)`, `;` chaining
- Block `python -c` with dangerous imports

### Layer 3: User Confirmation (like Claude Code's permission prompts)
- Before executing ANY tool, show the user what's about to happen
- User types `y` to approve or `n` to reject
- Add an "auto-approve" mode for read-only operations (reading files is safe)

---

## Files to Modify

- **`agent.py`** — all changes go here (single file project)

## Implementation Details

### Layer 1: Path sandboxing
```python
import pathlib

WORKDIR = pathlib.Path.cwd().resolve()

def safe_path(path: str) -> str | None:
    """Resolve path and ensure it's inside WORKDIR."""
    resolved = (WORKDIR / path).resolve()
    if not str(resolved).startswith(str(WORKDIR)):
        return None  # path escape attempt
    return str(resolved)
```
Apply this check in `read_file`, `edit_file`, `create_file`.

### Layer 2: Shell command validation
```python
DANGEROUS_PATTERNS = ["rm -rf", "rm -r /", "> /dev", "| sh", "| bash",
                      "curl | ", "wget | ", "$(", "`", "sudo", "chmod 777"]

def is_safe_command(cmd: str) -> bool:
    first_word = cmd.strip().split()[0]
    if first_word not in SAFE_COMMANDS:
        return False
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd:
            return False
    return True
```

### Layer 3: User confirmation
```python
def confirm_action(tool_name: str, args: dict) -> bool:
    """Ask user before executing. Auto-approve reads."""
    if tool_name == "read_file":
        return True  # reads are safe
    print(f"\n  Tool: {tool_name}")
    print(f"  Args: {json.dumps(args, indent=2)}")
    answer = input("  Approve? [y/n]: ").strip().lower()
    return answer == "y"
```
Call this in the tool dispatch section before executing.

## Verification

1. Run `uv run agent.py`
2. Ask: "read /etc/passwd" — should be blocked (outside workdir)
3. Ask: "edit main.py" — should prompt for confirmation
4. Ask: "run rm -rf /" — should be blocked (dangerous pattern)
5. Ask: "list my files" — shell `ls` should work after confirmation
6. Ask: "read main.py" — should auto-approve (read-only)

## Sources

- [Codex Security](https://developers.openai.com/codex/security/)
- [Claude Code Sandboxing Docs](https://code.claude.com/docs/en/sandboxing)
- [Anthropic Engineering: Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Docker Sandboxes for Agent Safety](https://www.docker.com/blog/docker-sandboxes-a-new-approach-for-coding-agent-safety/)
- [NVIDIA: Sandboxing Agentic Workflows](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)
