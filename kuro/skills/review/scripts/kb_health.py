"""Analyze wiki knowledge base health — find orphan pages, sparse topics, coverage stats."""

import re

from kuro.memory import wiki, store

_BACKLINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def kb_health_report(user_id: str) -> dict:
    """Scan wiki concept pages and return a health report."""
    from kuro.memory.store import supabase

    result = (
        supabase.table("wiki_pages")
        .select("path, content")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .execute()
    )

    if not result.data:
        return {
            "concept_count": 0, "article_count": 0, "backlink_count": 0,
            "orphan_pages": [], "sparse_pages": [], "rich_pages": [],
            "suggestions": ["Start adding knowledge to your wiki!"],
        }

    pages = {}
    all_backlinks = set()
    all_sources = set()

    for row in result.data:
        slug = row["path"].split("/")[-1].replace(".md", "")
        content = row["content"]
        word_count = len(content.split())
        links = _BACKLINK_PATTERN.findall(content)
        link_slugs = [wiki._slugify(link) for link in links]

        pages[slug] = {
            "name": slug.replace("-", " ").title(),
            "word_count": word_count,
            "outgoing_links": len(links),
            "link_slugs": link_slugs,
        }

        if link_slugs:
            all_sources.add(slug)
            for ls in link_slugs:
                all_backlinks.add(ls)

    total_backlinks = sum(p["outgoing_links"] for p in pages.values())
    linked_slugs = all_backlinks | all_sources
    orphans = [p for slug, p in pages.items() if slug not in linked_slugs]
    sparse = [p for p in pages.values() if p["word_count"] < 200]
    rich = [p for p in pages.values() if p["word_count"] >= 500]

    try:
        articles = store.list_articles(user_id=user_id)
    except Exception:
        articles = []

    suggestions = []
    if orphans:
        names = [o["name"] for o in orphans[:5]]
        suggestions.append(f"Connect orphan pages with [[backlinks]]: {', '.join(names)}")
    if sparse:
        names = [s["name"] for s in sparse[:5]]
        suggestions.append(f"Expand sparse pages (under 200 words): {', '.join(names)}")
    if len(articles) < 3:
        suggestions.append("Ingest more articles to build richer knowledge")
    if not rich:
        suggestions.append("No concept pages have 500+ words — consider deepening key topics")
    if len(pages) > 0 and len(orphans) / len(pages) > 0.5:
        suggestions.append("Over half your pages have no connections — add [[backlinks]] to link concepts")

    return {
        "concept_count": len(pages),
        "article_count": len(articles),
        "backlink_count": total_backlinks,
        "orphan_pages": [{"name": o["name"], "words": o["word_count"]} for o in orphans],
        "sparse_pages": [{"name": s["name"], "words": s["word_count"]} for s in sparse],
        "rich_pages": [{"name": r["name"], "words": r["word_count"]} for r in rich],
        "suggestions": suggestions,
    }
