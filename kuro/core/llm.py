import logging
import time
from collections.abc import Callable

import requests

from kuro.config import GEMINI_API_KEY, GEMINI_API_URL

log = logging.getLogger("kuro.llm")


def call_gemini(contents: list[dict], tools: list[dict] | None = None, system_instruction: str | None = None) -> dict:
    body = {"contents": contents}
    if tools:
        body["tools"] = tools
    if system_instruction:
        body["system_instruction"] = {"parts": [{"text": system_instruction}]}

    resp = requests.post(
        GEMINI_API_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=body,
    )
    resp.raise_for_status()
    return resp.json()


def extract_parts(response: dict) -> list[dict]:
    return response["candidates"][0]["content"]["parts"]


def run_agent_loop(
    contents: list[dict],
    tools: list[dict],
    tool_executor: Callable[[str, dict], str],
    system_instruction: str | None = None,
) -> str:
    """Generalized agent loop. Calls Gemini, executes tools via callback, repeats until text."""
    while True:
        start = time.time()
        response = call_gemini(contents, tools=tools, system_instruction=system_instruction)
        log.info(f"Inference: {time.time() - start:.2f}s")

        parts = extract_parts(response)
        function_calls = [p for p in parts if "functionCall" in p]

        if not function_calls:
            text = "".join(p.get("text", "") for p in parts)
            contents.append({"role": "model", "parts": parts})
            return text

        # Preserve thoughtSignature by appending raw parts
        contents.append({"role": "model", "parts": parts})

        function_response_parts = []
        for part in function_calls:
            fc = part["functionCall"]
            name = fc["name"]
            args = fc["args"]
            log.info(f"Tool: {name}({args})")

            result = tool_executor(name, args)

            function_response_parts.append({
                "functionResponse": {
                    "name": name,
                    "response": {"result": result},
                }
            })

        contents.append({"role": "user", "parts": function_response_parts})
