import json
import logging
import os
import pathlib
import shutil
import subprocess
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.1-pro-preview"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent")

# --- Sandbox config ---
WORKDIR = pathlib.Path.cwd().resolve()
SRT_SETTINGS = WORKDIR / "srt-settings.json"
SRT_PATH = shutil.which("srt")

# Tool definitions — these tell Gemini what functions it can call
TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "shell",
                "description": "Run a shell command and return its output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The shell command to run"}
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to read"}
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "edit_file",
                "description": "Edit a file by replacing an exact string with a new string. "
                "The old_string must match EXACTLY (including whitespace/indentation). "
                "Only the first occurrence is replaced. "
                "To insert new code, include surrounding lines in old_string for context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to edit"},
                        "old_string": {"type": "string", "description": "The exact string to find and replace"},
                        "new_string": {"type": "string", "description": "The replacement string"},
                    },
                    "required": ["path", "old_string", "new_string"],
                },
            },
            {
                "name": "create_file",
                "description": "Create a new file with the given content. Fails if the file already exists.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the new file"},
                        "content": {"type": "string", "description": "Content to write to the file"},
                    },
                    "required": ["path", "content"],
                },
            },
        ]
    }
]


def safe_path(path: str) -> str | None:
    """Resolve path and ensure it stays inside WORKDIR.

    This is our Python-level check (Layer 1). Even without srt,
    this prevents ../../../etc/passwd style escapes.
    """
    resolved = (WORKDIR / path).resolve()
    if not str(resolved).startswith(str(WORKDIR)):
        return None
    return str(resolved)


def confirm_action(tool_name: str, args: dict) -> bool:
    """Ask user before executing. Auto-approve reads (Layer 3).

    Like Claude Code's tiered permission system:
    - Tier 1: read_file auto-approved
    - Tier 2: everything else needs user approval
    """
    if tool_name == "read_file":
        return True
    print(f"\n  Tool: {tool_name}")
    print(f"  Args: {json.dumps(args, indent=2)}")
    answer = input("  Approve? [y/n]: ").strip().lower()
    return answer == "y"


def run_shell(command: str) -> str:
    """Run a shell command inside the srt sandbox (Layer 2).

    Instead of trying to parse commands for safety (weak allowlist),
    we let srt enforce OS-level restrictions:
    - Filesystem: can only write in project dir
    - Network: blocked entirely
    - Sensitive files (~/.ssh, ~/.aws): blocked from reading
    """
    try:
        if SRT_PATH:
            # OS-level sandboxing via Anthropic's sandbox-runtime
            result = subprocess.run(
                [SRT_PATH, "--settings", str(SRT_SETTINGS), "bash", "-c", command],
                capture_output=True, text=True, timeout=30,
            )
        else:
            # Fallback: run without sandbox (log a warning)
            log.warning("srt not found — running command WITHOUT sandbox")
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30,
            )
        return (result.stdout + result.stderr)[:4000]
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 30s"


def read_file(path: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return f"BLOCKED: '{path}' is outside the project directory"
    try:
        with open(resolved) as f:
            return f.read()
    except FileNotFoundError:
        return f"ERROR: file '{path}' not found"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return f"BLOCKED: '{path}' is outside the project directory"
    try:
        content = open(resolved).read()
    except FileNotFoundError:
        return f"ERROR: file '{path}' not found"

    if old_string not in content:
        return f"ERROR: old_string not found in '{path}'. Make sure it matches exactly."

    count = content.count(old_string)
    if count > 1:
        return f"ERROR: old_string appears {count} times in '{path}'. Make it more specific."

    new_content = content.replace(old_string, new_string, 1)
    with open(resolved, "w") as f:
        f.write(new_content)
    return f"OK: edited '{path}'"


def create_file(path: str, content: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return f"BLOCKED: '{path}' is outside the project directory"
    if os.path.exists(resolved):
        return f"ERROR: file '{path}' already exists. Use edit_file instead."
    with open(resolved, "w") as f:
        f.write(content)
    return f"OK: created '{path}'"


def call_gemini(contents: list[dict], tools: list[dict] | None = None) -> dict:
    """Make a raw HTTP POST to Gemini's generateContent endpoint.

    This is the lowest level — just JSON in, JSON out.
    Everything the model sees is in `contents`.
    """
    body = {"contents": contents}
    if tools:
        body["tools"] = tools

    resp = requests.post(
        API_URL,
        headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
        json=body,
    )
    resp.raise_for_status()
    return resp.json()


def extract_parts(response: dict) -> list[dict]:
    """Pull the parts list out of Gemini's response.

    Response shape: {"candidates": [{"content": {"role": "model", "parts": [...]}}]}
    """
    return response["candidates"][0]["content"]["parts"]


def get_response(contents: list[dict]) -> str:
    """The agent loop — call model, execute tools, repeat until we get text.

    Key concept: Gemini 3 uses 'thought signatures'. When the model returns
    a functionCall, each part may include a 'thoughtSignature' field. We MUST
    pass it back exactly as-is in the next request, or we get a 400 error.

    That's why we append the model's raw parts (including thoughtSignature)
    directly into the conversation history.
    """
    while True:
        start = time.time()
        response = call_gemini(contents, tools=TOOLS)
        log.info(f"Inference: {time.time() - start:.2f}s")

        parts = extract_parts(response)

        # Check if any part has a functionCall
        function_calls = [p for p in parts if "functionCall" in p]

        if not function_calls:
            # No tool calls — extract text and return
            text = "".join(p.get("text", "") for p in parts)
            print(text)
            # Append model response to history
            contents.append({"role": "model", "parts": parts})
            return text

        # Append the model's response AS-IS (preserves thoughtSignature!)
        # This is critical — if we rebuild the parts without thoughtSignature,
        # Gemini 3 will reject the next request.
        contents.append({"role": "model", "parts": parts})

        # Execute each function call and build response parts
        function_response_parts = []
        for part in function_calls:
            fc = part["functionCall"]
            name = fc["name"]
            args = fc["args"]
            log.info(f"Tool: {name}({args})")

            # Layer 3: User confirmation before executing
            if not confirm_action(name, args):
                result = "BLOCKED: user denied this action"
            elif name == "shell":
                result = run_shell(args.get("command", ""))
            elif name == "read_file":
                result = read_file(args.get("path", ""))
            elif name == "edit_file":
                result = edit_file(args.get("path", ""), args.get("old_string", ""), args.get("new_string", ""))
            elif name == "create_file":
                result = create_file(args.get("path", ""), args.get("content", ""))
            else:
                result = f"Unknown tool: {name}"

            function_response_parts.append({
                "functionResponse": {
                    "name": name,
                    "response": {"result": result},
                }
            })

        # Append tool results and loop back to call the model again
        contents.append({"role": "user", "parts": function_response_parts})


def main():
    # contents is our conversation history — just a list of dicts
    # This is ALL the state. No SDK objects, no hidden magic.
    contents = []

    if SRT_PATH:
        print(f"Agent ready. Sandbox: ON (srt at {SRT_PATH})")
    else:
        print("Agent ready. Sandbox: OFF (install @anthropic-ai/sandbox-runtime)")
    print(f"Working directory: {WORKDIR}")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Bye!")
            break

        # Add user message to history
        contents.append({"role": "user", "parts": [{"text": user_input}]})

        start = time.time()
        print("Agent: ", end="", flush=True)
        get_response(contents)
        log.info(f"Turn: {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()