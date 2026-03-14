import json
import logging

from kuro.core.llm import run_agent_loop
from kuro.memory import store

log = logging.getLogger("kuro.query")

SYSTEM_PROMPT = (
    "You are a knowledge retrieval agent with a knowledge base of entities, facts, "
    "relations, and saved articles.\n\n"
    "Strategy — progressive disclosure:\n"
    "1. Start broad: search_knowledge to find entities, facts, and article passages in one call.\n"
    "2. Drill down: get_facts_for_entity or get_relations_for_entity for details. "
    "   traverse_relations for multi-hop connections. grep_articles for exact phrase matches.\n"
    "3. Go deep: read_article to load full article content when you need more context.\n\n"
    "Use list_articles for an overview of saved articles. "
    "Follow leads — search results point to entities or articles worth exploring. "
    "Cite your sources. If nothing is found, say so."
)

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "search_knowledge",
                "description": "Unified full-text search across entities, facts, and article chunks. Returns results grouped by type.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            },
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
    if name == "search_knowledge":
        result = store.search_knowledge_unified(args["query"])
        return json.dumps(result, default=str)

    elif name == "get_facts_for_entity":
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


def query(user_text: str, history: list[dict] | None = None) -> str:
    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return run_agent_loop(contents, TOOLS, _execute_tool, system_instruction=SYSTEM_PROMPT)
