import json
import logging

from kuro.core.llm import run_agent_loop, run_agent_loop_streaming
from kuro.memory import store
from kuro.skills import read_skill_data, append_skill_data

log = logging.getLogger("kuro.ingest")

SYSTEM_PROMPT = (
    "You are a knowledge extraction agent for a personal learning system. "
    "Your goal is to extract concepts that are genuinely useful for studying and understanding.\n\n"

    "## Extraction Process\n"
    "1. First, use scrape_url (if given a URL), then save_article.\n"
    "2. Read the full article carefully. Identify 3-8 key concepts worth studying.\n"
    "3. For EACH concept, call in order:\n"
    "   a) store_entity — with a rich 2-3 sentence summary\n"
    "   b) store_fact (1-3 per concept) — each an explanatory paragraph, not a bare claim\n"
    "   c) store_passage (1-2 per concept) — the relevant paragraph(s) from the article verbatim\n"
    "   d) store_relation — connect concepts to each other with context\n\n"

    "## Quality Standards\n"
    "- SUMMARIES: 2-3 sentences. What it is, why it matters, when you'd use it. "
    "Bad: 'A design technique.' "
    "Good: 'A design strategy that reveals information progressively as users need it, "
    "reducing cognitive load. Commonly used in onboarding flows and documentation.'\n"
    "- FACTS: Self-contained explanatory paragraph (3-5 sentences). Include reasoning, "
    "an example from the article, and why it matters. "
    "Bad: 'X reduces cognitive load.' "
    "Good: 'X reduces cognitive load by hiding advanced options until the user signals "
    "readiness. For example, [specific example from article]. This resulted in [outcome].'\n"
    "- PASSAGES: Copy 1-3 relevant paragraphs from the article that best explain this concept. "
    "Direct quotes or close paraphrases a learner would want to re-read.\n"
    "- RELATIONS: Always populate context — explain WHY these concepts are related.\n\n"

    "## Entity Rules\n"
    "- Use entity_type 'topic' for study-worthy concepts. Only use 'person', 'company', etc. "
    "when the entity itself IS the subject of study.\n"
    "- Prioritize abstract concepts, techniques, methodologies over proper nouns.\n"
    "- Relation types: subtopic_of, related_to, requires, enables, contrasts_with, "
    "builds_on, part_of, example_of.\n\n"
    "After all extractions, confirm what you saved."
)

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "store_entity",
                "description": "Store a concept or topic in the knowledge base. Prefer type 'topic' for study-worthy concepts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the entity"},
                        "entity_type": {
                            "type": "string",
                            "description": "Type of entity",
                            "enum": ["person", "company", "project", "topic", "place", "event"],
                        },
                        "summary": {"type": "string", "description": "2-3 sentences: what it is, why it matters, and when/where it's used."},
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
                        "content": {"type": "string", "description": "A self-contained explanatory paragraph (3-5 sentences). Include reasoning, examples, and significance."},
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
                        "relation_type": {"type": "string", "description": "Type of relationship (e.g. subtopic_of, related_to, requires, enables, builds_on, contrasts_with, part_of, example_of)"},
                        "target_name": {"type": "string", "description": "Name of the target entity"},
                        "context": {"type": "string", "description": "Explain WHY these concepts are related (1-2 sentences). Always populate this field."},
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
                "name": "lookup_entity",
                "description": "Check if an entity already exists in the KB. Use before store_entity to avoid duplicates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Name of the entity to look up"},
                    },
                    "required": ["entity_name"],
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
            {
                "name": "store_passage",
                "description": "Store a relevant passage from the article that explains a concept. Extract 1-2 key paragraphs per concept.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Name of the entity this passage explains"},
                        "article_id": {"type": "integer", "description": "The article_id returned by save_article"},
                        "content": {"type": "string", "description": "The relevant paragraph(s) from the article, quoted or closely paraphrased. 2-8 sentences explaining this concept in context."},
                    },
                    "required": ["entity_name", "article_id", "content"],
                },
            },
        ]
    }
]


def _resolve_entity(name: str, user_id: str = "default") -> dict:
    """Get entity by name, auto-creating if it doesn't exist."""
    entity = store.get_entity_by_name(name, user_id=user_id)
    if entity:
        return entity
    log.info(f"Auto-creating entity: {name}")
    return store.upsert_entity(name, "topic", user_id=user_id)


def _make_tool_executor(user_id: str):
    def execute_tool(name: str, args: dict) -> str:
        if name == "store_entity":
            result = store.upsert_entity(
                args["name"],
                args["entity_type"],
                args.get("summary"),
                user_id=user_id,
            )
            return json.dumps({"status": "ok", "entity": result}, default=str)

        elif name == "store_fact":
            entity = _resolve_entity(args["entity_name"], user_id=user_id)
            result = store.insert_fact(entity["id"], args["content"], user_id=user_id)
            return json.dumps({"status": "ok", "fact": result}, default=str)

        elif name == "store_relation":
            source = _resolve_entity(args["source_name"], user_id=user_id)
            target = _resolve_entity(args["target_name"], user_id=user_id)
            result = store.insert_relation(
                source["id"],
                args["relation_type"],
                target["id"],
                args.get("context"),
                user_id=user_id,
            )
            return json.dumps({"status": "ok", "relation": result}, default=str)

        elif name == "lookup_entity":
            entity = store.get_entity_by_name(args["entity_name"], user_id=user_id)
            if entity:
                facts = store.get_facts_for_entity(entity["id"])
                return json.dumps({"exists": True, "entity": entity, "facts": facts}, default=str)
            return json.dumps({"exists": False, "entity_name": args["entity_name"]})

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
            row = store.insert_article(args.get("url", ""), args["title"], file_path, user_id=user_id)
            chunks = chunk_text(args["content"])
            chunk_rows = store.insert_article_chunks(row["id"], chunks, user_id=user_id)
            embeddings = embed_texts(chunks)
            for chunk_row, emb in zip(chunk_rows, embeddings):
                store.update_chunk_embedding(chunk_row["id"], emb)
            return json.dumps({"file_path": file_path, "article_id": row["id"],
                                "chunks": len(chunks), "embeddings_stored": len(embeddings)})

        elif name == "store_passage":
            entity = _resolve_entity(args["entity_name"], user_id=user_id)
            result = store.insert_entity_passage(
                entity["id"], args["article_id"], args["content"], user_id=user_id,
            )
            return json.dumps({"status": "ok", "passage": result}, default=str)

        return f"Unknown tool: {name}"

    return execute_tool


SKILL_DATA_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "read_skill_data",
                "description": "Read stored data from the active skill's data directory. Returns a list of JSON records.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Data file to read (e.g. 'sessions.jsonl')"},
                    },
                    "required": ["filename"],
                },
            },
            {
                "name": "append_skill_data",
                "description": "Append a data record to the active skill's data directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Data file to append to"},
                        "record": {"type": "object", "description": "JSON record to save"},
                    },
                    "required": ["filename", "record"],
                },
            },
        ]
    }
]


def ingest(user_text: str, history: list[dict] | None = None, user_id: str = "default",
           skill_instructions: str | None = None, skill_name: str | None = None) -> str:
    system = SYSTEM_PROMPT
    if skill_instructions:
        system += "\n\n" + skill_instructions
    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    active_tools = list(TOOLS)
    base_executor = _make_tool_executor(user_id)

    if skill_name:
        active_tools.extend(SKILL_DATA_TOOLS)

        def combined_executor(name: str, args: dict) -> str:
            if name == "read_skill_data":
                records = read_skill_data(skill_name, args["filename"], user_id=user_id)
                return json.dumps({"records": records, "count": len(records)}, default=str)
            elif name == "append_skill_data":
                result = append_skill_data(skill_name, args["filename"], args["record"], user_id=user_id)
                return json.dumps({"status": "saved", "message": result})
            return base_executor(name, args)

        return run_agent_loop(contents, active_tools, combined_executor, system_instruction=system)

    return run_agent_loop(contents, active_tools, base_executor, system_instruction=system)


def ingest_streaming(user_text: str, history: list[dict] | None = None, user_id: str = "default",
                     skill_instructions: str | None = None, skill_name: str | None = None):
    """Streaming variant of ingest(). Yields ("step"|"delta", data) tuples."""
    system = SYSTEM_PROMPT
    if skill_instructions:
        system += "\n\n" + skill_instructions
    contents = history or []
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    active_tools = list(TOOLS)
    base_executor = _make_tool_executor(user_id)

    if skill_name:
        active_tools.extend(SKILL_DATA_TOOLS)

        def combined_executor(name: str, args: dict) -> str:
            if name == "read_skill_data":
                records = read_skill_data(skill_name, args["filename"], user_id=user_id)
                return json.dumps({"records": records, "count": len(records)}, default=str)
            elif name == "append_skill_data":
                result = append_skill_data(skill_name, args["filename"], args["record"], user_id=user_id)
                return json.dumps({"status": "saved", "message": result})
            return base_executor(name, args)

        yield from run_agent_loop_streaming(contents, active_tools, combined_executor, system_instruction=system)
    else:
        yield from run_agent_loop_streaming(contents, active_tools, base_executor, system_instruction=system)
