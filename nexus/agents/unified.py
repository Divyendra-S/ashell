import json
import logging

from nexus.core.llm import run_agent_loop, run_agent_loop_streaming
from nexus.graph import wiki, articles, memories
from nexus.graph.progress import get_last_session, get_entries_by_type
from nexus.skills import (
    get_skill, get_skill_index, get_skill_guards,
    read_skill_data, append_skill_data,
)

log = logging.getLogger("nexus.unified")


SYSTEM_PROMPT_TEMPLATE = (
    "You are Nexus, a personal knowledge assistant. You help the user learn, "
    "remember, and retrieve information. You maintain a knowledge graph of concepts "
    "as the user's knowledge base.\n\n"

    "## User Profile\n{user_profile}\n\n"

    "## Your Memories\n"
    "These are your memories about this user. Update them when you learn something "
    "important (preferences, context, instructions). Use `update_memories` to rewrite "
    "the full file — read the current content from above.\n"
    "{user_memories}\n\n"

    "## Wiki Index\n"
    "This is the table of contents of the user's knowledge base. Each entry links to "
    "a concept page you can read with `read_wiki_page`.\n"
    "{wiki_index}\n\n"

    "## Saved Articles\n"
    "These are articles the user has saved. Each entry has a title and a summary describing what's "
    "in it. Pick the articles whose summaries match the question and read them with `read_article`. "
    "Only fall back to `grep_articles` if no summary matches.\n"
    "{article_index}\n\n"

    "## Recent Changes\n{wiki_recent}\n\n"

    "## Last Check-in\n{last_checkin}\n\n"

    "## Pending Goals\n{pending_goals}\n\n"

    "## How You Work\n"
    "You decide what to do based on the user's message. There is no separate mode.\n\n"

    "**When the user asks a question:**\n"
    "1. Look at the **Wiki Index** and **Saved Articles** above. Each entry has a title and a "
    "summary describing what's in it. Pick every page whose title or summary matches what the "
    "user is asking about — don't stop at the first hit.\n"
    "2. Read each picked page with `read_wiki_page` (for concepts) or `read_article` (for "
    "articles). Issue these reads in parallel when possible.\n"
    "3. Follow [[backlinks]] inside the pages you read — if a concept references [[Related Topic]] "
    "and that topic is in the index, read it too.\n"
    "4. Synthesize the answer from everything you read. **Cite ALL sources you used**, not just "
    "the first one.\n"
    "5. **Fallback only if the indices don't contain anything matching the user's wording**: use "
    "`search_knowledge` to do a keyword scan across the full content of every page. This catches "
    "cases where the user's terminology doesn't match the curated titles/summaries.\n"
    "6. **At the very end of your response**, always add a brief 'Sources:' line listing the "
    "article titles and/or concept pages you read. Example:\n"
    "   Sources: *Prompt Caching Is Everything*, *LLM Optimization*\n\n"

    "**When the user shares knowledge or a URL:**\n"
    "1. If URL: use `scrape_url` then `save_article` to save it\n"
    "2. Extract key concepts and write concept pages with `write_wiki_page`\n"
    "3. Use `[[Concept Name]]` backlinks to connect related concepts\n"
    "4. Update `_recent.md` with what you added\n"
    "5. The wiki index auto-updates for new concept pages\n"
    "6. If reorganizing the index, use `update_wiki_index` to rewrite it\n\n"

    "**When the user shares personal info or preferences:**\n"
    "Update `user/memories.md` using `update_memories`. Read the current content "
    "from above, make your changes, write back the full file.\n\n"

    "**Concept page format:**\n"
    "```markdown\n"
    "# Concept Name\n\n"
    "Summary paragraph explaining what it is and why it matters.\n\n"
    "## Key Facts\n"
    "- Fact with explanation and context\n"
    "- Another fact\n\n"
    "## Connections\n"
    "- [[Related Concept]] — why they're related\n"
    "- [[Another Concept]] — context\n\n"
    "## Source\n"
    "- From: *Article Title* (if extracted from a saved article)\n\n"
    "## Notes\n"
    "- User notes go here\n"
    "```\n\n"

    "If nothing relevant is found, say so. Don't make things up."
)


# --- Tool declarations ---

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "read_wiki_page",
                "description": "Read a wiki page by path (e.g., 'concepts/attention-mechanism.md'). Returns the full markdown content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path within the wiki (e.g., 'concepts/transformers.md')"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_wiki_page",
                "description": "Write or update a wiki page. For new concept pages under concepts/, the index is auto-updated. Use [[Concept Name]] for backlinks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path (e.g., 'concepts/attention-mechanism.md')"},
                        "content": {"type": "string", "description": "Full markdown content for the page"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_wiki_pages",
                "description": "List all wiki pages in a directory. Returns relative file paths.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory to list (e.g., 'concepts'). Omit for all pages."},
                    },
                },
            },
            {
                "name": "grep_wiki",
                "description": "FALLBACK keyword search across wiki concept pages only. Use only when the Wiki Index in the system prompt doesn't surface a matching concept.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Text pattern to search for"},
                        "max_results": {"type": "integer", "description": "Max results to return (default 10)"},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "search_knowledge",
                "description": "FALLBACK keyword search across all wiki pages and articles. Only use when the indices don't have matching titles or summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language search query"},
                        "max_results": {"type": "integer", "description": "Max results (default 15)"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "update_memories",
                "description": "Rewrite the user's memories file. Read the current content from the system prompt, make changes, write back the FULL file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Full markdown content for memories file"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "update_wiki_index",
                "description": "Rewrite the wiki index. Use when reorganizing topics. The index auto-appends for new pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Full markdown content for the wiki index"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "update_wiki_recent",
                "description": "Rewrite the recent changes file. Keep the last ~20 entries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Full markdown content for recent changes"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "scrape_url",
                "description": "Fetch a URL and convert its content to markdown.",
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
                "description": "Save a scraped article to the knowledge base. Use after scrape_url.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Article title"},
                        "content": {"type": "string", "description": "Article content in markdown"},
                        "topic": {"type": "string", "description": "Topic category (e.g. ai, web, science)"},
                        "url": {"type": "string", "description": "Source URL"},
                    },
                    "required": ["title", "content"],
                },
            },
            {
                "name": "grep_articles",
                "description": "Search across all saved articles for a pattern.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Text pattern to search for"},
                        "max_results": {"type": "integer", "description": "Max results (default 10)"},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "read_article",
                "description": "Load the full content of a saved article.",
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
                "description": "List all saved articles with title and file path.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "update_profile",
                "description": "Update the user's profile — a markdown document about their background, expertise, and preferences.",
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
                    "description": "Analyze the user's study session history — returns avg scores, trends, weak/strong topics.",
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
                    "description": "Analyze the wiki knowledge base — returns concept counts, orphan pages, sparse topics, and suggestions.",
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
                "description": "Read stored data from the active skill's data directory.",
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


# --- Tool executor ---


def _make_tool_executor(user_id: str):
    def execute_tool(name: str, args: dict) -> str:
        if name == "read_wiki_page":
            content = wiki.read_page(user_id, args["path"])
            if content is None:
                return json.dumps({"error": f"Page not found: {args['path']}"})
            return json.dumps({"path": args["path"], "content": content})

        elif name == "write_wiki_page":
            result_path = wiki.write_page(user_id, args["path"], args["content"])
            return json.dumps({"status": "saved", "path": result_path})

        elif name == "list_wiki_pages":
            pages = wiki.list_pages(user_id, args.get("directory"))
            return json.dumps({"pages": pages, "count": len(pages)})

        elif name == "grep_wiki":
            results = wiki.grep_wiki(user_id, args["pattern"], max_results=args.get("max_results", 10))
            return json.dumps({"results": results, "count": len(results)})

        elif name == "search_knowledge":
            results = wiki.search_knowledge(user_id, args["query"], max_results=args.get("max_results", 15))
            return json.dumps({"results": results, "count": len(results)})

        elif name == "update_memories":
            path = wiki.write_memories(user_id, args["content"])
            return json.dumps({"status": "updated", "path": path})

        elif name == "update_wiki_index":
            path = wiki.write_index(user_id, args["content"])
            return json.dumps({"status": "updated", "path": path})

        elif name == "update_wiki_recent":
            path = wiki.write_recent(user_id, args["content"])
            return json.dumps({"status": "updated", "path": path})

        elif name == "scrape_url":
            from nexus.core.scraper import scrape_url
            try:
                result = scrape_url(args["url"])
            except ValueError as e:
                return json.dumps({"error": str(e)})
            return json.dumps(result)

        elif name == "save_article":
            file_path = f"articles/{args.get('topic', 'general')}/{args['title'][:50]}.md"
            row = articles.insert_article(args.get("url", ""), args["title"], file_path, user_id=user_id)
            # Store article content in Neo4j
            articles.save_article_content(row["id"], args["content"])
            return json.dumps({"file_path": file_path, "article_id": row["id"]})

        elif name == "grep_articles":
            results = articles.grep_articles(args["pattern"], max_results=args.get("max_results", 10), user_id=user_id)
            return json.dumps(results, default=str)

        elif name == "read_article":
            content = articles.get_article_content(args["file_path"], user_id=user_id)
            if content is None:
                return json.dumps({"error": f"Article not found: {args['file_path']}"})
            return json.dumps({"file_path": args["file_path"], "content": content})

        elif name == "list_articles":
            result = articles.list_articles(user_id=user_id)
            return json.dumps(result, default=str)

        elif name == "update_profile":
            path = memories.write_profile(user_id, args["content"])
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
        return None
    return execute_tool


# --- Context formatting ---


def _format_last_checkin(session: dict | None) -> str:
    if not session:
        return "No previous check-ins."
    summary = session.get("summary") or "No summary"
    started = session.get("started_at", "unknown")
    entries = session.get("entries", [])
    lines = [f"**Date**: {started}", f"**Summary**: {summary}"]
    if entries:
        lines.append("**Entries**:")
        for e in entries[:10]:
            lines.append(f"  - [{e.get('entry_type', '')}] {e.get('content', '')}")
    return "\n".join(lines)


def _format_goals(goals: list[dict]) -> str:
    if not goals:
        return "No pending goals."
    lines = []
    for g in goals:
        meta = g.get("metadata", {})
        if isinstance(meta, str):
            meta = {}
        date = meta.get("target_date", "")
        date_str = f" (target: {date})" if date else ""
        lines.append(f"- {g.get('content', '')}{date_str}")
    return "\n".join(lines)


def _build_system_prompt(user_id: str, skill: str | None = None) -> str:
    user_profile = memories.read_profile(user_id) or "No profile yet. Share about yourself and I'll remember."
    user_memories = memories.read_memories(user_id) or "No memories saved yet."
    wiki_index = wiki.read_index(user_id) or "Wiki is empty. Start sharing knowledge and I'll build it."
    wiki_recent = wiki.read_recent(user_id) or "No recent changes."

    # Article index
    try:
        article_list = articles.list_articles(user_id=user_id)
        if article_list:
            article_lines = []
            for a in article_list[:30]:
                summary = a.get("summary", "")
                if summary:
                    article_lines.append(f"- **{a['title']}** (`{a['file_path']}`) — {summary}")
                else:
                    article_lines.append(f"- **{a['title']}** (`{a['file_path']}`)")
            article_index = "\n".join(article_lines)
        else:
            article_index = "No articles saved yet."
    except Exception:
        article_index = "No articles saved yet."

    try:
        last_session = get_last_session(user_id)
    except Exception:
        last_session = None
    try:
        pending_goals = get_entries_by_type(user_id, "goal", limit=5)
    except Exception:
        pending_goals = []

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_profile=user_profile,
        user_memories=user_memories,
        wiki_index=wiki_index,
        article_index=article_index,
        wiki_recent=wiki_recent,
        last_checkin=_format_last_checkin(last_session),
        pending_goals=_format_goals(pending_goals),
    )

    system_prompt += "\n\n" + get_skill_index()

    if skill:
        skill_data = get_skill(skill)
        if skill_data:
            system_prompt += f"\n\n## Active Skill: /{skill_data['name']}\n{skill_data['body']}"

    return system_prompt


# --- Main entry points ---


SLASH_CMD_PATTERN = __import__("re").compile(r"^/(\w+)\s*(.*)", __import__("re").DOTALL)


def detect_skill(message: str) -> str | None:
    match = SLASH_CMD_PATTERN.match(message)
    if match:
        cmd = match.group(1).lower()
        skill = get_skill(cmd)
        if skill:
            return cmd
    return None


def chat(
    user_text: str,
    history: list[dict] | None = None,
    user_id: str = "default",
    skill: str | None = None,
) -> str:
    system_prompt = _build_system_prompt(user_id, skill)

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

        return run_agent_loop(
            contents, active_tools, combined_executor,
            system_instruction=system_prompt, guards=guards,
        )

    return run_agent_loop(
        contents, active_tools, base_executor,
        system_instruction=system_prompt,
    )


def chat_streaming(
    user_text: str,
    history: list[dict] | None = None,
    user_id: str = "default",
    skill: str | None = None,
):
    system_prompt = _build_system_prompt(user_id, skill)

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

        yield from run_agent_loop_streaming(
            contents, active_tools, combined_executor,
            system_instruction=system_prompt, guards=guards,
        )
    else:
        yield from run_agent_loop_streaming(
            contents, active_tools, base_executor,
            system_instruction=system_prompt,
        )
