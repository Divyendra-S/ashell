import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client

from kuro.config import SUPABASE_URL, SUPABASE_KEY

_PROFILES_DIR = Path(__file__).parent.parent.parent / "data" / "user_profiles"

log = logging.getLogger("kuro.store")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upsert_entity(name: str, entity_type: str, summary: str | None = None, user_id: str = "default") -> dict:
    # Case-insensitive lookup to prevent near-duplicates
    existing = supabase.table("entities").select("*").ilike("name", name).eq("user_id", user_id).execute()
    if existing.data:
        row = existing.data[0]
        updated = supabase.table("entities").update({
            "entity_type": entity_type,
            "summary": summary,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row["id"]).execute()
        return updated.data[0]
    else:
        inserted = supabase.table("entities").insert({
            "name": name,
            "entity_type": entity_type,
            "summary": summary,
            "user_id": user_id,
        }).execute()
        return inserted.data[0]


def insert_fact(entity_id: int, content: str, source: str = "user", user_id: str = "default") -> dict:
    result = supabase.table("facts").insert({
        "entity_id": entity_id,
        "content": content,
        "source": source,
        "user_id": user_id,
    }).execute()
    return result.data[0]


def insert_relation(source_id: int, relation_type: str, target_id: int, context: str | None = None, user_id: str = "default") -> dict:
    result = supabase.table("relations").insert({
        "source_id": source_id,
        "relation_type": relation_type,
        "target_id": target_id,
        "context": context,
        "user_id": user_id,
    }).execute()
    return result.data[0]


def _to_tsquery(query: str) -> str:
    """Convert natural language query to tsquery format (join words with &)."""
    words = query.strip().split()
    return " & ".join(words)


def search_entities(query: str, user_id: str = "default") -> list[dict]:
    result = supabase.table("entities").select("*").eq("user_id", user_id).text_search(
        "search_vector", _to_tsquery(query), options={"config": "english", "type": "plain"}
    ).execute()
    return result.data


def search_facts(query: str, user_id: str = "default") -> list[dict]:
    result = supabase.table("facts").select("*").eq("user_id", user_id).text_search(
        "search_vector", _to_tsquery(query), options={"config": "english", "type": "plain"}
    ).execute()
    return result.data


def get_entity_by_name(name: str, user_id: str = "default") -> dict | None:
    result = supabase.table("entities").select("*").eq("name", name).eq("user_id", user_id).execute()
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


def insert_article(url: str, title: str, file_path: str, user_id: str = "default") -> dict:
    return supabase.table("articles").insert({
        "url": url, "title": title, "file_path": file_path, "user_id": user_id,
    }).execute().data[0]


def get_article_by_url(url: str) -> dict | None:
    res = supabase.table("articles").select("*").eq("url", url).execute()
    return res.data[0] if res.data else None


def search_knowledge_unified(query: str, user_id: str = "default") -> dict:
    """Unified FTS across entities, facts, and article chunks."""
    result = supabase.rpc("search_knowledge", {"search_query": query, "p_user_id": user_id}).execute()
    return result.data


def insert_article_chunks(article_id: int, chunks: list[str], user_id: str = "default") -> list[dict]:
    rows = [{"article_id": article_id, "chunk_index": i, "content": c, "user_id": user_id}
            for i, c in enumerate(chunks)]
    return supabase.table("article_chunks").insert(rows).execute().data


def list_articles(user_id: str = "default") -> list[dict]:
    result = supabase.table("articles").select("id, title, url, file_path").eq("user_id", user_id).order("created_at", desc=True).execute()
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


def semantic_search_chunks(query_embedding: list[float], threshold: float = 0.5, limit: int = 10, user_id: str = "default") -> list[dict]:
    result = supabase.rpc("match_chunks", {
        "query_embedding": str(query_embedding),
        "match_threshold": threshold,
        "match_count": limit,
        "p_user_id": user_id,
    }).execute()
    return result.data


def update_chunk_embedding(chunk_id: int, embedding: list[float]) -> None:
    supabase.table("article_chunks").update({"embedding": str(embedding)}).eq("id", chunk_id).execute()


def get_chunks_without_embeddings() -> list[dict]:
    result = supabase.table("article_chunks").select("id, content").is_("embedding", "null").execute()
    return result.data


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


# --- User Memory CRUD ---

# Consolidation thresholds
_MERGE_THRESHOLD = 0.85    # Auto-merge: memories are about the same thing
_CONFLICT_THRESHOLD = 0.70  # Conflict zone: same topic, possibly contradicting


def _embed_and_find_similar(
    user_id: str, content: str, exclude_name: str | None = None, threshold: float = _CONFLICT_THRESHOLD,
) -> tuple[list[dict], list[float]]:
    """Embed memory content and find semantically similar existing memories."""
    from kuro.core.llm import embed_text
    embedding = embed_text(content)
    try:
        similar = supabase.rpc("match_memories", {
            "query_embedding": str(embedding),
            "match_threshold": threshold,
            "match_count": 5,
            "p_user_id": user_id,
        }).execute().data
    except Exception:
        log.warning("match_memories RPC failed, skipping consolidation")
        similar = []
    if exclude_name:
        similar = [m for m in similar if m["name"] != exclude_name]
    return similar, embedding


def upsert_user_memory(
    user_id: str,
    name: str,
    memory_type: str,
    content: str,
    importance: int = 5,
    source: str = "agent",
    expires_at: str | None = None,
    auto_consolidate: bool = True,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    existing = supabase.table("user_memories").select("*").eq("user_id", user_id).eq("name", name).execute()
    payload = {
        "type": memory_type,
        "content": content,
        "importance": max(1, min(10, importance)),
        "source": source,
        "updated_at": now,
    }
    if expires_at is not None:
        payload["expires_at"] = expires_at

    # Auto-consolidation: embed content, find similar memories, merge/replace
    consolidated_from = []
    embedding = None
    if auto_consolidate:
        try:
            similar, embedding = _embed_and_find_similar(user_id, content, exclude_name=name)
            for mem in similar:
                sim = mem.get("similarity", 0)
                if sim >= _MERGE_THRESHOLD:
                    # Very similar → auto-merge (delete old, new content wins)
                    log.info(f"Auto-merging memory '{mem['name']}' (similarity={sim:.2f}) into '{name}'")
                    consolidated_from.append({"name": mem["name"], "action": "merged", "similarity": sim})
                    # Keep higher importance
                    payload["importance"] = max(payload["importance"], mem.get("importance", 5))
                    delete_user_memory(user_id, mem["name"])
                elif sim >= _CONFLICT_THRESHOLD and mem.get("type") == memory_type:
                    # Same type, moderately similar → conflict, newer wins
                    log.info(f"Resolving conflict: replacing '{mem['name']}' (similarity={sim:.2f}) with '{name}'")
                    consolidated_from.append({"name": mem["name"], "action": "replaced", "similarity": sim})
                    delete_user_memory(user_id, mem["name"])
        except Exception as e:
            log.warning(f"Consolidation failed, saving without: {e}")

    if embedding is not None:
        payload["embedding"] = str(embedding)

    if existing.data:
        updated = supabase.table("user_memories").update(payload).eq("user_id", user_id).eq("name", name).execute()
        result = updated.data[0]
    else:
        payload.update({"user_id": user_id, "name": name})
        inserted = supabase.table("user_memories").insert(payload).execute()
        result = inserted.data[0]

    if consolidated_from:
        result["_consolidated_from"] = consolidated_from
    return result


def get_user_memories(user_id: str) -> list[dict]:
    result = supabase.table("user_memories").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
    return result.data


def _recency_weight(updated_at: str) -> float:
    """Compute a decay weight based on how old the memory is."""
    try:
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 0.3
    age_days = (datetime.now(timezone.utc) - ts).total_seconds() / 86400
    if age_days < 7:
        return 1.0
    if age_days < 30:
        return 0.8
    if age_days < 90:
        return 0.5
    return 0.3


def get_top_memories(user_id: str, limit: int = 10) -> list[dict]:
    """Get the most relevant memories using importance × recency scoring."""
    all_mems = get_user_memories(user_id)
    now = datetime.now(timezone.utc)
    # Filter out expired memories
    active = []
    for m in all_mems:
        if m.get("expires_at"):
            try:
                exp = datetime.fromisoformat(m["expires_at"].replace("Z", "+00:00"))
                if exp < now:
                    continue
            except (ValueError, AttributeError):
                pass
        active.append(m)
    # Score and rank
    for m in active:
        importance = m.get("importance", 5)
        recency = _recency_weight(m.get("updated_at", ""))
        m["_score"] = importance * recency
    active.sort(key=lambda m: m["_score"], reverse=True)
    result = active[:limit]
    # Clean up internal score field
    for m in result:
        m.pop("_score", None)
    return result


def search_user_memories(user_id: str, query: str) -> list[dict]:
    """Search user memories by content (case-insensitive substring match)."""
    all_mems = get_user_memories(user_id)
    q = query.lower()
    return [m for m in all_mems if q in m.get("content", "").lower() or q in m.get("name", "").lower()]


def touch_memory(user_id: str, name: str) -> None:
    """Update access tracking for a memory."""
    mem = get_user_memory(user_id, name)
    if mem:
        count = (mem.get("access_count") or 0) + 1
        supabase.table("user_memories").update({
            "last_accessed_at": datetime.now(timezone.utc).isoformat(),
            "access_count": count,
        }).eq("user_id", user_id).eq("name", name).execute()


def get_user_memory(user_id: str, name: str) -> dict | None:
    result = supabase.table("user_memories").select("*").eq("user_id", user_id).eq("name", name).execute()
    return result.data[0] if result.data else None


def delete_user_memory(user_id: str, name: str) -> bool:
    result = supabase.table("user_memories").delete().eq("user_id", user_id).eq("name", name).execute()
    return len(result.data) > 0


# --- User Profile (markdown, progressive disclosure) ---

def read_user_profile(user_id: str) -> str:
    """Read the user's markdown profile. Returns empty string if none exists."""
    path = _PROFILES_DIR / user_id / "profile.md"
    if not path.exists():
        return ""
    return path.read_text()


def update_user_profile(user_id: str, content: str) -> str:
    """Write/overwrite the user's markdown profile."""
    d = _PROFILES_DIR / user_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / "profile.md"
    path.write_text(content)
    return str(path)


# --- Dashboard / Graph / Stats ---

def get_full_graph(user_id: str = "default") -> dict:
    """Return all entities and relations for a user, deduped by case-insensitive name."""
    raw_entities = supabase.table("entities").select("id, name, entity_type, summary").eq("user_id", user_id).execute().data

    # Get fact counts per entity
    for e in raw_entities:
        facts = supabase.table("facts").select("id").eq("entity_id", e["id"]).execute().data
        e["fact_count"] = len(facts)

    # Deduplicate by case-insensitive name — keep the one with most facts
    canonical = {}  # lower_name -> entity dict
    id_remap = {}   # old_id -> canonical_id
    for e in raw_entities:
        key = e["name"].lower()
        if key not in canonical or e["fact_count"] > canonical[key]["fact_count"]:
            canonical[key] = e
        id_remap[e["id"]] = None  # will fill after

    # Build final remap
    for e in raw_entities:
        key = e["name"].lower()
        id_remap[e["id"]] = canonical[key]["id"]
        # Merge fact counts into canonical
        if e["id"] != canonical[key]["id"]:
            canonical[key]["fact_count"] += e["fact_count"]

    entities = list(canonical.values())
    entity_ids = {e["id"] for e in entities}

    # Get all relations with IDs remapped and names resolved
    relations = []
    seen_rels = set()
    all_rels = supabase.table("relations").select("*").eq("user_id", user_id).execute().data
    name_map = {e["id"]: e["name"] for e in entities}

    for r in all_rels:
        src = id_remap.get(r["source_id"], r["source_id"])
        tgt = id_remap.get(r["target_id"], r["target_id"])
        if src not in entity_ids or tgt not in entity_ids or src == tgt:
            continue
        # Deduplicate relations after remapping
        rel_key = (src, tgt, r["relation_type"])
        if rel_key in seen_rels:
            continue
        seen_rels.add(rel_key)
        r["source_id"] = src
        r["target_id"] = tgt
        r["source_name"] = name_map.get(src, "unknown")
        r["target_name"] = name_map.get(tgt, "unknown")
        relations.append(r)

    return {"entities": entities, "relations": relations}


def get_stats(user_id: str = "default") -> dict:
    """Return KB stats with 7-day deltas."""
    now_iso = datetime.now(timezone.utc).isoformat()

    entity_count = len(supabase.table("entities").select("id").eq("user_id", user_id).execute().data)
    fact_count = len(supabase.table("facts").select("id").eq("user_id", user_id).execute().data)
    article_count = len(supabase.table("articles").select("id").eq("user_id", user_id).execute().data)
    relation_count = len(supabase.table("relations").select("id").eq("user_id", user_id).execute().data)

    # 7-day deltas
    from datetime import timedelta
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    new_entities = len(supabase.table("entities").select("id").eq("user_id", user_id).gte("created_at", week_ago).execute().data)
    new_facts = len(supabase.table("facts").select("id").eq("user_id", user_id).gte("created_at", week_ago).execute().data)
    new_articles = len(supabase.table("articles").select("id").eq("user_id", user_id).gte("created_at", week_ago).execute().data)

    # KB health score (simplified from kb_health_report)
    orphan_count = 0
    entities_data = supabase.table("entities").select("id").eq("user_id", user_id).execute().data
    for e in entities_data:
        fc = len(supabase.table("facts").select("id").eq("entity_id", e["id"]).execute().data)
        if fc == 0:
            orphan_count += 1

    health_score = 100
    if entity_count > 0:
        orphan_pct = orphan_count / entity_count
        health_score -= int(orphan_pct * 40)
    if article_count < 3:
        health_score -= 15
    if fact_count < entity_count:
        health_score -= 10
    health_score = max(0, min(100, health_score))

    return {
        "entity_count": entity_count,
        "fact_count": fact_count,
        "article_count": article_count,
        "relation_count": relation_count,
        "new_entities_7d": new_entities,
        "new_facts_7d": new_facts,
        "new_articles_7d": new_articles,
        "health_score": health_score,
    }


def get_growth_data(user_id: str = "default", days: int = 30) -> list[dict]:
    """Return daily counts of entities + facts + articles created for sparkline."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    entities = supabase.table("entities").select("created_at").eq("user_id", user_id).gte("created_at", cutoff).execute().data
    facts = supabase.table("facts").select("created_at").eq("user_id", user_id).gte("created_at", cutoff).execute().data
    articles = supabase.table("articles").select("created_at").eq("user_id", user_id).gte("created_at", cutoff).execute().data

    # Group by date
    from collections import defaultdict
    daily = defaultdict(lambda: {"entities": 0, "facts": 0, "articles": 0})

    for e in entities:
        day = e["created_at"][:10]
        daily[day]["entities"] += 1
    for f in facts:
        day = f["created_at"][:10]
        daily[day]["facts"] += 1
    for a in articles:
        day = a["created_at"][:10]
        daily[day]["articles"] += 1

    # Build complete list for all days in range
    result = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        day_str = d.isoformat()
        counts = daily.get(day_str, {"entities": 0, "facts": 0, "articles": 0})
        result.append({"date": day_str, **counts})

    return result


def get_entity_detail(entity_id: int, user_id: str = "default") -> dict | None:
    """Get full entity detail: entity + facts + enriched relations."""
    result = supabase.table("entities").select("*").eq("id", entity_id).eq("user_id", user_id).execute()
    if not result.data:
        return None
    entity = result.data[0]
    entity["facts"] = get_facts_for_entity(entity_id)
    entity["relations"] = get_relations_for_entity_enriched(entity_id)
    return entity


def list_articles_enhanced(user_id: str = "default") -> list[dict]:
    """Articles with chunk count and read status."""
    articles = supabase.table("articles").select("id, title, url, file_path, is_read, read_at, created_at").eq("user_id", user_id).order("created_at", desc=True).execute().data
    for a in articles:
        chunks = supabase.table("article_chunks").select("id").eq("article_id", a["id"]).execute().data
        a["chunk_count"] = len(chunks)
    return articles
