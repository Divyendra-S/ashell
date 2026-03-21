"""Analyze knowledge base health — find orphans, sparse topics, coverage stats."""

import json

from kuro.memory import store


def kb_health_report(user_id: str) -> dict:
    """Query the KB and return a health report.

    Returns dict with:
      - entity_count: total entities
      - fact_count: total facts
      - article_count: total articles
      - orphan_entities: entities with 0 facts
      - sparse_entities: entities with only 1 fact
      - rich_entities: entities with 3+ facts
      - entity_types: breakdown by type
      - suggestions: list of actionable suggestions
    """
    # Get all entities for this user
    entities = store.supabase.table("entities").select("id, name, entity_type, summary").eq("user_id", user_id).execute().data

    # Get fact counts per entity
    entity_fact_counts = {}
    for e in entities:
        facts = store.get_facts_for_entity(e["id"])
        entity_fact_counts[e["id"]] = {"name": e["name"], "type": e["entity_type"], "fact_count": len(facts)}

    # Get articles
    articles = store.list_articles(user_id=user_id)

    # Classify entities
    orphans = [v for v in entity_fact_counts.values() if v["fact_count"] == 0]
    sparse = [v for v in entity_fact_counts.values() if v["fact_count"] == 1]
    rich = [v for v in entity_fact_counts.values() if v["fact_count"] >= 3]

    # Type breakdown
    type_counts = {}
    for e in entities:
        t = e.get("entity_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Generate suggestions
    suggestions = []
    if orphans:
        names = [o["name"] for o in orphans[:5]]
        suggestions.append(f"Add facts to orphan entities: {', '.join(names)}")
    if len(articles) < 3:
        suggestions.append("Ingest more articles to build richer context for retrieval")
    if not rich:
        suggestions.append("No entities have 3+ facts — consider deepening knowledge on key topics")
    if len(entities) > 0 and len(orphans) / len(entities) > 0.5:
        suggestions.append("Over half your entities have no facts — focus on enrichment over breadth")

    return {
        "entity_count": len(entities),
        "fact_count": sum(v["fact_count"] for v in entity_fact_counts.values()),
        "article_count": len(articles),
        "orphan_entities": [{"name": o["name"], "type": o["type"]} for o in orphans],
        "sparse_entities": [{"name": s["name"], "type": s["type"]} for s in sparse],
        "rich_entities": [{"name": r["name"], "type": r["type"], "facts": r["fact_count"]} for r in rich],
        "entity_types": type_counts,
        "suggestions": suggestions,
    }
