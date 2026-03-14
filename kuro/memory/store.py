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


def search_entities(query: str) -> list[dict]:
    result = supabase.table("entities").select("*").text_search(
        "search_vector", query, options={"config": "english"}
    ).execute()
    return result.data


def search_facts(query: str) -> list[dict]:
    result = supabase.table("facts").select("*").text_search(
        "search_vector", query, options={"config": "english"}
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
