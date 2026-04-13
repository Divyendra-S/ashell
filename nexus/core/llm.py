import json
import logging
import time
from collections.abc import Callable, Generator

import requests

from nexus.core.config import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_STREAM_URL

log = logging.getLogger("nexus.llm")

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


_SUMMARY_PROMPT = """\
You are an indexing assistant for a personal knowledge base. Given an article, write a concise summary (2-3 sentences, max 250 chars) that helps an AI agent decide whether to read this article when answering user questions.

Your summary MUST:
- State the core topic and key concepts covered
- Mention specific techniques, tools, or frameworks discussed
- Use concrete terms a user would search for (not vague words like "explores" or "discusses")

Your summary MUST NOT:
- Include author bios, publication info, or dates
- Start with "This article..." — just state what it covers
- Include markdown formatting or links
"""

FLASH_MODEL = "gemini-2.5-flash"
FLASH_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{FLASH_MODEL}:generateContent"


def generate_article_summary(title: str, content: str) -> str:
    truncated = content[:3000]
    if len(content) > 3000:
        truncated += "\n\n[... article continues ...]"
    try:
        resp = requests.post(
            FLASH_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": _SUMMARY_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": f"Article title: {title}\n\n{truncated}"}]}],
            },
        )
        resp.raise_for_status()
        parts = resp.json()["candidates"][0]["content"]["parts"]
        summary = parts[0].get("text", "").strip()
        if len(summary) > 300:
            summary = summary[:297] + "..."
        return summary
    except Exception as e:
        log.warning(f"Summary generation failed: {e}")
        return ""


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

        contents.append({"role": "model", "parts": parts})

        function_response_parts = []
        for part in function_calls:
            fc = part["functionCall"]
            name = fc["name"]
            args = fc["args"]
            log.info(f"Tool: {name}({args})")

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


def stream_gemini(
    contents: list[dict],
    tools: list[dict] | None = None,
    system_instruction: str | None = None,
) -> Generator[dict, None, None]:
    body: dict = {"contents": contents}
    if tools:
        body["tools"] = tools
    if system_instruction:
        body["system_instruction"] = {"parts": [{"text": system_instruction}]}

    resp = requests.post(
        GEMINI_STREAM_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=body,
        stream=True,
    )
    resp.raise_for_status()

    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            try:
                chunk = json.loads(line[6:])
                yield chunk
            except json.JSONDecodeError:
                continue


def run_agent_loop_streaming(
    contents: list[dict],
    tools: list[dict],
    tool_executor: Callable[[str, dict], str],
    system_instruction: str | None = None,
    guards: list[Callable[[str, dict], str | None]] | None = None,
) -> Generator[tuple[str, dict | str], None, None]:
    while True:
        start = time.time()
        all_parts: list[dict] = []
        pending_deltas: list[str] = []
        has_function_calls = False

        for chunk in stream_gemini(contents, tools=tools, system_instruction=system_instruction):
            candidates = chunk.get("candidates", [])
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                all_parts.append(p)
                if "functionCall" in p:
                    has_function_calls = True
                elif "text" in p:
                    if has_function_calls:
                        pending_deltas.append(p["text"])
                    else:
                        yield ("delta", p["text"])

        log.info(f"Inference (stream): {time.time() - start:.2f}s")

        if not has_function_calls:
            contents.append({"role": "model", "parts": all_parts})
            for delta in pending_deltas:
                yield ("delta", delta)
            return

        contents.append({"role": "model", "parts": all_parts})

        function_calls = [p for p in all_parts if "functionCall" in p]
        function_response_parts = []
        for part in function_calls:
            fc = part["functionCall"]
            name = fc["name"]
            args = fc.get("args", {})
            log.info(f"Tool: {name}({args})")

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
                "functionResponse": {
                    "name": name,
                    "response": {"result": result},
                }
            })

        contents.append({"role": "user", "parts": function_response_parts})
