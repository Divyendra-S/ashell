import hashlib
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from nexus.graph.driver import run_query, run_write

log = logging.getLogger("nexus.wiki")

_BACKLINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Concept CRUD ---


def read_page(user_id: str, path: str) -> str | None:
    """Read a concept page by path. Path format: 'concepts/slug.md' or special paths like 'user/memories.md'."""
    # For concept pages, extract slug and query Concept node
    if path.startswith("concepts/") and path.endswith(".md"):
        slug = path.split("/")[-1].replace(".md", "")
        rows = run_query(
            "MATCH (c:Concept {slug: $slug, user_id: $uid}) RETURN c.content AS content",
            slug=slug, uid=user_id,
        )
        return rows[0]["content"] if rows else None

    # For special pages (_index.md, _recent.md, user/memories.md, user/profile.md)
    # These are stored as Concept nodes with special slugs
    special_slug = _path_to_slug(path)
    rows = run_query(
        "MATCH (c:Concept {slug: $slug, user_id: $uid}) RETURN c.content AS content",
        slug=special_slug, uid=user_id,
    )
    return rows[0]["content"] if rows else None


def write_page(user_id: str, path: str, content: str) -> str:
    """Write or update a concept page. Auto-appends to index for new concept pages."""
    is_concept = path.startswith("concepts/") and path.endswith(".md")
    now = _now_iso()

    if is_concept:
        slug = path.split("/")[-1].replace(".md", "")
        name = slug.replace("-", " ").title()

        # Extract name from first heading
        lines = content.strip().splitlines()
        if lines and lines[0].startswith("# "):
            name = lines[0][2:].strip()

        # Extract summary
        summary = ""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                summary = stripped[:200]
                break

        # Extract backlinks
        found_links = _BACKLINK_PATTERN.findall(content)

        # Check if new
        existing = run_query(
            "MATCH (c:Concept {slug: $slug, user_id: $uid}) RETURN c.slug",
            slug=slug, uid=user_id,
        )
        is_new = not existing

        # Upsert concept node
        run_write(
            """MERGE (c:Concept {slug: $slug, user_id: $uid})
            ON CREATE SET c.created_at = $now
            SET c.name = $name, c.summary = $summary, c.content = $content, c.updated_at = $now""",
            slug=slug, uid=user_id, name=name, summary=summary, content=content, now=now,
        )

        # Rebuild LINKS_TO relationships
        run_write(
            "MATCH (c:Concept {slug: $slug, user_id: $uid})-[r:LINKS_TO]->() DELETE r",
            slug=slug, uid=user_id,
        )
        for link_name in found_links:
            target_slug = _slugify(link_name)
            run_write(
                """MATCH (src:Concept {slug: $src_slug, user_id: $uid})
                MERGE (tgt:Concept {slug: $tgt_slug, user_id: $uid})
                ON CREATE SET tgt.name = $tgt_name, tgt.content = '', tgt.summary = '', tgt.created_at = $now, tgt.updated_at = $now
                WITH src, tgt
                MERGE (src)-[:LINKS_TO]->(tgt)""",
                src_slug=slug, tgt_slug=target_slug, tgt_name=link_name, uid=user_id, now=now,
            )

        # Auto-append to index for new concepts
        if is_new:
            index_entry = f"- [[{name}]] — {summary[:120]}"
            _append_to_index(user_id, index_entry)

        return path

    # Special pages
    special_slug = _path_to_slug(path)
    run_write(
        """MERGE (c:Concept {slug: $slug, user_id: $uid})
        ON CREATE SET c.name = $slug, c.summary = '', c.created_at = $now
        SET c.content = $content, c.updated_at = $now""",
        slug=special_slug, uid=user_id, content=content, now=now,
    )
    return path


def list_pages(user_id: str, directory: str | None = None) -> list[str]:
    if directory == "concepts" or directory is None:
        rows = run_query(
            """MATCH (c:Concept {user_id: $uid})
            WHERE c.slug =~ '^[a-z].*'
            AND NOT c.slug STARTS WITH '_'
            AND NOT c.slug STARTS WITH 'user-'
            RETURN c.slug AS slug ORDER BY c.slug""",
            uid=user_id,
        )
        return [f"concepts/{r['slug']}.md" for r in rows]
    return []


def _path_to_slug(path: str) -> str:
    return path.replace("/", "-").replace(".md", "").replace(".", "-")


# --- Index files ---


def read_index(user_id: str) -> str:
    return read_page(user_id, "_index.md") or ""


def write_index(user_id: str, content: str) -> str:
    write_page(user_id, "_index.md", content)
    return "_index.md"


def _append_to_index(user_id: str, entry: str) -> None:
    current = read_page(user_id, "_index.md") or "# Wiki Index\n"
    if entry.strip() in current:
        return
    updated = current.rstrip() + "\n" + entry + "\n"
    write_index(user_id, updated)


def read_recent(user_id: str) -> str:
    return read_page(user_id, "_recent.md") or ""


def write_recent(user_id: str, content: str) -> str:
    write_page(user_id, "_recent.md", content)
    return "_recent.md"


# --- User memories ---


def read_memories(user_id: str) -> str:
    return read_page(user_id, "user/memories.md") or ""


def write_memories(user_id: str, content: str) -> str:
    write_page(user_id, "user/memories.md", content)
    return "user/memories.md"


# --- Search ---


def grep_wiki(user_id: str, pattern: str, max_results: int = 10) -> list[dict]:
    words = re.findall(r'\w+', pattern)
    if not words:
        return []
    # Neo4j fulltext search with OR
    query_str = " OR ".join(words)
    try:
        rows = run_query(
            """CALL db.index.fulltext.queryNodes('concept_fts', $query)
            YIELD node, score
            WHERE node.user_id = $uid
            AND NOT node.slug STARTS WITH '_'
            AND NOT node.slug STARTS WITH 'user-'
            RETURN node.slug AS slug, node.content AS content, score
            ORDER BY score DESC LIMIT $limit""",
            query=query_str, uid=user_id, limit=max_results,
        )
    except Exception:
        # Fallback: CONTAINS search
        rows = run_query(
            """MATCH (c:Concept {user_id: $uid})
            WHERE c.content CONTAINS $pattern
            AND NOT c.slug STARTS WITH '_'
            RETURN c.slug AS slug, c.content AS content
            LIMIT $limit""",
            pattern=pattern, uid=user_id, limit=max_results,
        )
    return [{"file": f"concepts/{r['slug']}.md", "content": _build_snippet(r["content"], words)} for r in rows]


def search_knowledge(user_id: str, query: str, max_results: int = 15) -> list[dict]:
    words = re.findall(r'\w+', query)
    if not words:
        return []
    query_str = " OR ".join(words)
    results = []

    # Search concepts
    try:
        concept_rows = run_query(
            """CALL db.index.fulltext.queryNodes('concept_fts', $query)
            YIELD node, score
            WHERE node.user_id = $uid
            AND NOT node.slug STARTS WITH '_'
            AND NOT node.slug STARTS WITH 'user-'
            RETURN node.slug AS slug, node.name AS name, node.content AS content, score, 'concept' AS type
            ORDER BY score DESC LIMIT $limit""",
            query=query_str, uid=user_id, limit=max_results,
        )
        for r in concept_rows:
            results.append({
                "file": f"concepts/{r['slug']}.md",
                "title": r["name"],
                "type": "concept",
                "relevance": r["score"],
                "snippet": _build_snippet(r["content"], words),
            })
    except Exception:
        pass

    # Search articles
    try:
        article_rows = run_query(
            """CALL db.index.fulltext.queryNodes('article_fts', $query)
            YIELD node, score
            WHERE node.user_id = $uid
            RETURN node.id AS id, node.title AS title, node.file_path AS file_path, node.content AS content, score, 'article' AS type
            ORDER BY score DESC LIMIT $limit""",
            query=query_str, uid=user_id, limit=max_results,
        )
        for r in article_rows:
            results.append({
                "file": r["file_path"] or f"articles/{r['id']}",
                "title": r["title"],
                "type": "article",
                "relevance": r["score"],
                "snippet": _build_snippet(r.get("content", ""), words),
            })
    except Exception:
        pass

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:max_results]


def _build_snippet(content: str, words: list[str], context_chars: int = 250) -> str:
    if not content:
        return ""
    lower_content = content.lower()
    lower_words = [w.lower() for w in words]

    best_pos = 0
    best_density = 0
    window = context_chars * 2

    for i in range(0, len(lower_content), 50):
        window_text = lower_content[i:i + window]
        density = sum(window_text.count(w) for w in lower_words)
        if density > best_density:
            best_density = density
            best_pos = i

    start = max(0, best_pos)
    end = min(len(content), start + window)
    snippet = content[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    return snippet


# --- Graph building ---


def build_graph(user_id: str) -> dict:
    rows = run_query(
        """MATCH (c:Concept {user_id: $uid})
        WHERE NOT c.slug STARTS WITH '_'
        AND NOT c.slug STARTS WITH 'user-'
        AND c.content <> ''
        RETURN c.slug AS slug, c.name AS name, c.summary AS summary, c.content AS content""",
        uid=user_id,
    )
    if not rows:
        return {"entities": [], "relations": []}

    entities = []
    slug_to_id = {}

    for row in rows:
        slug = row["slug"]
        node_id = hashlib.md5(slug.encode()).hexdigest()[:12]
        slug_to_id[slug] = node_id

        found_links = _BACKLINK_PATTERN.findall(row["content"] or "")
        entities.append({
            "id": node_id,
            "name": row["name"] or slug.replace("-", " ").title(),
            "entity_type": "topic",
            "summary": row["summary"] or "",
            "fact_count": len(found_links),
        })

    # Get LINKS_TO relationships from graph
    rel_rows = run_query(
        """MATCH (src:Concept {user_id: $uid})-[:LINKS_TO]->(tgt:Concept {user_id: $uid})
        WHERE NOT src.slug STARTS WITH '_' AND NOT tgt.slug STARTS WITH '_'
        AND NOT src.slug STARTS WITH 'user-' AND NOT tgt.slug STARTS WITH 'user-'
        AND src.content <> '' AND tgt.content <> ''
        RETURN src.slug AS src_slug, tgt.slug AS tgt_slug""",
        uid=user_id,
    )

    relations = []
    seen_edges = set()
    for i, r in enumerate(rel_rows):
        src_id = slug_to_id.get(r["src_slug"])
        tgt_id = slug_to_id.get(r["tgt_slug"])
        if not src_id or not tgt_id or src_id == tgt_id:
            continue
        edge_key = (src_id, tgt_id)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        relations.append({
            "id": i,
            "source_id": src_id,
            "target_id": tgt_id,
            "relation_type": "related_to",
            "context": None,
            "source_name": r["src_slug"].replace("-", " ").title(),
            "target_name": r["tgt_slug"].replace("-", " ").title(),
        })

    return {"entities": entities, "relations": relations}


# --- Concept detail ---


def get_concept_detail(user_id: str, slug: str) -> dict | None:
    rows = run_query(
        """MATCH (c:Concept {slug: $slug, user_id: $uid})
        RETURN c.name AS name, c.summary AS summary, c.content AS content,
               c.created_at AS created_at, c.updated_at AS updated_at""",
        slug=slug, uid=user_id,
    )
    if not rows:
        return None

    row = rows[0]
    content = row["content"] or ""
    name = row["name"] or slug.replace("-", " ").title()

    found_links = _BACKLINK_PATTERN.findall(content)
    backlinks = [{"name": link, "slug": _slugify(link)} for link in found_links]

    # Incoming backlinks via graph relationships
    incoming_rows = run_query(
        """MATCH (src:Concept {user_id: $uid})-[:LINKS_TO]->(tgt:Concept {slug: $slug, user_id: $uid})
        WHERE src.slug <> $slug AND src.content <> ''
        RETURN src.name AS name, src.slug AS slug""",
        slug=slug, uid=user_id,
    )
    incoming = [{"name": r["name"] or r["slug"].replace("-", " ").title(), "slug": r["slug"]} for r in incoming_rows]

    notes = _extract_section(content, "Notes")

    return {
        "slug": slug,
        "name": name,
        "summary": row["summary"] or "",
        "content": content,
        "backlinks": backlinks,
        "incoming_backlinks": incoming,
        "notes": notes,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _extract_section(content: str, heading: str) -> str | None:
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


# --- Stats ---


def get_wiki_stats(user_id: str) -> dict:
    count_rows = run_query(
        """MATCH (c:Concept {user_id: $uid})
        WHERE NOT c.slug STARTS WITH '_' AND NOT c.slug STARTS WITH 'user-'
        AND c.content <> ''
        RETURN count(c) AS concept_count""",
        uid=user_id,
    )
    concept_count = count_rows[0]["concept_count"] if count_rows else 0

    backlink_rows = run_query(
        """MATCH (src:Concept {user_id: $uid})-[r:LINKS_TO]->(tgt:Concept {user_id: $uid})
        RETURN count(r) AS backlink_count""",
        uid=user_id,
    )
    backlink_count = backlink_rows[0]["backlink_count"] if backlink_rows else 0

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    new_rows = run_query(
        """MATCH (c:Concept {user_id: $uid})
        WHERE NOT c.slug STARTS WITH '_' AND NOT c.slug STARTS WITH 'user-'
        AND c.content <> '' AND c.created_at >= $cutoff
        RETURN count(c) AS cnt""",
        uid=user_id, cutoff=cutoff,
    )
    new_concepts_7d = new_rows[0]["cnt"] if new_rows else 0

    # Health score based on orphan ratio
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
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=days)).isoformat()

    rows = run_query(
        """MATCH (c:Concept {user_id: $uid})
        WHERE NOT c.slug STARTS WITH '_' AND NOT c.slug STARTS WITH 'user-'
        AND c.content <> '' AND c.created_at >= $cutoff
        RETURN c.created_at AS created_at""",
        uid=user_id, cutoff=cutoff,
    )

    daily = defaultdict(int)
    for row in rows:
        day_str = row["created_at"][:10]
        daily[day_str] += 1

    output = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        day_str = d.isoformat()
        output.append({"date": day_str, "concepts": daily.get(day_str, 0)})
    return output
