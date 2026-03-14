import logging
from datetime import datetime, timezone

from supabase import create_client

from kuro.config import SUPABASE_URL, SUPABASE_KEY

log = logging.getLogger("kuro.store")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upsert_entity(name: str, entity_type: str, summary: str | None = None) -> dict:
    existing = supabase.table("entities").select("*").eq("name", name).execute()
    if existing.data:
        updated = supabase.table("entities").update({
            "entity_type": entity_type,
            "summary": summary,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("name", name).execute()
        return updated.data[0]
    else:
        inserted = supabase.table("entities").insert({
            "name": name,
            "entity_type": entity_type,
            "summary": summary,
        }).execute()
        return inserted.data[0]


def insert_fact(entity_id: int, content: str, source: str = "user") -> dict:
    result = supabase.table("facts").insert({
        "entity_id": entity_id,
        "content": content,
        "source": source,
    }).execute()
    return result.data[0]


def insert_relation(source_id: int, relation_type: str, target_id: int, context: str | None = None) -> dict:
    result = supabase.table("relations").insert({
        "source_id": source_id,
        "relation_type": relation_type,
        "target_id": target_id,
        "context": context,
    }).execute()
    return result.data[0]


def _to_tsquery(query: str) -> str:
    """Convert natural language query to tsquery format (join words with &)."""
    words = query.strip().split()
    return " & ".join(words)


def search_entities(query: str) -> list[dict]:
    result = supabase.table("entities").select("*").text_search(
        "search_vector", _to_tsquery(query), options={"config": "english", "type": "plain"}
    ).execute()
    return result.data


def search_facts(query: str) -> list[dict]:
    result = supabase.table("facts").select("*").text_search(
        "search_vector", _to_tsquery(query), options={"config": "english", "type": "plain"}
    ).execute()
    return result.data


def get_entity_by_name(name: str) -> dict | None:
    result = supabase.table("entities").select("*").eq("name", name).execute()
    return result.data[0] if result.data else None


def get_facts_for_entity(entity_id: int) -> list[dict]:
    result = supabase.table("facts").select("*").eq("entity_id", entity_id).execute()
    return result.data


def get_relations_for_entity(entity_id: int) -> list[dict]:
    r1 = supabase.table("relations").select("*").eq("source_id", entity_id).execute()
    r2 = supabase.table("relations").select("*").eq("target_id", entity_id).execute()
    seen = {r["id"] for r in r1.data}
    combined = r1.data + [r for r in r2.data if r["id"] not in seen]
    return combined


def insert_article(url: str, title: str, file_path: str) -> dict:
    return supabase.table("articles").insert({
        "url": url, "title": title, "file_path": file_path
    }).execute().data[0]


def get_article_by_url(url: str) -> dict | None:
    res = supabase.table("articles").select("*").eq("url", url).execute()
    return res.data[0] if res.data else None


def search_knowledge_unified(query: str) -> dict:
    """Unified FTS across entities, facts, and article chunks."""
    result = supabase.rpc("search_knowledge", {"search_query": query}).execute()
    return result.data


def insert_article_chunks(article_id: int, chunks: list[str]) -> list[dict]:
    rows = [{"article_id": article_id, "chunk_index": i, "content": c}
            for i, c in enumerate(chunks)]
    return supabase.table("article_chunks").insert(rows).execute().data


def list_articles() -> list[dict]:
    result = supabase.table("articles").select("id, title, url, file_path").order("created_at", desc=True).execute()
    return result.data


def traverse(entity_id: int, depth: int = 1) -> dict:
    """BFS through relations up to `depth` hops."""
    visited_ids, edges, queue = set(), [], [entity_id]
    for _ in range(depth):
        next_queue = []
        for eid in queue:
            if eid in visited_ids:
                continue
            visited_ids.add(eid)
            rels = get_relations_for_entity(eid)
            for r in rels:
                edges.append(r)
                other_id = r["target_id"] if r["source_id"] == eid else r["source_id"]
                if other_id not in visited_ids:
                    next_queue.append(other_id)
        queue = next_queue
    entities = []
    for eid in visited_ids:
        row = supabase.table("entities").select("id, name, entity_type, summary").eq("id", eid).execute()
        if row.data:
            entities.append(row.data[0])
    return {"entities": entities, "relations": edges}


def get_relations_for_entity_enriched(entity_id: int) -> list[dict]:
    """Relations with entity names resolved."""
    relations = get_relations_for_entity(entity_id)
    entity_ids = set()
    for r in relations:
        entity_ids.add(r["source_id"])
        entity_ids.add(r["target_id"])
    names = {}
    for eid in entity_ids:
        row = supabase.table("entities").select("id, name").eq("id", eid).execute()
        if row.data:
            names[row.data[0]["id"]] = row.data[0]["name"]
    for r in relations:
        r["source_name"] = names.get(r["source_id"], "unknown")
        r["target_name"] = names.get(r["target_id"], "unknown")
    return relations
