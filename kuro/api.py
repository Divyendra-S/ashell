import asyncio
import logging
import re

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kuro.agents.ingest import ingest
from kuro.agents.query import query
from kuro.cli import classify, SLASH_CMD_PATTERN
from kuro.memory import store, checkin_store
from kuro.skills import load_skills, get_skill

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Kuro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    skill: str | None = None


class IngestRequest(BaseModel):
    text: str
    user_id: str = "default"


class QueryRequest(BaseModel):
    question: str
    user_id: str = "default"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    skill = req.skill
    message = req.message

    if skill:
        # Explicit skill from frontend — strip slash prefix if present
        slash = SLASH_CMD_PATTERN.match(message)
        if slash:
            message = slash.group(2).strip() or message
        skill_data = get_skill(skill)
        mode = skill_data.get("mode", "query") if skill_data else "query"
    else:
        mode, skill = classify(message)
        if skill:
            slash = SLASH_CMD_PATTERN.match(message)
            if slash:
                message = slash.group(2).strip() or message

    if mode == "query":
        response = query(message, user_id=req.user_id, skill=skill)
    else:
        # For ingest-url skill, pass instructions to ingest agent
        skill_instructions = None
        if skill:
            skill_data = get_skill(skill)
            if skill_data:
                skill_instructions = f"## Active Skill: /{skill_data['name']}\n{skill_data['body']}"
        response = ingest(message, user_id=req.user_id, skill_instructions=skill_instructions, skill_name=skill)

    return {"response": response, "mode": mode, "skill": skill}


@app.post("/api/ingest")
def ingest_endpoint(req: IngestRequest):
    response = ingest(req.text, user_id=req.user_id)
    return {"response": response}


@app.post("/api/query")
def query_endpoint(req: QueryRequest):
    answer = query(req.question, user_id=req.user_id)
    return {"answer": answer}


@app.get("/api/skills")
def list_skills_endpoint():
    skills = load_skills()
    return {
        "skills": [
            {"name": s["name"], "description": s["description"], "triggers": s["triggers"]}
            for s in skills.values()
        ]
    }


@app.get("/api/entities")
def list_entities(search: str | None = None, user_id: str = "default"):
    if search:
        entities = store.search_entities(search, user_id=user_id)
    else:
        entities = store.supabase.table("entities").select("*").eq("user_id", user_id).execute().data
    return {"entities": entities}


@app.get("/api/graph")
def graph_endpoint(user_id: str = "default"):
    return store.get_full_graph(user_id)


@app.get("/api/stats")
def stats_endpoint(user_id: str = "default"):
    return store.get_stats(user_id)


@app.get("/api/stats/growth")
def growth_endpoint(user_id: str = "default", days: int = 30):
    return {"data": store.get_growth_data(user_id, days)}


@app.get("/api/entity/{entity_id}")
def entity_detail_endpoint(entity_id: int, user_id: str = "default"):
    detail = store.get_entity_detail(entity_id, user_id)
    if not detail:
        return {"error": "Entity not found"}, 404
    return detail


@app.get("/api/articles")
def articles_endpoint(user_id: str = "default"):
    return {"articles": store.list_articles_enhanced(user_id)}


@app.get("/api/progress/timeline")
def timeline_endpoint(user_id: str = "default", days: int = 30):
    return {"timeline": checkin_store.get_timeline(user_id, days)}


@app.get("/api/progress/streak")
def streak_endpoint(user_id: str = "default"):
    return checkin_store.get_streak(user_id)


@app.patch("/api/goals/{entry_id}/complete")
def complete_goal_endpoint(entry_id: int, user_id: str = "default"):
    result = checkin_store.complete_goal(entry_id, user_id)
    if not result:
        return {"error": "Goal not found"}, 404
    return result


@app.get("/api/digest")
def digest_endpoint(user_id: str = "default"):
    return checkin_store.get_digest(user_id)


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

    # Extract user_id from the request data passed via the client
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
    """Handle WebRTC SDP offer from the client SDK."""
    body = await request.json()

    # Extract user_id from requestData before creating connection
    request_data = body.get("requestData") or body.get("request_data") or {}
    user_id = request_data.get("user_id", "default")

    webrtc_request = SmallWebRTCRequest(
        sdp=body["sdp"],
        type=body["type"],
        pc_id=body.get("pc_id"),
        restart_pc=body.get("restart_pc"),
        request_data=request_data,
    )

    # Wrap the callback to inject user_id onto the connection
    async def connection_callback(connection):
        connection._kuro_user_id = user_id
        await _on_webrtc_connection(connection)

    answer = await _webrtc_handler.handle_web_request(webrtc_request, connection_callback)
    return answer


@app.patch("/api/offer")
async def webrtc_ice_candidate(request: Request):
    """Handle WebRTC ICE candidates from the client SDK."""
    body = await request.json()
    patch_request = SmallWebRTCPatchRequest(
        pc_id=body["pc_id"],
        candidates=[IceCandidate(**c) for c in body.get("candidates", [])],
    )
    await _webrtc_handler.handle_patch_request(patch_request)
    return {"status": "ok"}


@app.get("/api/voice/sessions")
def voice_sessions(user_id: str = "default", limit: int = 7):
    """Get recent check-in sessions for a user."""
    sessions = checkin_store.get_recent_sessions(user_id, limit=limit)
    return {"sessions": sessions}
