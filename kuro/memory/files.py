"""Article file storage — Supabase wiki_pages backend.

Articles are stored in wiki_pages with path = 'articles/{topic}/{slug}.md'.
"""

import re
from datetime import datetime, timezone

from kuro.memory.store import supabase


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-"))


def save_article(title: str, content: str, topic: str = "general", user_id: str = "default") -> str:
    """Save article content to wiki_pages. Returns the path."""
    slug = slugify(title)
    path = f"articles/{topic}/{slug}.md"
    full_content = f"# {title}\n\n{content}"

    supabase.table("wiki_pages").upsert({
        "user_id": user_id,
        "path": path,
        "content": full_content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,path").execute()

    return path


def get_article(file_path: str, user_id: str = "default") -> str:
    """Read article content from wiki_pages."""
    # Normalize path — strip leading data/articles/ if present
    path = file_path
    if "data/articles/" in path:
        path = "articles/" + path.split("data/articles/", 1)[1]
    elif not path.startswith("articles/"):
        path = f"articles/{path}"

    result = (
        supabase.table("wiki_pages")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", path)
        .execute()
    )
    if not result.data:
        raise FileNotFoundError(f"Article not found: {path}")
    return result.data[0]["content"]


def list_topics(user_id: str = "default") -> list[str]:
    """List distinct article topics."""
    result = (
        supabase.table("wiki_pages")
        .select("path")
        .eq("user_id", user_id)
        .like("path", "articles/%")
        .execute()
    )
    topics = set()
    for row in result.data:
        parts = row["path"].split("/")
        if len(parts) >= 2:
            topics.add(parts[1])
    return sorted(topics)


def grep_articles(pattern: str, max_results: int = 10, user_id: str = "default") -> list[str]:
    """Search across all article pages using FTS with OR logic."""
    words = re.findall(r'\w+', pattern)
    if not words:
        return []
    # Use OR logic so multi-word queries find articles about any term
    tsquery = " | ".join(words)

    try:
        # NOTE: .limit() must come before .text_search() in supabase-py
        result = (
            supabase.table("wiki_pages")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "articles/%")
            .limit(max_results)
            .text_search("fts", tsquery)
            .execute()
        )
    except Exception:
        result = (
            supabase.table("wiki_pages")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "articles/%")
            .ilike("content", f"%{pattern}%")
            .limit(max_results)
            .execute()
        )

    lower_words = [w.lower() for w in words]
    matches = []
    for row in result.data:
        content = row["content"]
        lower_content = content.lower()
        # Find best matching region
        best_pos = 0
        best_density = 0
        for i in range(0, len(lower_content), 50):
            window = lower_content[i:i + 400]
            density = sum(window.count(w) for w in lower_words)
            if density > best_density:
                best_density = density
                best_pos = i

        start = max(0, best_pos)
        end = min(len(content), start + 400)
        snippet = content[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        matches.append(f"{row['path']}:\n{snippet}")

    return matches


def chunk_text(text: str, max_words: int = 500) -> list[str]:
    """Split text into ~500-word chunks at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks, current, current_words = [], [], 0
    for para in paragraphs:
        words = len(para.split())
        if current_words + words > max_words and current:
            chunks.append("\n\n".join(current))
            current, current_words = [para], words
        else:
            current.append(para)
            current_words += words
    if current:
        chunks.append("\n\n".join(current))
    return chunks
