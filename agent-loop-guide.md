# Building AI Agents in Python: Functional Agent Loop Pattern

A practical reference for building LLM-powered agents using a **functional programming** approach in Python — no classes, no frameworks, just functions, closures, and dicts.

This pattern is extracted from a production agent (Kuro) and can be adapted to any LLM provider (Gemini, OpenAI, Anthropic, etc.).

---

## Architecture Overview

```
API / CLI
  │
  ▼
Entry Point ─── chat(message, history, context)
  │
  ├── Build system prompt (pulls live context)
  ├── Assemble tools list (declarative JSON)
  ├── Create tool executor (closure over context)
  │
  ▼
Agent Loop ─── run_agent_loop(contents, tools, executor, guards)
  │
  │  ┌──────────────────────────────────────┐
  │  │  1. Call LLM with messages + tools   │
  │  │  2. If text response → return        │
  │  │  3. If tool calls:                   │
  │  │     a. Run guards (permission check) │
  │  │     b. Execute each tool via callback│
  │  │     c. Append results to history     │
  │  │     d. Loop back to step 1           │
  │  └──────────────────────────────────────┘
  │
  ▼
Final text response
```

---

## Core Components

### 1. The Agent Loop

The heart of the system. A single pure function that loops until the LLM returns text instead of tool calls.

```python
from collections.abc import Callable

def call_llm(contents: list[dict], tools: list[dict] | None = None,
             system_instruction: str | None = None) -> dict:
    """Call your LLM provider. Returns raw response dict."""
    # Adapt to your provider: OpenAI, Gemini, Anthropic, etc.
    ...

def extract_parts(response: dict) -> list[dict]:
    """Extract message parts from LLM response."""
    return response["candidates"][0]["content"]["parts"]

def run_agent_loop(
    contents: list[dict],
    tools: list[dict],
    tool_executor: Callable[[str, dict], str],
    system_instruction: str | None = None,
    guards: list[Callable[[str, dict], str | None]] | None = None,
) -> str:
    """Agent loop. Calls LLM, executes tools via callback, repeats until text."""
    while True:
        response = call_llm(contents, tools=tools, system_instruction=system_instruction)
        parts = extract_parts(response)
        function_calls = [p for p in parts if "functionCall" in p]

        # No tool calls → return text response
        if not function_calls:
            text = "".join(p.get("text", "") for p in parts)
            contents.append({"role": "model", "parts": parts})
            return text

        # Tool calls → execute and loop
        contents.append({"role": "model", "parts": parts})

        function_response_parts = []
        for part in function_calls:
            fc = part["functionCall"]
            name, args = fc["name"], fc["args"]

            # Check guards before executing
            blocked = None
            if guards:
                for guard in guards:
                    blocked = guard(name, args)
                    if blocked:
                        break

            result = blocked if blocked else tool_executor(name, args)

            function_response_parts.append({
                "functionResponse": {
                    "name": name,
                    "response": {"result": result},
                }
            })

        contents.append({"role": "user", "parts": function_response_parts})
```

**Key properties:**
- Stateless — conversation history is passed in, not stored
- LLM-agnostic — swap `call_llm` for any provider
- Behavior is injected via `tool_executor` and `guards` callbacks

### 2. Tool Definitions (Declarative JSON)

Tools are data, not code. Define them as plain dicts matching your LLM's function-calling schema.

```python
TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "read_file",
                "description": "Read a file by path. Returns file content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "content": {"type": "string", "description": "Content to write"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "search",
                "description": "Search across files for a pattern.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Max results (default 10)"},
                    },
                    "required": ["query"],
                },
            },
        ]
    }
]
```

### 3. Tool Executor (Closure Factory)

Tools are executed via a **factory function** that creates a closure over shared context (user ID, config, DB connection, etc.). No classes needed.

```python
import json

def _make_tool_executor(user_id: str):
    """Factory: returns an executor function closed over user_id."""

    def execute_tool(name: str, args: dict) -> str:
        if name == "read_file":
            content = read_file(user_id, args["path"])
            if content is None:
                return json.dumps({"error": f"Not found: {args['path']}"})
            return json.dumps({"path": args["path"], "content": content})

        elif name == "write_file":
            result = write_file(user_id, args["path"], args["content"])
            return json.dumps({"status": "saved", "path": result})

        elif name == "search":
            results = search(user_id, args["query"], max_results=args.get("max_results", 10))
            return json.dumps({"results": results, "count": len(results)})

        return json.dumps({"error": f"Unknown tool: {name}"})

    return execute_tool
```

**Why closures over classes:**
- No `self`, no `__init__`, no inheritance hierarchy
- Context is captured at creation time, immutable after
- Easy to compose — just wrap one function with another

### 4. Guards (Permission System)

Guards are pure functions that intercept tool calls and optionally block them. Return an error string to block, `None` to allow.

```python
_WRITE_TOOLS = {"write_file", "delete_file", "update_config"}

def guard_read_only(name: str, args: dict) -> str | None:
    """Block all write tools — read-only mode."""
    if name in _WRITE_TOOLS:
        return f"Tool '{name}' is blocked: running in read-only mode."
    return None

def guard_path_allowlist(name: str, args: dict) -> str | None:
    """Only allow file operations within /data."""
    if "path" in args and not args["path"].startswith("data/"):
        return f"Access denied: path must be under data/"
    return None
```

Pass guards to the agent loop:

```python
run_agent_loop(
    contents, tools, executor,
    guards=[guard_read_only, guard_path_allowlist],
)
```

### 5. Composable Executors

When you need multiple sets of tools (e.g., base tools + feature-specific tools), compose executors via wrapping — not inheritance.

```python
def _make_feature_executor(feature_name: str, user_id: str):
    def execute_tool(name: str, args: dict) -> str:
        if name == "feature_specific_tool":
            return json.dumps(do_feature_thing(feature_name, args))
        return None  # Not handled → fall through

    return execute_tool


# In your entry point:
base_executor = _make_tool_executor(user_id)
feature_executor = _make_feature_executor("analytics", user_id)

def combined_executor(name: str, args: dict) -> str:
    result = feature_executor(name, args)
    if result is not None:
        return result
    return base_executor(name, args)

run_agent_loop(contents, all_tools, combined_executor)
```

### 6. System Prompt (Rebuilt Per Request)

The system prompt is a pure function that pulls live context on every call. No stale state.

```python
SYSTEM_PROMPT_TEMPLATE = (
    "You are an assistant that helps the user manage their project.\n\n"
    "## User Profile\n{user_profile}\n\n"
    "## Available Data\n{data_index}\n\n"
    "## How You Work\n"
    "- Use tools to read data before answering\n"
    "- Cite sources in your response\n"
)

def _build_system_prompt(user_id: str) -> str:
    user_profile = db.get_profile(user_id) or "No profile yet."
    data_index = db.get_index(user_id) or "No data yet."

    return SYSTEM_PROMPT_TEMPLATE.format(
        user_profile=user_profile,
        data_index=data_index,
    )
```

### 7. Entry Point (Wiring It All Together)

A single function that assembles everything and kicks off the loop.

```python
def chat(
    user_text: str,
    history: list[dict] | None = None,
    user_id: str = "default",
) -> str:
    system_prompt = _build_system_prompt(user_id)

    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    executor = _make_tool_executor(user_id)

    return run_agent_loop(
        contents, TOOLS, executor,
        system_instruction=system_prompt,
    )
```

---

## Streaming Variant

For real-time UIs, the same loop but yields events instead of returning a string.

```python
from collections.abc import Generator

def run_agent_loop_streaming(
    contents: list[dict],
    tools: list[dict],
    tool_executor: Callable[[str, dict], str],
    system_instruction: str | None = None,
    guards: list[Callable[[str, dict], str | None]] | None = None,
) -> Generator[tuple[str, dict | str], None, None]:
    """Yields events: ("delta", text_chunk) and ("step", {tool, args, status})."""
    while True:
        all_parts = []
        has_function_calls = False

        for chunk in stream_llm(contents, tools=tools, system_instruction=system_instruction):
            parts = extract_stream_parts(chunk)
            for p in parts:
                all_parts.append(p)
                if "functionCall" in p:
                    has_function_calls = True
                elif "text" in p and not has_function_calls:
                    yield ("delta", p["text"])

        if not has_function_calls:
            contents.append({"role": "model", "parts": all_parts})
            return

        contents.append({"role": "model", "parts": all_parts})

        function_calls = [p for p in all_parts if "functionCall" in p]
        function_response_parts = []
        for part in function_calls:
            fc = part["functionCall"]
            name, args = fc["name"], fc.get("args", {})

            yield ("step", {"tool": name, "args": args, "status": "running"})

            blocked = None
            if guards:
                for guard in guards:
                    blocked = guard(name, args)
                    if blocked:
                        break
            result = blocked if blocked else tool_executor(name, args)

            yield ("step", {"tool": name, "args": args, "status": "done"})

            function_response_parts.append({
                "functionResponse": {"name": name, "response": {"result": result}}
            })

        contents.append({"role": "user", "parts": function_response_parts})
```

**Frontend consumes via SSE:**

```python
from fastapi.responses import StreamingResponse

@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    def generate():
        for event_type, data in chat_streaming(req.message, history=req.history):
            if event_type == "step":
                yield f"event: step\ndata: {json.dumps(data)}\n\n"
            elif event_type == "delta":
                yield f"event: delta\ndata: {json.dumps({'text': data})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Project Structure

```
your_agent/
├── core/
│   └── llm.py              # Agent loop + LLM calls (provider-agnostic)
├── agents/
│   └── main.py             # Tool defs, executor factories, entry points
├── memory/                  # Storage layer (DB, files, etc.)
│   ├── store.py
│   └── files.py
├── skills/                  # Optional: pluggable skill modules
│   └── __init__.py
├── api.py                   # FastAPI routes (stateless)
├── cli.py                   # CLI entry point
└── config.py                # Env vars, constants
```

---

## Principles

1. **No classes** — Functions and dicts only. Closures capture context.
2. **Agent loop is generic** — It knows nothing about your domain. Behavior comes from the executor callback and tool definitions you pass in.
3. **Tools are data** — JSON declarations, not decorated functions. Easy to filter, merge, or generate dynamically.
4. **Executors are factories** — `_make_tool_executor(context)` returns a closure. Compose them by wrapping, not inheriting.
5. **Guards are pure functions** — `(name, args) -> str | None`. Stack them as a list.
6. **System prompt is rebuilt per request** — Pull live context every time. No stale state.
7. **History is passed in, not stored** — The caller owns session management. The loop is stateless.
8. **Return JSON strings from tools** — Uniform interface. The LLM parses them.
9. **Streaming and sync share the same logic** — Only the outer loop differs (return vs yield).

---

## Quick Start Checklist

- [ ] Implement `call_llm()` for your provider
- [ ] Define your `TOOLS` as declarative JSON
- [ ] Write `_make_tool_executor()` with your tool implementations
- [ ] Write `_build_system_prompt()` with your context
- [ ] Wire up `chat()` as the entry point
- [ ] Add guards if you need permission control
- [ ] Add streaming variant for real-time UIs
- [ ] Expose via API (FastAPI) or CLI
