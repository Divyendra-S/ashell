import logging
from datetime import datetime, timezone

from kuro.memory.store import supabase

log = logging.getLogger("kuro.checkin_store")


def create_checkin_session(user_id: str = "default") -> dict:
    result = supabase.table("checkin_sessions").insert({
        "user_id": user_id,
    }).execute()
    return result.data[0]


def end_checkin_session(session_id: int, summary: str, mood: str | None = None) -> dict:
    payload = {
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
    if mood:
        payload["mood"] = mood
    result = supabase.table("checkin_sessions").update(payload).eq("id", session_id).execute()
    return result.data[0]


def add_checkin_entry(
    session_id: int, user_id: str, entry_type: str, content: str, metadata: dict | None = None,
) -> dict:
    result = supabase.table("checkin_entries").insert({
        "session_id": session_id,
        "user_id": user_id,
        "entry_type": entry_type,
        "content": content,
        "metadata": metadata or {},
    }).execute()
    return result.data[0]


def get_session_entries(session_id: int) -> list[dict]:
    result = supabase.table("checkin_entries").select("*").eq("session_id", session_id).order("created_at").execute()
    return result.data


def get_recent_sessions(user_id: str = "default", limit: int = 7) -> list[dict]:
    result = (
        supabase.table("checkin_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    sessions = result.data
    for s in sessions:
        s["entries"] = get_session_entries(s["id"])
    return sessions


def get_last_session(user_id: str = "default") -> dict | None:
    result = (
        supabase.table("checkin_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    session = result.data[0]
    session["entries"] = get_session_entries(session["id"])
    return session


def get_entries_by_type(user_id: str = "default", entry_type: str = "goal", limit: int = 10) -> list[dict]:
    result = (
        supabase.table("checkin_entries")
        .select("*")
        .eq("user_id", user_id)
        .eq("entry_type", entry_type)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def mark_article_read(article_id: int) -> dict:
    result = supabase.table("articles").update({
        "is_read": True,
        "read_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", article_id).execute()
    return result.data[0] if result.data else {}


def search_articles_by_title(query: str, user_id: str = "default") -> list[dict]:
    result = (
        supabase.table("articles")
        .select("id, title, url, is_read")
        .eq("user_id", user_id)
        .ilike("title", f"%{query}%")
        .limit(5)
        .execute()
    )
    return result.data
