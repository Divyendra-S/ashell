"""Migrate wiki markdown files and articles from filesystem to Supabase wiki_pages table.

Usage:
    uv run python scripts/migrate_wiki_to_supabase.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from kuro.memory.store import supabase

WIKI_ROOT = Path(__file__).parent.parent / "data" / "wiki"
ARTICLES_ROOT = Path(__file__).parent.parent / "data" / "articles"


def migrate_wiki():
    """Migrate all wiki files for all users."""
    if not WIKI_ROOT.exists():
        print("No wiki data found")
        return 0

    total = 0
    for user_dir in WIKI_ROOT.iterdir():
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name
        print(f"\n=== Migrating wiki for user: {user_id} ===")

        for md_file in sorted(user_dir.rglob("*.md")):
            if md_file.suffix == ".lock":
                continue
            rel_path = str(md_file.relative_to(user_dir))
            content = md_file.read_text()

            supabase.table("wiki_pages").upsert({
                "user_id": user_id,
                "path": rel_path,
                "content": content,
            }, on_conflict="user_id,path").execute()

            print(f"  {rel_path} ({len(content)} chars)")
            total += 1

    return total


def migrate_articles():
    """Migrate article files into wiki_pages with path = articles/{topic}/{slug}.md."""
    if not ARTICLES_ROOT.exists():
        print("\nNo articles data found")
        return 0

    total = 0
    # Articles aren't user-scoped on disk, but article metadata in Supabase has user_id.
    # We'll look up each article file's user from the articles table.
    articles = supabase.table("articles").select("file_path, user_id").execute().data
    file_to_user = {a["file_path"]: a["user_id"] for a in articles}

    for md_file in sorted(ARTICLES_ROOT.rglob("*.md")):
        rel_path = str(md_file.relative_to(ARTICLES_ROOT.parent))  # e.g. data/articles/ai/slug.md
        # Normalize to articles/{topic}/{slug}.md
        article_path = str(md_file.relative_to(ARTICLES_ROOT))  # e.g. ai/slug.md
        wiki_path = f"articles/{article_path}"

        content = md_file.read_text()

        # Look up user from articles table, fall back to "default"
        user_id = file_to_user.get(str(md_file), file_to_user.get(rel_path, "default"))

        supabase.table("wiki_pages").upsert({
            "user_id": user_id,
            "path": wiki_path,
            "content": content,
        }, on_conflict="user_id,path").execute()

        print(f"  [{user_id}] {wiki_path} ({len(content)} chars)")
        total += 1

    return total


if __name__ == "__main__":
    wiki_count = migrate_wiki()
    article_count = migrate_articles()

    # Verify
    result = supabase.table("wiki_pages").select("user_id, path", count="exact").execute()
    print(f"\n=== Migration complete ===")
    print(f"  Wiki files migrated: {wiki_count}")
    print(f"  Article files migrated: {article_count}")
    print(f"  Total rows in wiki_pages: {result.count}")
