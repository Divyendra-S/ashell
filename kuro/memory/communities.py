import json
import logging
from collections import defaultdict

import igraph as ig
import leidenalg

from kuro.core.llm import call_gemini
from kuro.memory import store

log = logging.getLogger("kuro.communities")

SUMMARY_INSTRUCTION = (
    "You are given a cluster of related concepts from a personal knowledge base, "
    "along with sample facts about them. "
    "Return a JSON object with two fields:\n"
    '- "name": a short label (2-4 words) for this topic cluster\n'
    '- "summary": a 1-2 sentence description of what this cluster covers\n'
    "Return ONLY the JSON object, nothing else."
)


def _build_igraph(entities: list[dict], relations: list[dict]) -> tuple[ig.Graph, dict]:
    """Convert entities + relations into an igraph Graph.
    Returns (graph, id_map) where id_map maps vertex index -> entity DB id.
    """
    entity_ids = [e["id"] for e in entities]
    id_to_idx = {eid: i for i, eid in enumerate(entity_ids)}

    g = ig.Graph(n=len(entities), directed=False)
    g.vs["entity_id"] = entity_ids
    g.vs["name"] = [e["name"] for e in entities]

    edges = []
    for r in relations:
        src_idx = id_to_idx.get(r["source_id"])
        tgt_idx = id_to_idx.get(r["target_id"])
        if src_idx is not None and tgt_idx is not None and src_idx != tgt_idx:
            edges.append((src_idx, tgt_idx))
    if edges:
        g.add_edges(edges)

    idx_to_id = {i: eid for i, eid in enumerate(entity_ids)}
    return g, idx_to_id


def _generate_summary(entity_names: list[str], facts_sample: list[str]) -> tuple[str, str]:
    """Call Gemini to produce a community name and summary."""
    prompt = (
        f"Concepts in this cluster: {', '.join(entity_names)}\n\n"
        f"Sample facts:\n" + "\n".join(f"- {f}" for f in facts_sample[:10])
    )
    try:
        response = call_gemini(
            [{"role": "user", "parts": [{"text": prompt}]}],
            system_instruction=SUMMARY_INSTRUCTION,
        )
        raw = response["candidates"][0]["content"]["parts"][0].get("text", "")
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        data = json.loads(raw)
        return data.get("name", "Unnamed Cluster"), data.get("summary", "")
    except Exception as e:
        log.warning(f"Community summary generation failed: {e}")
        # Fallback: use first few entity names
        return ", ".join(entity_names[:3]), f"Cluster covering: {', '.join(entity_names)}"


def rebuild_communities(user_id: str = "default") -> dict:
    """Full pipeline: load graph -> Leiden -> generate summaries -> persist."""
    graph_data = store.get_full_graph(user_id)
    entities = graph_data["entities"]
    relations = graph_data["relations"]

    if not entities:
        return {"community_count": 0, "entity_count": 0, "communities": []}

    # Build igraph
    g, idx_to_id = _build_igraph(entities, relations)

    # Run Leiden community detection
    if g.ecount() == 0:
        # No edges — each entity is its own community
        membership = list(range(len(entities)))
    else:
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            resolution_parameter=0.8,
        )
        membership = partition.membership

    # Group entities by community
    community_groups = defaultdict(list)
    for idx, comm_id in enumerate(membership):
        entity_id = idx_to_id[idx]
        community_groups[comm_id].append(entity_id)

    # Build entity lookup
    entity_map = {e["id"]: e for e in entities}

    # Delete old communities for this user
    old = store.supabase.table("communities").select("id").eq("user_id", user_id).execute().data
    if old:
        # Clear entity community_ids first
        for o in old:
            store.supabase.table("entities").update({"community_id": None}).eq("community_id", o["id"]).execute()
        for o in old:
            store.supabase.table("communities").delete().eq("id", o["id"]).execute()

    # Create new communities and assign entities
    result_communities = []
    for comm_idx, entity_ids in community_groups.items():
        names = [entity_map[eid]["name"] for eid in entity_ids if eid in entity_map]
        # Collect sample facts for summary generation
        facts_sample = []
        for eid in entity_ids[:5]:  # sample from first 5 entities
            facts = store.get_facts_for_entity(eid)
            for f in facts[:3]:
                facts_sample.append(f["content"])

        # Generate summary
        comm_name, comm_summary = _generate_summary(names, facts_sample)

        # Insert community
        row = store.supabase.table("communities").insert({
            "user_id": user_id,
            "name": comm_name,
            "summary": comm_summary,
            "entity_count": len(entity_ids),
        }).execute().data[0]

        # Update entities with community_id
        for eid in entity_ids:
            store.supabase.table("entities").update({"community_id": row["id"]}).eq("id", eid).execute()

        result_communities.append({
            "id": row["id"],
            "name": comm_name,
            "summary": comm_summary,
            "entity_count": len(entity_ids),
            "entities": names,
        })

    return {
        "community_count": len(result_communities),
        "entity_count": len(entities),
        "communities": result_communities,
    }


def get_communities(user_id: str = "default") -> list[dict]:
    """List all communities for a user."""
    return store.supabase.table("communities").select("*").eq("user_id", user_id).order("entity_count", desc=True).execute().data


def get_community(community_id: int) -> dict | None:
    """Get a single community by ID."""
    result = store.supabase.table("communities").select("*").eq("id", community_id).execute()
    return result.data[0] if result.data else None
