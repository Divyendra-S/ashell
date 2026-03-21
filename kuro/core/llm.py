import logging
import time
from collections.abc import Callable

import requests

from kuro.config import GEMINI_API_KEY, GEMINI_API_URL

log = logging.getLogger("kuro.llm")

EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"
BATCH_EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:batchEmbedContents"
EMBED_DIMENSIONS = 768


def embed_text(text: str) -> list[float]:
    resp = requests.post(
        EMBED_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json={"content": {"parts": [{"text": text}]}, "output_dimensionality": EMBED_DIMENSIONS},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


def embed_texts(texts: list[str]) -> list[list[float]]:
    requests_body = [
        {"model": f"models/{EMBEDDING_MODEL}",
         "content": {"parts": [{"text": t}]},
         "output_dimensionality": EMBED_DIMENSIONS}
        for t in texts
    ]
    resp = requests.post(
        BATCH_EMBED_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json={"requests": requests_body},
    )
    resp.raise_for_status()
    return [e["values"] for e in resp.json()["embeddings"]]


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
    guards: list[Callable[[str, dict], str | None]] | None = None,
) -> str:
    """Generalized agent loop. Calls Gemini, executes tools via callback, repeats until text.

    Args:
        guards: Optional list of guard functions. Each takes (tool_name, args) and returns
                an error message string if the call should be blocked, or None to allow it.
    """
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
