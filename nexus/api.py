import json
import logging
import re
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nexus.agents.unified import chat, chat_streaming, detect_skill, SLASH_CMD_PATTERN
from nexus.graph import wiki, articles, memories
from nexus.graph.progress import (
    get_timeline, get_streak, complete_goal, get_digest,
)
from nexus.skills import load_skills

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "chrome-extension://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: str
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
    try:
        response = chat(message, history=history or None, user_id=req.user_id, skill=skill)
        return {"response": response, "skill": skill}
    except Exception as e:
        logging.getLogger("nexus.api").exception(f"Chat failed: {e}")
        raise


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
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
                    yield f"event: step\ndata: {json.dumps(data)}\n\n"
                elif event_type == "delta":
                    yield f"event: delta\ndata: {json.dumps({'text': data})}\n\n"
            yield f"event: done\ndata: {json.dumps({'skill': skill})}\n\n"
        except Exception as e:
            logging.getLogger("nexus.api").error(f"Stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

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


# --- Knowledge Graph ---


@app.get("/api/graph")
def graph_endpoint(user_id: str = "default"):
    return wiki.build_graph(user_id)


@app.get("/api/concept/{slug}")
def concept_detail_endpoint(slug: str, user_id: str = "default"):
    detail = wiki.get_concept_detail(user_id, slug)
    if not detail:
        return {"error": "Concept not found"}, 404
    return detail


# --- Stats ---


@app.get("/api/stats")
def stats_endpoint(user_id: str = "default"):
    wiki_stats = wiki.get_wiki_stats(user_id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    article_count = articles.count_articles(user_id)
    new_articles_7d = articles.count_new_articles(user_id, cutoff)
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

    # Merge article growth from Neo4j
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        from nexus.graph.driver import run_query
        article_rows = run_query(
            "MATCH (a:Article {user_id: $uid}) WHERE a.created_at >= $cutoff RETURN a.created_at AS created_at",
            uid=user_id, cutoff=cutoff,
        )
        for a in article_rows:
            day = a["created_at"][:10]
            for entry in wiki_growth:
                if entry["date"] == day:
                    entry["articles"] = entry.get("articles", 0) + 1
                    break
    except Exception:
        pass

    for entry in wiki_growth:
        entry.setdefault("articles", 0)
    return {"data": wiki_growth}


# --- Articles ---


@app.get("/api/articles")
def articles_endpoint(user_id: str = "default"):
    try:
        return {"articles": articles.list_articles_enhanced(user_id)}
    except Exception:
        return {"articles": []}


@app.get("/api/check-article")
def check_article(url: str, user_id: str = "default"):
    existing = articles.get_article_by_url(url)
    if existing and existing.get("user_id") == user_id:
        return {"saved": True, "article_id": existing["id"]}
    return {"saved": False}


@app.post("/api/ingest-article")
def ingest_article(req: IngestArticleRequest):
    existing = articles.get_article_by_url(req.url)
    if existing and existing.get("user_id") == req.user_id:
        return {"article_id": existing["id"], "file_path": existing.get("file_path", ""), "duplicate": True}

    file_path = f"articles/{req.topic}/{req.title[:50]}.md"

    from nexus.core.llm import generate_article_summary
    summary = generate_article_summary(req.title, req.content)

    row = articles.insert_article(req.url, req.title, file_path, user_id=req.user_id, summary=summary)
    articles.save_article_content(row["id"], req.content)

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
            logging.getLogger("nexus.api").warning(f"Auto-extract failed: {e}")

    return {"article_id": row["id"], "file_path": file_path, "duplicate": False}


# --- Progress ---


@app.get("/api/progress/timeline")
def timeline_endpoint(user_id: str = "default", days: int = 30):
    try:
        return {"timeline": get_timeline(user_id, days)}
    except Exception:
        return {"timeline": []}


@app.get("/api/progress/streak")
def streak_endpoint(user_id: str = "default"):
    try:
        return get_streak(user_id)
    except Exception:
        return {"current": 0, "longest": 0, "total_active_days": 0}


@app.patch("/api/goals/{entry_id}/complete")
def complete_goal_endpoint(entry_id: str, user_id: str = "default"):
    try:
        result = complete_goal(entry_id, user_id)
        if not result:
            return {"error": "Goal not found"}, 404
        return result
    except Exception:
        return {"error": "Database unavailable"}, 503


@app.get("/api/digest")
def digest_endpoint(user_id: str = "default"):
    try:
        return get_digest(user_id)
    except Exception:
        return {
            "streak": {"current": 0, "longest": 0, "total_active_days": 0},
            "recent_concepts": [], "recent_articles": [],
            "pending_goals": [], "study_suggestion": None, "kb_suggestions": [],
        }


# --- Notes ---


@app.post("/api/notes")
def create_note(req: NoteRequest):
    if not req.concept_slug:
        return {"error": "concept_slug is required"}, 400
    content = wiki.read_page(req.user_id, f"concepts/{req.concept_slug}.md")
    if content is None:
        return {"error": f"Concept '{req.concept_slug}' not found"}, 404

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    note_line = f"- {req.content} [{timestamp}]"

    if "## Notes" in content:
        content = content.rstrip() + "\n" + note_line + "\n"
    else:
        content = content.rstrip() + "\n\n## Notes\n" + note_line + "\n"

    wiki.write_page(req.user_id, f"concepts/{req.concept_slug}.md", content)
    return {"status": "saved", "concept_slug": req.concept_slug}
