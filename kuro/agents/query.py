import json
import logging

from kuro.core.llm import run_agent_loop, run_agent_loop_streaming
from kuro.core.retrieval import rewrite_query, hybrid_retrieve, rrf_merge, graph_retrieve
from kuro.memory import store
from kuro.skills import get_skill, get_skill_index, get_skill_guards, read_skill_data, append_skill_data

log = logging.getLogger("kuro.query")

SYSTEM_PROMPT_TEMPLATE = (
    "You are a knowledge retrieval agent. Relevant context from the knowledge base "
    "has been retrieved for you below.\n\n"
    "## User Profile\n{user_profile}\n\n"
    "## Your Memory (about this user)\n"
    "These are your top memories ranked by importance and recency. "
    "Use `search_memories` to find more.\n{user_memory}\n\n"
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
    "- search_memories: Search memories by keyword when you need context not shown above\n"
    "- delete_memory: Remove a saved memory\n\n"
    "## Memory Management\n"
    "When the user shares personal preferences, context about themselves, or "
    "standing instructions, save them using save_memory. Do this proactively — "
    "you don't need to be explicitly asked.\n\n"
    "**Importance levels (1-10):**\n"
    "- 9-10: Critical instructions ('never do X', 'always check Y first')\n"
    "- 7-8: Strong preferences ('I prefer short answers', 'I'm a backend engineer')\n"
    "- 5-6: Useful context ('studying React', 'works on project X')\n"
    "- 3-4: Casual facts ('mentioned liking Python', 'asked about topic Y')\n"
    "- 1-2: Ephemeral notes (temporary debugging context, one-off mentions)\n\n"
    "Examples:\n"
    "- 'I'm a backend engineer' → save as context, importance=7\n"
    "- 'I prefer short answers' → save as preference, importance=8\n"
    "- 'always check the deployment guide first' → save as instruction, importance=9\n"
    "- 'I'm debugging auth today' → save as context, importance=3, expires in 1 day\n"
    "Confirm briefly when you save a memory.\n\n"
    "## Memory Consolidation\n"
    "Only your top memories are shown above. When you notice related or redundant "
    "memories (e.g., multiple study sessions on the same topic), consolidate them "
    "into a single updated memory using save_memory with the same name. "
    "Prefer one evolving summary over many granular entries.\n\n"
    "## User Profile Management\n"
    "The User Profile above is a living markdown document you maintain. "
    "Use `update_profile` to keep it current when you learn significant new info "
    "about the user — background, expertise, active projects, knowledge gaps from "
    "study sessions, or preferences. Read the existing profile first (it's in the "
    "system prompt), then write back the full updated markdown. Don't update on "
    "every interaction — only when there's meaningful new information.\n\n"
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
                "description": "Save a memory about the current user. Use proactively when user shares preferences, context, or instructions. Assign importance based on how critical the memory is.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Short identifier for this memory (e.g. 'preferred_response_style'). Reuse the same name to update an existing memory."},
                        "content": {"type": "string", "description": "The memory content to save"},
                        "type": {
                            "type": "string",
                            "description": "Type of memory",
                            "enum": ["preference", "context", "instruction"],
                        },
                        "importance": {
                            "type": "integer",
                            "description": "How important is this memory? 1-2=ephemeral, 3-4=casual, 5-6=useful, 7-8=strong preference, 9-10=critical instruction. Default 5.",
                        },
                        "expires_at": {
                            "type": "string",
                            "description": "Optional ISO timestamp when this memory should expire. Use for temporary context (e.g. 'debugging auth today').",
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
            {
                "name": "search_memories",
                "description": "Search all saved memories by keyword. Use when the top memories shown in context aren't enough and you need to find older or lower-importance memories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search for in memory names and content"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "update_profile",
                "description": "Update the user's living profile — a markdown document summarizing their background, preferences, knowledge gaps, and active projects. Write the full markdown content (not a diff).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Full markdown content for the user profile"},
                    },
                    "required": ["content"],
                },
            },
        ]
    }
]

SKILL_HELPER_TOOLS = {
    "study": [
        {
            "functionDeclarations": [
                {
                    "name": "analyze_study_progress",
                    "description": "Analyze the user's study session history — returns avg scores, trends, weak/strong topics. Use before generating questions to avoid repeats and target weak areas.",
                    "parameters": {"type": "object", "properties": {}},
                },
            ]
        }
    ],
    "review": [
        {
            "functionDeclarations": [
                {
                    "name": "kb_health_report",
                    "description": "Analyze the knowledge base — returns entity/fact/article counts, orphan entities, sparse topics, and actionable suggestions.",
                    "parameters": {"type": "object", "properties": {}},
                },
            ]
        }
    ],
}

SKILL_DATA_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "read_skill_data",
                "description": "Read stored data from the active skill's data directory (e.g., past study sessions, research logs). Returns a list of JSON records.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Data file to read (e.g. 'sessions.jsonl', 'research_log.jsonl')"},
                    },
                    "required": ["filename"],
                },
            },
            {
                "name": "append_skill_data",
                "description": "Append a data record to the active skill's data directory. Use for saving session results, logs, or progress.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Data file to append to (e.g. 'sessions.jsonl')"},
                        "record": {"type": "object", "description": "JSON record to save"},
                    },
                    "required": ["filename", "record"],
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
    for mem_type in ("instruction", "preference", "context"):
        items = grouped.get(mem_type, [])
        if items:
            lines = [f"### {mem_type.title()}s"]
            for item in items:
                imp = item.get("importance", 5)
                imp_tag = f" [importance={imp}]" if imp != 5 else ""
                lines.append(f"- **{item['name']}**: {item['content']}{imp_tag}")
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
            result = store.upsert_user_memory(
                user_id, args["name"], args["type"], args["content"],
                importance=args.get("importance", 5),
                source=args.get("source", "agent"),
                expires_at=args.get("expires_at"),
            )
            consolidated = result.pop("_consolidated_from", [])
            response = {"status": "saved", "memory": result}
            if consolidated:
                response["consolidated_from"] = consolidated
            return json.dumps(response, default=str)

        elif name == "list_memories":
            result = store.get_user_memories(user_id)
            return json.dumps(result, default=str)

        elif name == "delete_memory":
            deleted = store.delete_user_memory(user_id, args["name"])
            return json.dumps({"status": "deleted" if deleted else "not_found", "name": args["name"]})

        elif name == "search_memories":
            results = store.search_user_memories(user_id, args["query"])
            return json.dumps(results, default=str)

        elif name == "update_profile":
            path = store.update_user_profile(user_id, args["content"])
            return json.dumps({"status": "updated", "path": path})

        return f"Unknown tool: {name}"

    return execute_tool


def _make_skill_data_executor(skill_name: str, user_id: str):
    def execute_tool(name: str, args: dict) -> str:
        if name == "read_skill_data":
            records = read_skill_data(skill_name, args["filename"], user_id=user_id)
            return json.dumps({"records": records, "count": len(records)}, default=str)
        elif name == "append_skill_data":
            result = append_skill_data(skill_name, args["filename"], args["record"], user_id=user_id)
            return json.dumps({"status": "saved", "message": result})
        elif name == "analyze_study_progress":
            from kuro.skills.study.scripts.analyze_progress import analyze_progress
            return json.dumps(analyze_progress(user_id), default=str)
        elif name == "kb_health_report":
            from kuro.skills.review.scripts.kb_health import kb_health_report
            return json.dumps(kb_health_report(user_id), default=str)
        return None
    return execute_tool


def _format_context(results: list[dict]) -> str:
    if not results:
        return "No relevant results found in the knowledge base."

    entities = [r for r in results if r["type"] == "entity"]
    facts = [r for r in results if r["type"] == "fact"]
    chunks = [r for r in results if r["type"] == "article_chunk"]
    graph_items = [r for r in results if r["type"] == "graph_neighborhood"]
    community_items = [r for r in results if r["type"] == "community_summary"]

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

    if graph_items:
        lines = ["### Graph Neighborhood"]
        for g in graph_items:
            etype = g.get("entity_type", "")
            label = f" ({etype})" if etype else ""
            lines.append(f"**{g.get('title', '')}**{label}")
            lines.append(g.get("content", ""))
            lines.append("")
        sections.append("\n".join(lines))

    if community_items:
        lines = ["### Topic Clusters"]
        for c in community_items:
            lines.append(f"- **{c.get('title', '')}**: {c.get('content', '')}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def query(user_text: str, history: list[dict] | None = None, user_id: str = "default", skill: str | None = None) -> str:
    queries = rewrite_query(user_text)
    log.info(f"Rewritten queries: {queries}")
    raw = hybrid_retrieve(queries, user_id=user_id)
    top = rrf_merge(raw, top_k=8)

    # Graph-aware retrieval: pull structured neighborhood context
    graph_context = graph_retrieve(user_text, user_id=user_id)
    top.extend(graph_context)

    context = _format_context(top)

    memories = store.get_top_memories(user_id, limit=10)
    user_memory = _format_user_memory(memories)
    user_profile = store.read_user_profile(user_id) or "No profile yet. Create one when you learn about this user."
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context, user_memory=user_memory, user_profile=user_profile)

    # Append skill index for auto-detection
    system_prompt += "\n\n" + get_skill_index()

    # Append active skill body if explicitly activated
    if skill:
        skill_data = get_skill(skill)
        if skill_data:
            system_prompt += f"\n\n## Active Skill: /{skill_data['name']}\n{skill_data['body']}"

    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    # Compose tools: always include base tools, add skill data tools when a skill is active
    active_tools = list(TOOLS)
    base_executor = _make_tool_executor(user_id)
    guards = get_skill_guards(skill) if skill else None

    if skill:
        active_tools.extend(SKILL_DATA_TOOLS)
        if skill in SKILL_HELPER_TOOLS:
            active_tools.extend(SKILL_HELPER_TOOLS[skill])
        skill_data_executor = _make_skill_data_executor(skill, user_id)

        def combined_executor(name: str, args: dict) -> str:
            result = skill_data_executor(name, args)
            if result is not None:
                return result
            return base_executor(name, args)

        return run_agent_loop(contents, active_tools, combined_executor, system_instruction=system_prompt, guards=guards)

    return run_agent_loop(contents, active_tools, base_executor, system_instruction=system_prompt)


def query_streaming(user_text: str, history: list[dict] | None = None, user_id: str = "default", skill: str | None = None):
    """Streaming variant of query(). Yields ("step"|"delta", data) tuples."""
    queries = rewrite_query(user_text)
    log.info(f"Rewritten queries: {queries}")
    raw = hybrid_retrieve(queries, user_id=user_id)
    top = rrf_merge(raw, top_k=8)

    graph_context = graph_retrieve(user_text, user_id=user_id)
    top.extend(graph_context)

    context = _format_context(top)

    memories = store.get_top_memories(user_id, limit=10)
    user_memory = _format_user_memory(memories)
    user_profile = store.read_user_profile(user_id) or "No profile yet. Create one when you learn about this user."
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context, user_memory=user_memory, user_profile=user_profile)

    system_prompt += "\n\n" + get_skill_index()

    if skill:
        skill_data = get_skill(skill)
        if skill_data:
            system_prompt += f"\n\n## Active Skill: /{skill_data['name']}\n{skill_data['body']}"

    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    active_tools = list(TOOLS)
    base_executor = _make_tool_executor(user_id)
    guards = get_skill_guards(skill) if skill else None

    if skill:
        active_tools.extend(SKILL_DATA_TOOLS)
        if skill in SKILL_HELPER_TOOLS:
            active_tools.extend(SKILL_HELPER_TOOLS[skill])
        skill_data_executor = _make_skill_data_executor(skill, user_id)

        def combined_executor(name: str, args: dict) -> str:
            result = skill_data_executor(name, args)
            if result is not None:
                return result
            return base_executor(name, args)

        yield from run_agent_loop_streaming(contents, active_tools, combined_executor, system_instruction=system_prompt, guards=guards)
    else:
        yield from run_agent_loop_streaming(contents, active_tools, base_executor, system_instruction=system_prompt)
