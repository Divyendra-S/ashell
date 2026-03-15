import json
import logging

from kuro.core.llm import run_agent_loop
from kuro.memory import store

log = logging.getLogger("kuro.ingest")

SYSTEM_PROMPT = (
    "You are a knowledge extraction agent. Extract entities, facts, and relations "
    "from user input. Use the provided tools to store them. After storing, confirm "
    "what you saved in a brief summary. "
    "If the user provides a URL, use scrape_url to fetch it, then save_article to "
    "store it, then extract key concepts as entities and facts using the existing tools."
)

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "store_entity",
                "description": "Store an entity (person, company, project, etc.) in the knowledge base.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the entity"},
                        "entity_type": {
                            "type": "string",
                            "description": "Type of entity",
                            "enum": ["person", "company", "project", "topic", "place", "event"],
                        },
                        "summary": {"type": "string", "description": "Brief description of the entity"},
                    },
                    "required": ["name", "entity_type"],
                },
            },
            {
                "name": "store_fact",
                "description": "Store a fact about an entity. The entity must exist or will be auto-created.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Name of the entity this fact is about"},
                        "content": {"type": "string", "description": "The fact content"},
                    },
                    "required": ["entity_name", "content"],
                },
            },
            {
                "name": "store_relation",
                "description": "Store a relationship between two entities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_name": {"type": "string", "description": "Name of the source entity"},
                        "relation_type": {"type": "string", "description": "Type of relationship (e.g. works_at, knows, manages)"},
                        "target_name": {"type": "string", "description": "Name of the target entity"},
                        "context": {"type": "string", "description": "Additional context about the relationship"},
                    },
                    "required": ["source_name", "relation_type", "target_name"],
                },
            },
            {
                "name": "scrape_url",
                "description": "Fetch a URL and convert its content to markdown. Use this when the user provides a URL to ingest.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to scrape"},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "save_article",
                "description": "Save a scraped article to disk and store its metadata. Use after scrape_url.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Article title"},
                        "content": {"type": "string", "description": "Article content in markdown"},
                        "topic": {"type": "string", "description": "Topic category for filing (e.g. ai, web, science)"},
                        "url": {"type": "string", "description": "Source URL of the article"},
                    },
                    "required": ["title", "content"],
                },
            },
        ]
    }
]


def _resolve_entity(name: str) -> dict:
    """Get entity by name, auto-creating if it doesn't exist."""
    entity = store.get_entity_by_name(name)
    if entity:
        return entity
    log.info(f"Auto-creating entity: {name}")
    return store.upsert_entity(name, "topic")


def _execute_tool(name: str, args: dict) -> str:
    if name == "store_entity":
        result = store.upsert_entity(
            args["name"],
            args["entity_type"],
            args.get("summary"),
        )
        return json.dumps({"status": "ok", "entity": result}, default=str)

    elif name == "store_fact":
        entity = _resolve_entity(args["entity_name"])
        result = store.insert_fact(entity["id"], args["content"])
        return json.dumps({"status": "ok", "fact": result}, default=str)

    elif name == "store_relation":
        source = _resolve_entity(args["source_name"])
        target = _resolve_entity(args["target_name"])
        result = store.insert_relation(
            source["id"],
            args["relation_type"],
            target["id"],
            args.get("context"),
        )
        return json.dumps({"status": "ok", "relation": result}, default=str)

    elif name == "scrape_url":
        from kuro.memory.scraper import scrape_url
        try:
            result = scrape_url(args["url"])
        except ValueError as e:
            return json.dumps({"error": str(e)})
        return json.dumps(result)

    elif name == "save_article":
        from kuro.memory.files import save_article as _save_article, chunk_text
        from kuro.core.llm import embed_texts
        file_path = _save_article(args["title"], args["content"], args.get("topic", "general"))
        row = store.insert_article(args.get("url", ""), args["title"], file_path)
        chunks = chunk_text(args["content"])
        chunk_rows = store.insert_article_chunks(row["id"], chunks)
        embeddings = embed_texts(chunks)
        for chunk_row, emb in zip(chunk_rows, embeddings):
            store.update_chunk_embedding(chunk_row["id"], emb)
        return json.dumps({"file_path": file_path, "article_id": row["id"],
                            "chunks": len(chunks), "embeddings_stored": len(embeddings)})

    return f"Unknown tool: {name}"


def ingest(user_text: str, history: list[dict] | None = None) -> str:
    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return run_agent_loop(contents, TOOLS, _execute_tool, system_instruction=SYSTEM_PROMPT)
