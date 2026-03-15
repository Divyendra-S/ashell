import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kuro.agents.ingest import ingest
from kuro.agents.query import query
from kuro.cli import classify
from kuro.memory import store

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
    mode = classify(req.message)
    if mode == "query":
        response = query(req.message, user_id=req.user_id)
    else:
        response = ingest(req.message, user_id=req.user_id)
    return {"response": response, "mode": mode}


@app.post("/api/ingest")
def ingest_endpoint(req: IngestRequest):
    response = ingest(req.text, user_id=req.user_id)
    return {"response": response}


@app.post("/api/query")
def query_endpoint(req: QueryRequest):
    answer = query(req.question, user_id=req.user_id)
    return {"answer": answer}


@app.get("/api/entities")
def list_entities(search: str | None = None, user_id: str = "default"):
    if search:
        entities = store.search_entities(search, user_id=user_id)
    else:
        entities = store.supabase.table("entities").select("*").eq("user_id", user_id).execute().data
    return {"entities": entities}
