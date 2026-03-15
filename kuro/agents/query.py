import json
import logging

from kuro.core.llm import run_agent_loop
from kuro.core.retrieval import rewrite_query, hybrid_retrieve, rrf_merge
from kuro.memory import store
from kuro.skills import get_skill, get_skill_index

log = logging.getLogger("kuro.query")

SYSTEM_PROMPT_TEMPLATE = (
    "You are a knowledge retrieval agent. Relevant context from the knowledge base "
    "has been retrieved for you below.\n\n"
    "## Your Memory (about this user)\n{user_memory}\n\n"
    "## Retrieved Context\n{context}\n\n"
    "## Available Tools\n"
    "If the retrieved context is insufficient, you can use these tools to explore further:\n"
    "- get_facts_for_entity / get_relations_for_entity: Drill into specific entities\n"
    "- traverse_relations: Multi-hop graph exploration\n"
    "- grep_articles: Exact phrase search across article files\n"
    "- read_article: Load full article when you need more than a chunk\n"
    "- list_articles: Overview of all saved articles\n"
    "- save_memory: Save a memory about the user (preference, context, or instruction)\n"
    "- list_memories: List all saved memories for the current user\n"
    "- delete_memory: Remove a saved memory\n\n"
    "## Memory Management\n"
    "When the user shares personal preferences, context about themselves, or "
    "standing instructions, save them using save_memory. Do this proactively — "
    "you don't need to be explicitly asked. Examples:\n"
    "- 'I'm a backend engineer' → save as context\n"
    "- 'I prefer short answers' → save as preference\n"
    "- 'always check the deployment guide first' → save as instruction\n"
    "Confirm briefly when you save a memory.\n\n"
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
            {
                "name": "save_memory",
                "description": "Save a memory about the current user. Use proactively when user shares preferences, context, or instructions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Short identifier for this memory (e.g. 'preferred_response_style')"},
                        "content": {"type": "string", "description": "The memory content to save"},
                        "type": {
                            "type": "string",
                            "description": "Type of memory",
                            "enum": ["preference", "context", "instruction"],
                        },
                    },
                    "required": ["name", "content", "type"],
                },
            },
            {
                "name": "list_memories",
                "description": "List all saved memories for the current user.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "delete_memory",
                "description": "Delete a saved memory by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the memory to delete"},
                    },
                    "required": ["name"],
                },
            },
        ]
    }
]


def _format_user_memory(memories: list[dict]) -> str:
    if not memories:
        return "No memories saved for this user yet."

    grouped: dict[str, list[dict]] = {}
    for m in memories:
        grouped.setdefault(m["type"], []).append(m)

    sections = []
    for mem_type in ("preference", "context", "instruction"):
        items = grouped.get(mem_type, [])
        if items:
            lines = [f"### {mem_type.title()}s"]
            for item in items:
                lines.append(f"- **{item['name']}**: {item['content']}")
            sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _make_tool_executor(user_id: str):
    def execute_tool(name: str, args: dict) -> str:
        if name == "get_facts_for_entity":
            entity = store.get_entity_by_name(args["entity_name"], user_id=user_id)
            if not entity:
                return json.dumps({"error": f"Entity '{args['entity_name']}' not found"})
            facts = store.get_facts_for_entity(entity["id"])
            return json.dumps({"entity": entity, "facts": facts}, default=str)

        elif name == "get_relations_for_entity":
            entity = store.get_entity_by_name(args["entity_name"], user_id=user_id)
            if not entity:
                return json.dumps({"error": f"Entity '{args['entity_name']}' not found"})
            relations = store.get_relations_for_entity_enriched(entity["id"])
            return json.dumps({"entity": entity, "relations": relations}, default=str)

        elif name == "traverse_relations":
            entity = store.get_entity_by_name(args["entity_name"], user_id=user_id)
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
            result = store.list_articles(user_id=user_id)
            return json.dumps(result, default=str)

        elif name == "save_memory":
            result = store.upsert_user_memory(user_id, args["name"], args["type"], args["content"])
            return json.dumps({"status": "saved", "memory": result}, default=str)

        elif name == "list_memories":
            result = store.get_user_memories(user_id)
            return json.dumps(result, default=str)

        elif name == "delete_memory":
            deleted = store.delete_user_memory(user_id, args["name"])
            return json.dumps({"status": "deleted" if deleted else "not_found", "name": args["name"]})

        return f"Unknown tool: {name}"

    return execute_tool


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


def query(user_text: str, history: list[dict] | None = None, user_id: str = "default", skill: str | None = None) -> str:
    queries = rewrite_query(user_text)
    log.info(f"Rewritten queries: {queries}")
    raw = hybrid_retrieve(queries, user_id=user_id)
    top = rrf_merge(raw, top_k=8)
    context = _format_context(top)

    memories = store.get_user_memories(user_id)
    user_memory = _format_user_memory(memories)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context, user_memory=user_memory)

    # Append skill index for auto-detection
    system_prompt += "\n\n" + get_skill_index()

    # Append active skill body if explicitly activated
    if skill:
        skill_data = get_skill(skill)
        if skill_data:
            system_prompt += f"\n\n## Active Skill: /{skill_data['name']}\n{skill_data['body']}"

    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    tool_executor = _make_tool_executor(user_id)
    return run_agent_loop(contents, TOOLS, tool_executor, system_instruction=system_prompt)
