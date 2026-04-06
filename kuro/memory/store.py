"""Supabase storage layer — articles and metadata only.

Knowledge (concepts, facts, relations) has moved to wiki markdown files.
User memories have moved to wiki/user/memories.md.
This module retains only article metadata operations needed by the dashboard.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client

from kuro.config import SUPABASE_URL, SUPABASE_KEY

log = logging.getLogger("kuro.store")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- Articles ---


def insert_article(url: str, title: str, file_path: str, user_id: str = "default", summary: str = "") -> dict:
    return supabase.table("articles").insert({
        "url": url, "title": title, "file_path": file_path, "user_id": user_id, "summary": summary,
    }).execute().data[0]


def get_article_by_url(url: str) -> dict | None:
    res = supabase.table("articles").select("*").eq("url", url).execute()
    return res.data[0] if res.data else None


def list_articles(user_id: str = "default") -> list[dict]:
    result = supabase.table("articles").select("id, title, url, file_path, summary").eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data


def list_articles_enhanced(user_id: str = "default") -> list[dict]:
    """Articles with chunk count and read status."""
    articles = supabase.table("articles").select("id, title, url, file_path, is_read, read_at, created_at").eq("user_id", user_id).order("created_at", desc=True).execute().data
    return articles


# --- User Profile ---
# Profile is now stored in wiki/user/profile.md but these functions remain
# for backward compatibility during transition.


def read_user_profile(user_id: str) -> str:
    """Read the user's markdown profile from wiki."""
    from kuro.memory.wiki import read_page
    return read_page(user_id, "user/profile.md") or ""


def update_user_profile(user_id: str, content: str) -> str:
    """Write the user's markdown profile to wiki."""
    from kuro.memory.wiki import write_page
    path = write_page(user_id, "user/profile.md", content)
    return path
