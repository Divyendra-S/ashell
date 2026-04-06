import asyncio
import logging
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from kuro.agents.unified import chat, chat_streaming
from kuro.cli import detect_skill, SLASH_CMD_PATTERN
from kuro.memory import store, wiki, checkin_store
from kuro.skills import load_skills, get_skill

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Kuro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "chrome-extension://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: str  # "user" or "kuro"
    text: str


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    skill: str | None = None
    history: list[HistoryMessage] = []


class IngestArticleRequest(BaseModel):
    url: str
    title: str
    content: str
    topic: str = "general"
    user_id: str = "default"
    auto_extract: bool = False


class NoteRequest(BaseModel):
    content: str
    user_id: str = "default"
    concept_slug: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Chat ---


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    skill = req.skill
    message = req.message

    if skill:
        slash = SLASH_CMD_PATTERN.match(message)
        if slash:
            message = slash.group(2).strip() or message
    else:
        skill = detect_skill(message)
        if skill:
            slash = SLASH_CMD_PATTERN.match(message)
            if slash:
                message = slash.group(2).strip() or message

    history = [
        {"role": "user" if m.role == "user" else "model", "parts": [{"text": m.text}]}
        for m in req.history if m.text.strip()
    ]
    response = chat(message, history=history or None, user_id=req.user_id, skill=skill)
    return {"response": response, "skill": skill}


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    import json as _json

    skill = req.skill
    message = req.message

    if skill:
        slash = SLASH_CMD_PATTERN.match(message)
        if slash:
            message = slash.group(2).strip() or message
    else:
        skill = detect_skill(message)
        if skill:
            slash = SLASH_CMD_PATTERN.match(message)
            if slash:
                message = slash.group(2).strip() or message

    history = [
        {"role": "user" if m.role == "user" else "model", "parts": [{"text": m.text}]}
        for m in req.history if m.text.strip()
    ]

    def generate():
        try:
            stream = chat_streaming(message, history=history or None, user_id=req.user_id, skill=skill)
            for event_type, data in stream:
                if event_type == "step":
                    yield f"event: step\ndata: {_json.dumps(data)}\n\n"
                elif event_type == "delta":
                    yield f"event: delta\ndata: {_json.dumps({'text': data})}\n\n"

            yield f"event: done\ndata: {_json.dumps({'skill': skill})}\n\n"
        except Exception as e:
            logging.getLogger("kuro.api").error(f"Stream error: {e}")
            yield f"event: error\ndata: {_json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Skills ---


@app.get("/api/skills")
def list_skills_endpoint():
    skills = load_skills()
    return {
        "skills": [
            {"name": s["name"], "description": s["description"], "triggers": s["triggers"]}
            for s in skills.values()
        ]
    }


# --- Knowledge Graph (wiki-based) ---


@app.get("/api/graph")
def graph_endpoint(user_id: str = "default"):
    return wiki.build_graph(user_id)


@app.get("/api/concept/{slug}")
def concept_detail_endpoint(slug: str, user_id: str = "default"):
    detail = wiki.get_concept_detail(user_id, slug)
    if not detail:
        return {"error": "Concept not found"}, 404
    return detail


# --- Stats (wiki + articles) ---


@app.get("/api/stats")
def stats_endpoint(user_id: str = "default"):
    wiki_stats = wiki.get_wiki_stats(user_id)
    article_count = 0
    new_articles_7d = 0
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        article_count = len(store.list_articles(user_id=user_id))
        articles = store.supabase.table("articles").select("id").eq("user_id", user_id).gte("created_at", cutoff).execute().data
        new_articles_7d = len(articles)
    except Exception:
        pass
    return {
        "concept_count": wiki_stats["concept_count"],
        "backlink_count": wiki_stats["backlink_count"],
        "article_count": article_count,
        "new_concepts_7d": wiki_stats["new_concepts_7d"],
        "new_articles_7d": new_articles_7d,
        "health_score": wiki_stats["health_score"],
    }


@app.get("/api/stats/growth")
def growth_endpoint(user_id: str = "default", days: int = 30):
    try:
        wiki_growth = wiki.get_growth_data(user_id, days)
    except Exception:
        wiki_growth = []
    # Merge article growth from Supabase
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        articles = store.supabase.table("articles").select("created_at").eq("user_id", user_id).gte("created_at", cutoff).execute().data
        for a in articles:
            day = a["created_at"][:10]
            for entry in wiki_growth:
                if entry["date"] == day:
                    entry["articles"] = entry.get("articles", 0) + 1
                    break
    except Exception:
        pass
    # Ensure articles key exists on all entries
    for entry in wiki_growth:
        entry.setdefault("articles", 0)
    return {"data": wiki_growth}


# --- Articles ---


@app.get("/api/articles")
def articles_endpoint(user_id: str = "default"):
    try:
        return {"articles": store.list_articles_enhanced(user_id)}
    except Exception:
        return {"articles": []}


@app.get("/api/check-article")
def check_article(url: str, user_id: str = "default"):
    existing = store.get_article_by_url(url)
    if existing and existing.get("user_id") == user_id:
        return {"saved": True, "article_id": existing["id"]}
    return {"saved": False}


@app.post("/api/ingest-article")
def ingest_article(req: IngestArticleRequest):
    from kuro.memory import files

    # Check for duplicate (same URL + same user)
    existing = store.get_article_by_url(req.url)
    if existing and existing.get("user_id") == req.user_id:
        return {"article_id": existing["id"], "file_path": existing.get("file_path", ""), "duplicate": True}

    # 1. Save article content to wiki_pages
    file_path = files.save_article(req.title, req.content, req.topic, req.user_id)

    # 2. Generate retrieval-optimized summary via LLM
    from kuro.core.llm import generate_article_summary
    summary = generate_article_summary(req.title, req.content)

    # 3. Save metadata + summary to articles table
    row = store.insert_article(req.url, req.title, file_path, user_id=req.user_id, summary=summary)

    # 3. Optionally auto-extract concepts via agent
    if req.auto_extract:
        try:
            chat(
                f"I just saved this article: '{req.title}'. "
                f"Read it from '{file_path}' and extract the key concepts into wiki pages. "
                f"For each concept: write a clear summary that explains what it is and WHY it matters, "
                f"include concrete examples and practical details from the article (not just definitions), "
                f"add specific gotchas or best practices mentioned, "
                f"and connect concepts with [[backlinks]]. "
                f"Make each concept page genuinely useful as a reference — someone reading it should "
                f"learn the key insights without needing to re-read the original article.",
                user_id=req.user_id,
            )
        except Exception as e:
            logging.getLogger("kuro.api").warning(f"Auto-extract failed: {e}")

    return {"article_id": row["id"], "file_path": file_path, "duplicate": False}


# --- Progress (unchanged, from checkin_store) ---


@app.get("/api/progress/timeline")
def timeline_endpoint(user_id: str = "default", days: int = 30):
    try:
        return {"timeline": checkin_store.get_timeline(user_id, days)}
    except Exception:
        return {"timeline": []}


@app.get("/api/progress/streak")
def streak_endpoint(user_id: str = "default"):
    try:
        return checkin_store.get_streak(user_id)
    except Exception:
        return {"current": 0, "longest": 0, "total_active_days": 0}


@app.patch("/api/goals/{entry_id}/complete")
def complete_goal_endpoint(entry_id: int, user_id: str = "default"):
    try:
        result = checkin_store.complete_goal(entry_id, user_id)
        if not result:
            return {"error": "Goal not found"}, 404
        return result
    except Exception:
        return {"error": "Database unavailable"}, 503


@app.get("/api/digest")
def digest_endpoint(user_id: str = "default"):
    try:
        return checkin_store.get_digest(user_id)
    except Exception:
        return {"streak": {"current": 0, "longest": 0, "total_active_days": 0}, "recent_concepts": [], "recent_articles": [], "pending_goals": [], "study_suggestion": None, "kb_suggestions": []}


# --- Notes (wiki-based, append to concept page) ---


@app.post("/api/notes")
def create_note(req: NoteRequest):
    if not req.concept_slug:
        return {"error": "concept_slug is required"}, 400
    content = wiki.read_page(req.user_id, f"concepts/{req.concept_slug}.md")
    if content is None:
        return {"error": f"Concept '{req.concept_slug}' not found"}, 404

    # Append to ## Notes section or create it
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    note_line = f"- {req.content} [{timestamp}]"

    if "## Notes" in content:
        content = content.rstrip() + "\n" + note_line + "\n"
    else:
        content = content.rstrip() + "\n\n## Notes\n" + note_line + "\n"

    wiki.write_page(req.user_id, f"concepts/{req.concept_slug}.md", content)
    return {"status": "saved", "concept_slug": req.concept_slug}


# --- Voice Agent (Pipecat SmallWebRTC) ---

from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequestHandler,
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    IceCandidate,
)

_webrtc_handler = SmallWebRTCRequestHandler()


async def _on_webrtc_connection(connection):
    """Called when a new WebRTC peer connects. Sets up the voice pipeline."""
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
    from pipecat.transports.base_transport import TransportParams
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.runner import PipelineRunner
    from kuro.agents.voice import create_voice_pipeline, _generate_session_summary

    user_id = getattr(connection, "_kuro_user_id", "default")

    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    task, session_id = await create_voice_pipeline(transport, user_id)

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        try:
            entries = checkin_store.get_session_entries(session_id)
            if entries:
                summary = _generate_session_summary(entries)
                checkin_store.end_checkin_session(session_id, summary)
        except Exception as e:
            logging.getLogger("kuro.voice").warning(f"Failed to close session on disconnect: {e}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    asyncio.create_task(runner.run(task))


@app.post("/api/offer")
async def webrtc_offer(request: Request):
    body = await request.json()
    request_data = body.get("requestData") or body.get("request_data") or {}
    user_id = request_data.get("user_id", "default")

    webrtc_request = SmallWebRTCRequest(
        sdp=body["sdp"],
        type=body["type"],
        pc_id=body.get("pc_id"),
        restart_pc=body.get("restart_pc"),
        request_data=request_data,
    )

    async def connection_callback(connection):
        connection._kuro_user_id = user_id
        await _on_webrtc_connection(connection)

    answer = await _webrtc_handler.handle_web_request(webrtc_request, connection_callback)
    return answer


@app.patch("/api/offer")
async def webrtc_ice_candidate(request: Request):
    body = await request.json()
    patch_request = SmallWebRTCPatchRequest(
        pc_id=body["pc_id"],
        candidates=[IceCandidate(**c) for c in body.get("candidates", [])],
    )
    await _webrtc_handler.handle_patch_request(patch_request)
    return {"status": "ok"}


@app.get("/api/voice/sessions")
def voice_sessions(user_id: str = "default", limit: int = 7):
    sessions = checkin_store.get_recent_sessions(user_id, limit=limit)
    return {"sessions": sessions}
