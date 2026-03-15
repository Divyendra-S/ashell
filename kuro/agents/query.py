import json
import logging

from kuro.core.llm import run_agent_loop
from kuro.core.retrieval import rewrite_query, hybrid_retrieve, rrf_merge
from kuro.memory import store

log = logging.getLogger("kuro.query")

SYSTEM_PROMPT_TEMPLATE = (
    "You are a knowledge retrieval agent. Relevant context from the knowledge base "
    "has been retrieved for you below.\n\n"
    "## Retrieved Context\n{context}\n\n"
    "## Available Tools\n"
    "If the retrieved context is insufficient, you can use these tools to explore further:\n"
    "- get_facts_for_entity / get_relations_for_entity: Drill into specific entities\n"
    "- traverse_relations: Multi-hop graph exploration\n"
    "- grep_articles: Exact phrase search across article files\n"
    "- read_article: Load full article when you need more than a chunk\n"
    "- list_articles: Overview of all saved articles\n\n"
    "Cite your sources. If nothing is found, say so."
)

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "get_facts_for_entity",
                "description": "Get all facts stored about a specific entity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Exact name of the entity"},
                    },
                    "required": ["entity_name"],
                },
            },
            {
                "name": "get_relations_for_entity",
                "description": "Get all relationships involving a specific entity, with names resolved.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Exact name of the entity"},
                    },
                    "required": ["entity_name"],
                },
            },
            {
                "name": "traverse_relations",
                "description": "BFS graph traversal from an entity, depth 1-3. Finds multi-hop connections.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Starting entity name"},
                        "depth": {"type": "integer", "description": "How many hops to traverse (1-3, default 1)"},
                    },
                    "required": ["entity_name"],
                },
            },
            {
                "name": "grep_articles",
                "description": "Exact-match search across all saved article files on disk. Good for phrases, names, or code snippets that FTS might miss.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Text pattern to search for (case-insensitive)"},
                        "max_results": {"type": "integer", "description": "Max results to return (default 10)"},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "read_article",
                "description": "Load the full content of a saved article from disk.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the article file"},
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "list_articles",
                "description": "List all saved articles with title and file path. Lightweight overview.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
    }
]


def _execute_tool(name: str, args: dict) -> str:
    if name == "get_facts_for_entity":
        entity = store.get_entity_by_name(args["entity_name"])
        if not entity:
            return json.dumps({"error": f"Entity '{args['entity_name']}' not found"})
        facts = store.get_facts_for_entity(entity["id"])
        return json.dumps({"entity": entity, "facts": facts}, default=str)

    elif name == "get_relations_for_entity":
        entity = store.get_entity_by_name(args["entity_name"])
        if not entity:
            return json.dumps({"error": f"Entity '{args['entity_name']}' not found"})
        relations = store.get_relations_for_entity_enriched(entity["id"])
        return json.dumps({"entity": entity, "relations": relations}, default=str)

    elif name == "traverse_relations":
        entity = store.get_entity_by_name(args["entity_name"])
        if not entity:
            return json.dumps({"error": f"Entity '{args['entity_name']}' not found"})
        depth = min(args.get("depth", 1), 3)
        result = store.traverse(entity["id"], depth=depth)
        return json.dumps(result, default=str)

    elif name == "grep_articles":
        from kuro.memory.files import grep_articles
        results = grep_articles(args["pattern"], max_results=args.get("max_results", 10))
        return json.dumps(results, default=str)

    elif name == "read_article":
        from kuro.memory.files import get_article
        try:
            content = get_article(args["file_path"])
            return json.dumps({"file_path": args["file_path"], "content": content})
        except FileNotFoundError:
            return json.dumps({"error": f"Article not found: {args['file_path']}"})

    elif name == "list_articles":
        result = store.list_articles()
        return json.dumps(result, default=str)

    return f"Unknown tool: {name}"


def _format_context(results: list[dict]) -> str:
    if not results:
        return "No relevant results found in the knowledge base."

    entities = [r for r in results if r["type"] == "entity"]
    facts = [r for r in results if r["type"] == "fact"]
    chunks = [r for r in results if r["type"] == "article_chunk"]

    sections = []

    if entities:
        lines = ["### Entities"]
        for e in entities:
            etype = e.get("entity_type", "")
            label = f" ({etype})" if etype else ""
            lines.append(f"- **{e.get('title', '')}**{label}: {e.get('content', '')}")
        sections.append("\n".join(lines))

    if facts:
        lines = ["### Facts"]
        for f in facts:
            lines.append(f"- {f.get('content', '')}")
        sections.append("\n".join(lines))

    if chunks:
        lines = ["### Article Passages"]
        for c in chunks:
            title = c.get("title") or "Untitled"
            content = c.get("content", "")
            # Truncate to ~300 words
            words = content.split()
            if len(words) > 300:
                content = " ".join(words[:300]) + " ..."
            lines.append(f"**[{title}]**\n{content}\n")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def query(user_text: str, history: list[dict] | None = None) -> str:
    queries = rewrite_query(user_text)
    log.info(f"Rewritten queries: {queries}")
    raw = hybrid_retrieve(queries)
    top = rrf_merge(raw, top_k=8)
    context = _format_context(top)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return run_agent_loop(contents, TOOLS, _execute_tool, system_instruction=system_prompt)
