import json
import logging

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.tts import GroqTTSService
from pipecat.services.llm_service import FunctionCallParams

from kuro.config import GEMINI_API_KEY, GROQ_API_KEY
from kuro.memory import store, wiki, checkin_store

log = logging.getLogger("kuro.voice")

VOICE_SYSTEM_PROMPT = """\
You are Kuro, a friendly voice assistant for daily check-ins. You help the user \
reflect on their day — what they learned, articles they read, progress on goals, \
and plans for tomorrow.

## Your Personality
- Warm, concise, conversational — this is voice, keep responses SHORT (1-3 sentences)
- Gently drive the conversation but allow free-form discussion
- Ask follow-up questions to draw out insights
- Be encouraging about progress and non-judgmental about missed goals

## User Profile
{user_profile}

## Your Memory (about this user)
{user_memory}

## Last Check-in
{last_checkin}

## Pending Goals
{pending_goals}

## Today's Date
{today_date}

## Conversation Flow
1. Greet the user warmly. If there are pending goals from last time, ask about progress.
2. Ask what they worked on or learned today.
3. If they mention reading articles, use mark_article_read to track them.
4. When they share learnings, use save_learning to capture key concepts.
5. Ask about plans for tomorrow, use save_goal to save them.
6. When the conversation naturally wraps up, use end_session.

## Rules
- NEVER give long responses. This is voice — keep it to 1-3 sentences per turn.
- Use tools proactively. When the user says "I read that article about X", search and mark it.
- When the user shares something important about themselves, use save_memory.
- If asked about past check-ins, use get_last_checkin.
- If asked about goals, use get_recent_goals.
- Do not announce tool usage verbally. Just do it and respond naturally.
- If the user wants to discuss freely, follow their lead. Don't force the flow.

## CRITICAL: Granular Capture
- Save EACH distinct learning, concept, or topic as a SEPARATE save_learning call. \
If the user mentions "graph regularization" AND "file system storage", that is TWO learnings, not one.
- Save EACH distinct goal or plan as a SEPARATE save_goal call. \
"Read about voice agents" and "read that skills article" are TWO goals.
- If mark_article_read returns "not_found", ALWAYS follow up by saving it as a goal \
using save_goal (e.g. "Find and read the skills article shared by X team"). Never silently drop it.
- When using save_goal with dates, resolve relative dates to ISO format using today's date. \
"Tomorrow" → the day after today's date. "Next week" → 7 days from today.
- Prefer multiple small, specific entries over fewer large combined ones. \
Each entry should capture ONE concept or ONE plan.
"""

# --- Tool definitions as FunctionSchema objects ---

VOICE_TOOLS = ToolsSchema(standard_tools=[
    FunctionSchema(
        name="save_learning",
        description="Save something the user learned or a concept they understood today.",
        properties={
            "content": {"type": "string", "description": "What the user learned"},
            "topic": {"type": "string", "description": "Topic area (optional)"},
        },
        required=["content"],
    ),
    FunctionSchema(
        name="mark_article_read",
        description="Mark an article as read. Search by title keywords if exact title unknown.",
        properties={
            "title_query": {"type": "string", "description": "Article title or keywords to search for"},
        },
        required=["title_query"],
    ),
    FunctionSchema(
        name="save_goal",
        description="Save a goal or plan for tomorrow/future.",
        properties={
            "content": {"type": "string", "description": "The goal or plan"},
            "target_date": {"type": "string", "description": "Target date (ISO format, defaults to tomorrow)"},
        },
        required=["content"],
    ),
    FunctionSchema(
        name="save_progress",
        description="Save a progress update on an ongoing project or learning path.",
        properties={
            "content": {"type": "string", "description": "Progress update"},
        },
        required=["content"],
    ),
    FunctionSchema(
        name="get_last_checkin",
        description="Get the user's most recent check-in session summary and entries.",
        properties={},
        required=[],
    ),
    FunctionSchema(
        name="get_recent_goals",
        description="Get the user's recent goals to review progress.",
        properties={
            "limit": {"type": "integer", "description": "Number of goals to fetch (default 5)"},
        },
        required=[],
    ),
    FunctionSchema(
        name="search_knowledge",
        description="Search the user's knowledge base for information about a topic.",
        properties={
            "query": {"type": "string", "description": "Search query"},
        },
        required=["query"],
    ),
    FunctionSchema(
        name="save_memory",
        description="Save a memory about the user (preference, context, or instruction).",
        properties={
            "name": {"type": "string", "description": "Short identifier for this memory"},
            "content": {"type": "string", "description": "The memory content"},
            "type": {"type": "string", "description": "Memory type: preference, context, or instruction"},
            "importance": {"type": "integer", "description": "Importance 1-10 (default 5)"},
        },
        required=["name", "content", "type"],
    ),
    FunctionSchema(
        name="end_session",
        description="End the current check-in session. Call when the conversation is wrapping up.",
        properties={
            "mood": {"type": "string", "description": "User's mood (e.g. 'good', 'tired', 'motivated')"},
        },
        required=[],
    ),
])


# --- Context formatting ---

def _format_memories(memories: list[dict]) -> str:
    if not memories:
        return "No memories saved yet."
    lines = []
    for m in memories:
        lines.append(f"- **{m['name']}** ({m['type']}): {m['content']}")
    return "\n".join(lines)


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
            lines.append(f"  - [{e['entry_type']}] {e['content']}")
    return "\n".join(lines)


def _format_goals(goals: list[dict]) -> str:
    if not goals:
        return "No pending goals."
    lines = []
    for g in goals:
        date = g.get("metadata", {}).get("target_date", "")
        date_str = f" (target: {date})" if date else ""
        lines.append(f"- {g['content']}{date_str}")
    return "\n".join(lines)


def build_system_prompt(user_id: str) -> str:
    from datetime import date
    user_profile = wiki.read_page(user_id, "user/profile.md") or "New user — no profile yet."
    memories_text = wiki.read_memories(user_id) or "No memories saved yet."
    last_session = checkin_store.get_last_session(user_id)
    recent_goals = checkin_store.get_entries_by_type(user_id, "goal", limit=5)

    return VOICE_SYSTEM_PROMPT.format(
        user_profile=user_profile,
        user_memory=memories_text,
        last_checkin=_format_last_checkin(last_session),
        pending_goals=_format_goals(recent_goals),
        today_date=date.today().isoformat(),
    )


def _truncate(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def _generate_session_summary(entries: list[dict]) -> str:
    if not entries:
        return "Empty session."
    parts = []
    learnings = [e for e in entries if e["entry_type"] == "learning"]
    goals = [e for e in entries if e["entry_type"] == "goal"]
    articles = [e for e in entries if e["entry_type"] == "article_read"]
    progress = [e for e in entries if e["entry_type"] == "progress"]

    if learnings:
        parts.append(f"Learned {len(learnings)} thing(s): {', '.join(_truncate(e['content']) for e in learnings)}")
    if articles:
        parts.append(f"Read {len(articles)} article(s)")
    if progress:
        parts.append(f"Progress: {', '.join(_truncate(e['content']) for e in progress)}")
    if goals:
        parts.append(f"Goals ({len(goals)}): {', '.join(_truncate(e['content']) for e in goals)}")
    return ". ".join(parts) if parts else "Brief check-in."


# --- Tool handlers ---

def register_tool_handlers(llm: GoogleLLMService, user_id: str, session_id: int):
    """Register all voice tool function handlers on the LLM service."""

    async def on_save_learning(params: FunctionCallParams):
        entry = checkin_store.add_checkin_entry(
            session_id, user_id, "learning", params.arguments["content"],
            metadata={"topic": params.arguments.get("topic")},
        )
        await params.result_callback(json.dumps({"status": "saved", "id": entry["id"]}))

    async def on_mark_article_read(params: FunctionCallParams):
        articles = checkin_store.search_articles_by_title(params.arguments["title_query"], user_id)
        if not articles:
            await params.result_callback(json.dumps({"status": "not_found", "query": params.arguments["title_query"]}))
            return
        article = articles[0]
        checkin_store.mark_article_read(article["id"])
        checkin_store.add_checkin_entry(
            session_id, user_id, "article_read", f"Read: {article['title']}",
            metadata={"article_id": article["id"]},
        )
        await params.result_callback(json.dumps({"status": "marked_read", "article": article["title"]}))

    async def on_save_goal(params: FunctionCallParams):
        entry = checkin_store.add_checkin_entry(
            session_id, user_id, "goal", params.arguments["content"],
            metadata={"target_date": params.arguments.get("target_date")},
        )
        await params.result_callback(json.dumps({"status": "saved", "id": entry["id"]}))

    async def on_save_progress(params: FunctionCallParams):
        entry = checkin_store.add_checkin_entry(
            session_id, user_id, "progress", params.arguments["content"],
        )
        await params.result_callback(json.dumps({"status": "saved", "id": entry["id"]}))

    async def on_get_last_checkin(params: FunctionCallParams):
        session = checkin_store.get_last_session(user_id)
        if not session:
            await params.result_callback(json.dumps({"status": "no_sessions"}))
            return
        await params.result_callback(json.dumps({
            "started_at": session["started_at"],
            "summary": session.get("summary"),
            "entries": [{"type": e["entry_type"], "content": e["content"]} for e in session.get("entries", [])],
        }, default=str))

    async def on_get_recent_goals(params: FunctionCallParams):
        limit = params.arguments.get("limit", 5)
        goals = checkin_store.get_entries_by_type(user_id, "goal", limit=limit)
        await params.result_callback(json.dumps([
            {"content": g["content"], "date": g["created_at"], "metadata": g.get("metadata", {})}
            for g in goals
        ], default=str))

    async def on_search_knowledge(params: FunctionCallParams):
        results = wiki.grep_wiki(user_id, params.arguments["query"], max_results=5)
        await params.result_callback(json.dumps(results, default=str))

    async def on_save_memory(params: FunctionCallParams):
        current = wiki.read_memories(user_id) or "# Memories\n"
        mem_type = params.arguments.get("type", "context")
        new_entry = f"- **{params.arguments['name']}**: {params.arguments['content']}"
        # Append to the appropriate section or end of file
        updated = current.rstrip() + "\n" + new_entry + "\n"
        wiki.write_memories(user_id, updated)
        await params.result_callback(json.dumps({"status": "saved"}, default=str))

    async def on_end_session(params: FunctionCallParams):
        entries = checkin_store.get_session_entries(session_id)
        summary = _generate_session_summary(entries)
        checkin_store.end_checkin_session(session_id, summary, params.arguments.get("mood"))
        await params.result_callback(json.dumps({"status": "ended", "summary": summary}))

    llm.register_function("save_learning", on_save_learning)
    llm.register_function("mark_article_read", on_mark_article_read)
    llm.register_function("save_goal", on_save_goal)
    llm.register_function("save_progress", on_save_progress)
    llm.register_function("get_last_checkin", on_get_last_checkin)
    llm.register_function("get_recent_goals", on_get_recent_goals)
    llm.register_function("search_knowledge", on_search_knowledge)
    llm.register_function("save_memory", on_save_memory)
    llm.register_function("end_session", on_end_session)


# --- Pipeline creation ---

async def create_voice_pipeline(transport, user_id: str) -> tuple[PipelineTask, int]:
    """Create a Pipecat voice pipeline for a daily check-in session."""
    session = checkin_store.create_checkin_session(user_id)
    session_id = session["id"]

    system_prompt = build_system_prompt(user_id)

    stt = GroqSTTService(
        api_key=GROQ_API_KEY,
        settings=GroqSTTService.Settings(model="whisper-large-v3-turbo"),
    )

    tts = GroqTTSService(
        api_key=GROQ_API_KEY,
        settings=GroqTTSService.Settings(voice="diana"),
    )

    llm = GoogleLLMService(
        api_key=GEMINI_API_KEY,
        settings=GoogleLLMService.Settings(
            model="gemini-2.5-flash",
            temperature=0.7,
            system_instruction=system_prompt,
        ),
    )

    register_tool_handlers(llm, user_id, session_id)

    context = LLMContext(
        messages=[{"role": "user", "content": "Hello"}],
        tools=VOICE_TOOLS,
    )
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True),
    )

    return task, session_id
