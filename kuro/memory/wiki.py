"""Wiki-based knowledge storage layer — Supabase backend.

All knowledge is stored as rows in the wiki_pages table.
The LLM maintains index files, concept articles, and user memories.
"""

import hashlib
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone

from kuro.memory.store import supabase

log = logging.getLogger("kuro.wiki")

_BACKLINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _slugify(name: str) -> str:
    """Convert a concept name to a filename-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


# --- Core read/write ---


def read_page(user_id: str, path: str) -> str | None:
    """Read a wiki page by relative path (e.g., 'concepts/attention.md')."""
    result = (
        supabase.table("wiki_pages")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", path)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["content"]


def write_page(user_id: str, path: str, content: str) -> str:
    """Write a wiki page. Auto-appends to _index.md for new concept pages."""
    is_concept = path.startswith("concepts/") and path.endswith(".md")

    # Check if page exists before upsert
    existing = (
        supabase.table("wiki_pages")
        .select("id")
        .eq("user_id", user_id)
        .eq("path", path)
        .execute()
    )
    is_new = not existing.data

    supabase.table("wiki_pages").upsert({
        "user_id": user_id,
        "path": path,
        "content": content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,path").execute()

    # Auto-append to _index.md for new concept pages
    if is_new and is_concept:
        stem = path.rsplit("/", 1)[-1].replace(".md", "")
        name = stem.replace("-", " ").title()
        # Extract first paragraph as summary
        lines = content.strip().splitlines()
        summary = ""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                summary = stripped[:120]
                break
        index_entry = f"- [[{name}]] — {summary}"
        _append_to_index(user_id, index_entry)

    return path


def list_pages(user_id: str, directory: str | None = None) -> list[str]:
    """List all pages under a wiki subdirectory. Returns relative paths."""
    query = supabase.table("wiki_pages").select("path").eq("user_id", user_id)
    if directory:
        query = query.like("path", f"{directory}/%")
    else:
        # Exclude internal files
        query = query.not_.like("path", "\\_%")
    result = query.order("path").execute()
    return [r["path"] for r in result.data]


# --- Index files ---


def read_index(user_id: str) -> str:
    """Read _index.md (the wiki table of contents)."""
    return read_page(user_id, "_index.md") or ""


def write_index(user_id: str, content: str) -> str:
    """Write _index.md (full rewrite by LLM for reorganization)."""
    supabase.table("wiki_pages").upsert({
        "user_id": user_id,
        "path": "_index.md",
        "content": content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,path").execute()
    return "_index.md"


def _append_to_index(user_id: str, entry: str) -> None:
    """Append a single line to _index.md (used by write_page for new concepts)."""
    current = read_page(user_id, "_index.md") or "# Wiki Index\n"
    if entry.strip() in current:
        return
    updated = current.rstrip() + "\n" + entry + "\n"
    write_index(user_id, updated)


def read_recent(user_id: str) -> str:
    """Read _recent.md (last ~20 changes)."""
    return read_page(user_id, "_recent.md") or ""


def write_recent(user_id: str, content: str) -> str:
    """Write _recent.md."""
    supabase.table("wiki_pages").upsert({
        "user_id": user_id,
        "path": "_recent.md",
        "content": content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,path").execute()
    return "_recent.md"


# --- User memories ---


def read_memories(user_id: str) -> str:
    """Read user/memories.md."""
    return read_page(user_id, "user/memories.md") or ""


def write_memories(user_id: str, content: str) -> str:
    """Write user/memories.md."""
    supabase.table("wiki_pages").upsert({
        "user_id": user_id,
        "path": "user/memories.md",
        "content": content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,path").execute()
    return "user/memories.md"


# --- Search ---


def grep_wiki(user_id: str, pattern: str, max_results: int = 10) -> list[dict]:
    """Search across all wiki pages using Postgres full-text search with OR logic."""
    words = re.findall(r'\w+', pattern)
    if not words:
        return []
    # Use OR logic so "skills subagent" finds pages about either topic
    tsquery = " | ".join(words)

    try:
        # NOTE: .limit() must come before .text_search() in supabase-py
        result = (
            supabase.table("wiki_pages")
            .select("path, content")
            .eq("user_id", user_id)
            .limit(max_results)
            .text_search("fts", tsquery)
            .execute()
        )
    except Exception:
        result = (
            supabase.table("wiki_pages")
            .select("path, content")
            .eq("user_id", user_id)
            .ilike("content", f"%{pattern}%")
            .limit(max_results)
            .execute()
        )

    results = _extract_snippets(result.data, words)
    return results


def search_knowledge(user_id: str, query: str, max_results: int = 15) -> list[dict]:
    """Combined search across concepts and articles with relevance scoring.

    Uses OR-based FTS to find all relevant pages, then ranks by how many
    query terms matched. Returns richer snippets with page type info.
    """
    words = re.findall(r'\w+', query)
    if not words:
        return []
    tsquery = " | ".join(words)

    try:
        # NOTE: .limit() must come before .text_search() in supabase-py
        result = (
            supabase.table("wiki_pages")
            .select("path, content")
            .eq("user_id", user_id)
            .limit(max_results * 2)
            .text_search("fts", tsquery)
            .execute()
        )
    except Exception:
        result = (
            supabase.table("wiki_pages")
            .select("path, content")
            .eq("user_id", user_id)
            .ilike("content", f"%{query}%")
            .limit(max_results)
            .execute()
        )

    if not result.data:
        return []

    # Score each result by number of query terms found
    scored = []
    lower_words = [w.lower() for w in words]
    for row in result.data:
        content = row["content"]
        lower_content = content.lower()
        # Count how many query terms appear
        term_hits = sum(1 for w in lower_words if w in lower_content)
        # Bonus for title/heading matches
        first_line = content.split("\n", 1)[0].lower()
        heading_hits = sum(1 for w in lower_words if w in first_line)
        score = term_hits + heading_hits * 2

        # Classify page type
        path = row["path"]
        if path.startswith("concepts/"):
            page_type = "concept"
        elif path.startswith("articles/"):
            page_type = "article"
        else:
            page_type = "other"

        scored.append((score, path, content, page_type))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, path, content, page_type in scored[:max_results]:
        snippet = _build_snippet(content, lower_words, context_chars=250)
        # Extract title from first heading
        first_line = content.split("\n", 1)[0]
        title = first_line.lstrip("# ").strip() if first_line.startswith("#") else path

        results.append({
            "file": path,
            "title": title,
            "type": page_type,
            "relevance": score,
            "snippet": snippet,
        })

    return results


def _build_snippet(content: str, search_words: list[str], context_chars: int = 250) -> str:
    """Build a context snippet around the best matching region."""
    lower_content = content.lower()

    # Find the position with the densest cluster of matches
    best_pos = 0
    best_density = 0
    window = context_chars * 2

    for i in range(0, len(lower_content), 50):
        window_text = lower_content[i:i + window]
        density = sum(window_text.count(w) for w in search_words)
        if density > best_density:
            best_density = density
            best_pos = i

    start = max(0, best_pos)
    end = min(len(content), start + window)
    snippet = content[start:end].strip()

    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    return snippet


def _extract_snippets(rows: list[dict], words: list[str]) -> list[dict]:
    """Extract snippets from search results with wider context."""
    lower_words = [w.lower() for w in words]
    results = []
    for row in rows:
        content = row["content"]
        snippet = _build_snippet(content, lower_words, context_chars=200)
        results.append({
            "file": row["path"],
            "content": snippet,
        })
    return results


# --- Graph building (for frontend visualization) ---


def build_graph(user_id: str) -> dict:
    """Parse concept pages, extract [[backlinks]], return graph data for frontend."""
    result = (
        supabase.table("wiki_pages")
        .select("path, content")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .execute()
    )

    if not result.data:
        return {"entities": [], "relations": []}

    entities = []
    slug_to_id = {}
    backlinks_map = defaultdict(list)

    for row in result.data:
        path = row["path"]
        content = row["content"]
        slug = path.split("/")[-1].replace(".md", "")
        name = slug.replace("-", " ").title()
        node_id = hashlib.md5(slug.encode()).hexdigest()[:12]
        slug_to_id[slug] = node_id

        lines = content.strip().splitlines()
        if lines and lines[0].startswith("# "):
            name = lines[0][2:].strip()

        summary = ""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                summary = stripped[:200]
                break

        found_links = _BACKLINK_PATTERN.findall(content)
        link_count = len(found_links)

        for link_name in found_links:
            target_slug = _slugify(link_name)
            backlinks_map[target_slug].append(slug)

        entities.append({
            "id": node_id,
            "name": name,
            "entity_type": "topic",
            "summary": summary,
            "fact_count": link_count,
        })

    relations = []
    rel_id = 0
    seen_edges = set()
    for target_slug, source_slugs in backlinks_map.items():
        target_id = slug_to_id.get(target_slug)
        if not target_id:
            continue
        for source_slug in source_slugs:
            source_id = slug_to_id.get(source_slug)
            if not source_id or source_id == target_id:
                continue
            edge_key = (source_id, target_id)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            source_name = source_slug.replace("-", " ").title()
            target_name = target_slug.replace("-", " ").title()
            relations.append({
                "id": rel_id,
                "source_id": source_id,
                "target_id": target_id,
                "relation_type": "related_to",
                "context": None,
                "source_name": source_name,
                "target_name": target_name,
            })
            rel_id += 1

    return {"entities": entities, "relations": relations}


# --- Concept detail ---


def get_concept_detail(user_id: str, slug: str) -> dict | None:
    """Read concepts/{slug}.md, parse into structured detail for the frontend."""
    path = f"concepts/{slug}.md"
    result = (
        supabase.table("wiki_pages")
        .select("content, created_at, updated_at")
        .eq("user_id", user_id)
        .eq("path", path)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    content = row["content"]

    lines = content.strip().splitlines()
    name = slug.replace("-", " ").title()
    if lines and lines[0].startswith("# "):
        name = lines[0][2:].strip()

    summary = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            summary = stripped[:300]
            break

    found_links = _BACKLINK_PATTERN.findall(content)
    backlinks = [{"name": link, "slug": _slugify(link)} for link in found_links]

    incoming = _find_incoming_backlinks(user_id, slug)
    notes = _extract_section(content, "Notes")

    return {
        "slug": slug,
        "name": name,
        "summary": summary,
        "content": content,
        "backlinks": backlinks,
        "incoming_backlinks": incoming,
        "notes": notes,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _find_incoming_backlinks(user_id: str, target_slug: str) -> list[dict]:
    """Find all concept pages that link to the given slug."""
    result = (
        supabase.table("wiki_pages")
        .select("path, content")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .neq("path", f"concepts/{target_slug}.md")
        .execute()
    )

    incoming = []
    for row in result.data:
        links = _BACKLINK_PATTERN.findall(row["content"])
        for link in links:
            if _slugify(link) == target_slug:
                stem = row["path"].split("/")[-1].replace(".md", "")
                incoming.append({
                    "name": stem.replace("-", " ").title(),
                    "slug": stem,
                })
                break
    return incoming


def _extract_section(content: str, heading: str) -> str | None:
    """Extract content under a ## heading, up to the next ## heading."""
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(content)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^## ", content[start:], re.MULTILINE)
    if next_heading:
        section = content[start:start + next_heading.start()]
    else:
        section = content[start:]
    return section.strip() or None


# --- Stats for dashboard ---


def get_wiki_stats(user_id: str) -> dict:
    """Count concept pages, backlinks, ages for stats/growth endpoints."""
    result = (
        supabase.table("wiki_pages")
        .select("path, content, created_at")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .execute()
    )

    concept_count = len(result.data)
    backlink_count = 0
    new_concepts_7d = 0
    now = datetime.now(timezone.utc)
    cutoff_7d = now.timestamp() - (7 * 86400)

    for row in result.data:
        backlink_count += len(_BACKLINK_PATTERN.findall(row["content"]))
        created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        if created.timestamp() >= cutoff_7d:
            new_concepts_7d += 1

    # Health score
    health_score = 100
    if concept_count > 0:
        graph = build_graph(user_id)
        linked_ids = set()
        for r in graph["relations"]:
            linked_ids.add(r["source_id"])
            linked_ids.add(r["target_id"])
        orphan_count = sum(1 for e in graph["entities"] if e["id"] not in linked_ids)
        orphan_pct = orphan_count / concept_count if concept_count else 0
        health_score -= int(orphan_pct * 40)

    health_score = max(0, min(100, health_score))

    return {
        "concept_count": concept_count,
        "backlink_count": backlink_count,
        "new_concepts_7d": new_concepts_7d,
        "health_score": health_score,
    }


def get_growth_data(user_id: str, days: int = 30) -> list[dict]:
    """Daily concept creation counts."""
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=days)).isoformat()

    result = (
        supabase.table("wiki_pages")
        .select("created_at")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .gte("created_at", cutoff)
        .execute()
    )

    daily = defaultdict(int)
    for row in result.data:
        day_str = row["created_at"][:10]
        daily[day_str] += 1

    output = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        day_str = d.isoformat()
        output.append({"date": day_str, "concepts": daily.get(day_str, 0)})

    return output
