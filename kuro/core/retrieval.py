import json
import logging

from kuro.core.llm import call_gemini, embed_texts
from kuro.memory import store

log = logging.getLogger("kuro.retrieval")

REWRITE_INSTRUCTION = (
    "Given a user question, produce 2-3 search queries optimized for a knowledge base. "
    "Return ONLY a JSON array of strings."
)


def rewrite_query(user_text: str) -> list[str]:
    response = call_gemini(
        [{"role": "user", "parts": [{"text": user_text}]}],
        system_instruction=REWRITE_INSTRUCTION,
    )
    raw = response["candidates"][0]["content"]["parts"][0].get("text", "")
    try:
        queries = json.loads(raw)
        if not isinstance(queries, list):
            queries = [user_text]
    except (json.JSONDecodeError, KeyError):
        queries = [user_text]
    if user_text not in queries:
        queries.append(user_text)
    return queries


def hybrid_retrieve(
    queries: list[str],
    vec_threshold: float = 0.3,
    vec_limit: int = 10,
    user_id: str = "default",
) -> list[dict]:
    embeddings = embed_texts(queries)
    results = []

    for rank_offset, query in enumerate(queries):
        # FTS
        fts_data = store.search_knowledge_unified(query, user_id=user_id)
        if isinstance(fts_data, dict):
            entities = fts_data.get("entities", [])
            facts = fts_data.get("facts", [])
            chunks = fts_data.get("article_chunks", [])
        elif isinstance(fts_data, list):
            entities, facts, chunks = [], [], []
            for item in fts_data:
                t = item.get("result_type", "")
                if t == "entity":
                    entities.append(item)
                elif t == "fact":
                    facts.append(item)
                elif t == "article_chunk":
                    chunks.append(item)
        else:
            entities, facts, chunks = [], [], []

        for i, e in enumerate(entities):
            results.append({
                "key": f"entity:{e.get('name', '')}",
                "type": "entity",
                "content": e.get("summary", ""),
                "title": e.get("name", ""),
                "file_path": None,
                "rank": i + 1,
                "source": "fts",
                "similarity": None,
                "entity_type": e.get("entity_type"),
            })

        for i, f in enumerate(facts):
            results.append({
                "key": f"fact:{f.get('id', i)}",
                "type": "fact",
                "content": f.get("content", ""),
                "title": None,
                "file_path": None,
                "rank": i + 1,
                "source": "fts",
                "similarity": None,
                "entity_id": f.get("entity_id"),
            })

        for i, c in enumerate(chunks):
            results.append({
                "key": f"chunk:{c.get('id', i)}",
                "type": "article_chunk",
                "content": c.get("content", ""),
                "title": c.get("article_title", c.get("title")),
                "file_path": c.get("file_path"),
                "rank": i + 1,
                "source": "fts",
                "similarity": None,
            })

        # Vector search
        embedding = embeddings[rank_offset]
        vec_results = store.semantic_search_chunks(embedding, vec_threshold, vec_limit, user_id=user_id)

        if vec_results:
            article_ids = list({r["article_id"] for r in vec_results if r.get("article_id")})
            article_map = {}
            if article_ids:
                articles = (
                    store.supabase.table("articles")
                    .select("id, title, url")
                    .in_("id", article_ids)
                    .execute()
                )
                article_map = {a["id"]: a for a in articles.data}

            for i, v in enumerate(vec_results):
                article = article_map.get(v.get("article_id"), {})
                results.append({
                    "key": f"chunk:{v.get('id', '')}",
                    "type": "article_chunk",
                    "content": v.get("content", ""),
                    "title": article.get("title"),
                    "file_path": article.get("url"),
                    "rank": i + 1,
                    "source": "vector",
                    "similarity": v.get("similarity"),
                })

    return results


def rrf_merge(results: list[dict], top_k: int = 8, k: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    best: dict[str, dict] = {}

    for r in results:
        key = r["key"]
        scores[key] = scores.get(key, 0) + 1 / (k + r["rank"])
        # Keep version with more metadata
        if key not in best or _metadata_count(r) > _metadata_count(best[key]):
            best[key] = r

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [best[key] for key, _ in ranked[:top_k]]


def _metadata_count(r: dict) -> int:
    return sum(1 for v in r.values() if v is not None)


def graph_retrieve(user_text: str, user_id: str = "default") -> list[dict]:
    """Match entities from query via FTS, pull 1-hop neighborhood as structured context."""
    results = []

    # Find matching entities via FTS
    matched_entities = store.search_entities(user_text, user_id=user_id)
    if not matched_entities:
        return results

    seen_communities = set()
    for entity in matched_entities[:3]:
        eid = entity["id"]
        name = entity["name"]

        # Get top facts
        facts = store.get_facts_for_entity(eid)
        fact_texts = [f["content"] for f in facts[:5]]

        # Get relations (1-hop neighborhood)
        relations = store.get_relations_for_entity_enriched(eid)
        rel_texts = []
        for r in relations[:8]:
            src = r.get("source_name", "?")
            tgt = r.get("target_name", "?")
            rtype = r.get("relation_type", "related_to")
            rel_texts.append(f"{src} --[{rtype}]--> {tgt}")

        # Build graph neighborhood context
        content_parts = []
        if fact_texts:
            content_parts.append("Facts: " + "; ".join(fact_texts))
        if rel_texts:
            content_parts.append("Connections: " + "; ".join(rel_texts))

        results.append({
            "key": f"graph:{name}",
            "type": "graph_neighborhood",
            "title": name,
            "content": "\n".join(content_parts),
            "entity_type": entity.get("entity_type"),
            "rank": 0,
            "source": "graph",
            "similarity": None,
        })

        # Community summary (deduplicated)
        community_id = entity.get("community_id")
        if community_id and community_id not in seen_communities:
            seen_communities.add(community_id)
            comm = store.supabase.table("communities").select("name, summary").eq("id", community_id).execute()
            if comm.data:
                c = comm.data[0]
                results.append({
                    "key": f"community:{community_id}",
                    "type": "community_summary",
                    "title": c.get("name", ""),
                    "content": c.get("summary", ""),
                    "rank": 0,
                    "source": "graph",
                    "similarity": None,
                })

    return results
