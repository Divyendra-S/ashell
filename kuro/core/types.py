from pydantic import BaseModel


class Entity(BaseModel):
    id: int | None = None
    name: str
    entity_type: str
    summary: str | None = None


class Fact(BaseModel):
    id: int | None = None
    entity_id: int
    content: str
    source: str = "user"


class Relation(BaseModel):
    id: int | None = None
    source_id: int
    relation_type: str
    target_id: int
    context: str | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    mode: str
