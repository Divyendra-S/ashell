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


class IngestRequest(BaseModel):
    text: str


class QueryRequest(BaseModel):
    question: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    mode = classify(req.message)
    if mode == "query":
        response = query(req.message)
    else:
        response = ingest(req.message)
    return {"response": response, "mode": mode}


@app.post("/api/ingest")
def ingest_endpoint(req: IngestRequest):
    response = ingest(req.text)
    return {"response": response}


@app.post("/api/query")
def query_endpoint(req: QueryRequest):
    answer = query(req.question)
    return {"answer": answer}


@app.get("/api/entities")
def list_entities(search: str | None = None):
    if search:
        entities = store.search_entities(search)
    else:
        entities = store.supabase.table("entities").select("*").execute().data
    return {"entities": entities}
