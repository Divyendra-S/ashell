import logging
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kuro.agents.ingest import ingest
from kuro.agents.query import query
from kuro.cli import classify, SLASH_CMD_PATTERN
from kuro.memory import store
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
        response = ingest(message, user_id=req.user_id, skill_instructions=skill_instructions)

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
