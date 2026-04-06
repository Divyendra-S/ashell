"""Migrate Supabase knowledge graph data to wiki markdown files.

Reads entities, facts, relations, passages, user_memories, and notes from Supabase,
generates markdown concept pages with [[backlinks]], and writes them to data/wiki/{user_id}/.

Does NOT delete Supabase data — old data stays as backup.

Usage:
    uv run python scripts/migrate_to_wiki.py [user_id]
    uv run python scripts/migrate_to_wiki.py          # migrates 'default' user
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kuro.memory.store import supabase
from kuro.memory.wiki import _slugify, _wiki_dir, write_page, write_index, write_memories, write_recent


def migrate_user(user_id: str = "default"):
    print(f"\n=== Migrating user: {user_id} ===\n")

    # --- Fetch all data from Supabase ---
    print("Fetching entities...")
    entities = supabase.table("entities").select("*").eq("user_id", user_id).execute().data
    print(f"  Found {len(entities)} entities")

    print("Fetching facts...")
    facts = supabase.table("facts").select("*").eq("user_id", user_id).execute().data
    facts_by_entity = defaultdict(list)
    for f in facts:
        facts_by_entity[f["entity_id"]].append(f)
    print(f"  Found {len(facts)} facts")

    print("Fetching relations...")
    relations = supabase.table("relations").select("*").eq("user_id", user_id).execute().data
    print(f"  Found {len(relations)} relations")

    # Build entity name lookup
    entity_names = {e["id"]: e["name"] for e in entities}

    # Build relations by entity
    relations_by_entity = defaultdict(list)
    for r in relations:
        relations_by_entity[r["source_id"]].append(r)
        relations_by_entity[r["target_id"]].append(r)

    # Fetch passages
    print("Fetching passages...")
    try:
        passages = supabase.table("entity_passages").select("*, articles(id, title, url)").eq("user_id", user_id).execute().data
    except Exception:
        passages = []
    passages_by_entity = defaultdict(list)
    for p in passages:
        passages_by_entity[p["entity_id"]].append(p)
    print(f"  Found {len(passages)} passages")

    # Fetch notes
    print("Fetching notes...")
    try:
        notes = supabase.table("notes").select("*").eq("user_id", user_id).execute().data
    except Exception:
        notes = []
    notes_by_entity = defaultdict(list)
    for n in notes:
        if n.get("entity_id"):
            notes_by_entity[n["entity_id"]].append(n)
    print(f"  Found {len(notes)} notes")

    # --- Generate concept pages ---
    print("\nGenerating concept pages...")
    index_entries = []

    for entity in entities:
        eid = entity["id"]
        name = entity["name"]
        slug = _slugify(name)
        summary = entity.get("summary") or ""
        etype = entity.get("entity_type", "topic")

        entity_facts = facts_by_entity.get(eid, [])
        entity_rels = relations_by_entity.get(eid, [])
        entity_passages = passages_by_entity.get(eid, [])
        entity_notes = notes_by_entity.get(eid, [])

        # Build markdown
        lines = [f"# {name}"]
        if summary:
            lines.append("")
            lines.append(summary)

        # Key Facts
        if entity_facts:
            lines.append("")
            lines.append("## Key Facts")
            for f in entity_facts:
                content = f["content"].strip()
                # If it's multi-sentence, keep as a paragraph bullet
                lines.append(f"- {content}")

        # Connections (with backlinks)
        if entity_rels:
            lines.append("")
            lines.append("## Connections")
            seen_connections = set()
            for r in entity_rels:
                if r["source_id"] == eid:
                    other_name = entity_names.get(r["target_id"], "Unknown")
                    direction = ""
                else:
                    other_name = entity_names.get(r["source_id"], "Unknown")
                    direction = " (incoming)"

                rel_type = r.get("relation_type", "related_to")
                context = r.get("context", "")
                conn_key = (other_name, rel_type)
                if conn_key in seen_connections:
                    continue
                seen_connections.add(conn_key)

                context_str = f" — {context}" if context else ""
                lines.append(f"- [[{other_name}]] ({rel_type}){context_str}")

        # Source Passages
        if entity_passages:
            lines.append("")
            lines.append("## Source Passages")
            for p in entity_passages:
                content = p["content"].strip()
                article_info = p.get("articles") or {}
                title = article_info.get("title", "Unknown source")
                url = article_info.get("url", "")
                source_ref = f"[{title}]({url})" if url else title
                lines.append(f"> {content}")
                lines.append(f"> — {source_ref}")
                lines.append("")

        # Notes
        if entity_notes:
            lines.append("")
            lines.append("## Notes")
            for n in entity_notes:
                lines.append(f"- {n['content']}")

        content = "\n".join(lines) + "\n"
        file_path = f"concepts/{slug}.md"

        # Don't use write_page (which auto-appends index) — we'll build index manually
        wiki = _wiki_dir(user_id)
        (wiki / "concepts").mkdir(parents=True, exist_ok=True)
        (wiki / file_path).write_text(content)
        print(f"  Wrote {file_path} ({len(entity_facts)} facts, {len(entity_rels)} relations)")

        # Build index entry
        summary_short = summary[:120] if summary else f"{etype} concept"
        index_entries.append(f"- [[{name}]] — {summary_short}")

    # --- Build _index.md ---
    print(f"\nBuilding _index.md with {len(index_entries)} entries...")
    index_content = "# Wiki Index\n\n" + "\n".join(sorted(index_entries)) + "\n"
    write_index(user_id, index_content)

    # --- Migrate user memories ---
    print("Migrating user memories...")
    try:
        memories = supabase.table("user_memories").select("*").eq("user_id", user_id).order("importance", desc=True).execute().data
    except Exception:
        memories = []

    if memories:
        grouped = defaultdict(list)
        for m in memories:
            grouped[m.get("type", "context")].append(m)

        mem_lines = ["# Memories", ""]
        for mem_type in ("instruction", "preference", "context"):
            items = grouped.get(mem_type, [])
            if items:
                mem_lines.append(f"## {mem_type.title()}s")
                for m in items:
                    imp = m.get("importance", 5)
                    imp_tag = f" [importance={imp}]" if imp != 5 else ""
                    mem_lines.append(f"- **{m['name']}**: {m['content']}{imp_tag}")
                mem_lines.append("")

        write_memories(user_id, "\n".join(mem_lines) + "\n")
        print(f"  Migrated {len(memories)} memories")
    else:
        print("  No memories to migrate")

    # --- Move user profile ---
    print("Migrating user profile...")
    old_profile = Path(__file__).parent.parent / "data" / "user_profiles" / user_id / "profile.md"
    if old_profile.exists():
        profile_content = old_profile.read_text()
        wiki = _wiki_dir(user_id)
        (wiki / "user").mkdir(parents=True, exist_ok=True)
        (wiki / "user" / "profile.md").write_text(profile_content)
        print(f"  Copied profile ({len(profile_content)} chars)")
    else:
        print("  No profile found")

    # --- Initialize _recent.md ---
    write_recent(user_id, "# Recent Changes\n\n_Migrated from Supabase knowledge graph._\n")

    # --- Summary ---
    print(f"\n=== Migration complete for {user_id} ===")
    print(f"  Concepts: {len(entities)}")
    print(f"  Facts: {len(facts)}")
    print(f"  Relations: {len(relations)}")
    print(f"  Passages: {len(passages)}")
    print(f"  Notes: {len(notes)}")
    print(f"  Memories: {len(memories)}")
    print(f"  Wiki root: {_wiki_dir(user_id)}")


if __name__ == "__main__":
    target_user = sys.argv[1] if len(sys.argv) > 1 else "default"
    migrate_user(target_user)
