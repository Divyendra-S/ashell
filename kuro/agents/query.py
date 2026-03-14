import json
import logging

from kuro.core.llm import run_agent_loop
from kuro.memory import store

log = logging.getLogger("kuro.query")

SYSTEM_PROMPT = (
    "You are a knowledge retrieval agent. Search the knowledge base to answer questions. "
    "Follow leads — if you find an entity, get its facts and relations to build a complete answer. "
    "Cite what you find. If nothing is found, say so."
)

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "search_entities",
                "description": "Full-text search across entity names and summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "search_facts",
                "description": "Full-text search across all stored facts.",
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
                        "entity_name": {"type": "string", "description": "Name of the entity"},
                    },
                    "required": ["entity_name"],
                },
            },
            {
                "name": "get_relations_for_entity",
                "description": "Get all relationships involving a specific entity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Name of the entity"},
                    },
                    "required": ["entity_name"],
                },
            },
        ]
    }
]


def _execute_tool(name: str, args: dict) -> str:
    if name == "search_entities":
        results = store.search_entities(args["query"])
        return json.dumps(results, default=str)

    elif name == "search_facts":
        results = store.search_facts(args["query"])
        return json.dumps(results, default=str)

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
        relations = store.get_relations_for_entity(entity["id"])
        return json.dumps({"entity": entity, "relations": relations}, default=str)

    return f"Unknown tool: {name}"


def query(user_text: str, history: list[dict] | None = None) -> str:
    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return run_agent_loop(contents, TOOLS, _execute_tool, system_instruction=SYSTEM_PROMPT)
