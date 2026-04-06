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


def complete_goal(entry_id: int, user_id: str = "default") -> dict | None:
    """Mark a checkin entry (goal) as completed."""
    result = (
        supabase.table("checkin_entries")
        .update({"completed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_pending_goals(user_id: str = "default", limit: int = 10) -> list[dict]:
    """Get goals that haven't been completed."""
    result = (
        supabase.table("checkin_entries")
        .select("*")
        .eq("user_id", user_id)
        .eq("entry_type", "goal")
        .is_("completed_at", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_timeline(user_id: str = "default", days: int = 30) -> list[dict]:
    """Aggregate activity timeline from all sources."""
    from datetime import timedelta
    from collections import defaultdict

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    timeline = []

    # Check-in sessions
    sessions = (
        supabase.table("checkin_sessions")
        .select("*")
        .eq("user_id", user_id)
        .gte("started_at", cutoff)
        .order("started_at", desc=True)
        .execute()
    ).data
    for s in sessions:
        s["entries"] = get_session_entries(s["id"])
        timeline.append({
            "type": "checkin",
            "date": s["started_at"],
            "data": {"summary": s.get("summary", ""), "mood": s.get("mood"), "entry_count": len(s["entries"])},
        })

    # Articles ingested
    articles = (
        supabase.table("articles")
        .select("id, title, url, created_at")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .execute()
    ).data
    for a in articles:
        timeline.append({
            "type": "article",
            "date": a["created_at"],
            "data": {"title": a["title"], "url": a.get("url")},
        })

    # Wiki concept pages created
    concept_rows = (
        supabase.table("wiki_pages")
        .select("path, created_at")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .execute()
    ).data
    for row in concept_rows:
        name = row["path"].split("/")[-1].replace(".md", "").replace("-", " ").title()
        timeline.append({
            "type": "concept",
            "date": row["created_at"],
            "data": {"name": name},
        })

    # Goals set/completed
    goals = (
        supabase.table("checkin_entries")
        .select("*")
        .eq("user_id", user_id)
        .eq("entry_type", "goal")
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .execute()
    ).data
    for g in goals:
        timeline.append({
            "type": "goal_set",
            "date": g["created_at"],
            "data": {"content": g["content"], "id": g["id"], "completed_at": g.get("completed_at")},
        })

    # Sort by date descending
    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline


def get_streak(user_id: str = "default") -> dict:
    """Calculate current consecutive-day activity streak."""
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()

    # Collect all activity dates
    activity_dates = set()

    sessions = supabase.table("checkin_sessions").select("started_at").eq("user_id", user_id).execute().data
    for s in sessions:
        activity_dates.add(s["started_at"][:10])

    articles = supabase.table("articles").select("created_at").eq("user_id", user_id).execute().data
    for a in articles:
        activity_dates.add(a["created_at"][:10])

    concept_rows = supabase.table("wiki_pages").select("created_at").eq("user_id", user_id).like("path", "concepts/%").execute().data
    for row in concept_rows:
        activity_dates.add(row["created_at"][:10])

    # Calculate streak
    streak = 0
    check_date = today
    while check_date.isoformat() in activity_dates:
        streak += 1
        check_date -= timedelta(days=1)

    # If no activity today, check if yesterday started the streak
    if streak == 0:
        check_date = today - timedelta(days=1)
        while check_date.isoformat() in activity_dates:
            streak += 1
            check_date -= timedelta(days=1)

    # Longest streak
    longest = 0
    if activity_dates:
        sorted_dates = sorted(activity_dates)
        current_run = 1
        for i in range(1, len(sorted_dates)):
            prev = datetime.fromisoformat(sorted_dates[i - 1]).date()
            curr = datetime.fromisoformat(sorted_dates[i]).date()
            if (curr - prev).days == 1:
                current_run += 1
            else:
                longest = max(longest, current_run)
                current_run = 1
        longest = max(longest, current_run)

    return {"current": streak, "longest": longest, "total_active_days": len(activity_dates)}


def get_digest(user_id: str = "default") -> dict:
    """Build a daily digest from DB queries (no LLM call)."""
    from datetime import timedelta

    cutoff_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # Recent concept pages
    recent_concept_rows = (
        supabase.table("wiki_pages")
        .select("path")
        .eq("user_id", user_id)
        .like("path", "concepts/%")
        .gte("created_at", cutoff_48h)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    ).data
    recent_concepts = [
        {"name": row["path"].split("/")[-1].replace(".md", "").replace("-", " ").title()}
        for row in recent_concept_rows
    ]

    recent_articles = (
        supabase.table("articles")
        .select("title, url")
        .eq("user_id", user_id)
        .gte("created_at", cutoff_48h)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    ).data

    # Pending goals
    pending_goals = get_pending_goals(user_id, limit=5)

    # Streak
    streak_data = get_streak(user_id)

    # Study suggestions (try to load, gracefully fail)
    study_suggestion = None
    try:
        from kuro.skills.study.scripts.analyze_progress import analyze_progress
        progress = analyze_progress(user_id)
        if progress.get("weakest_topics"):
            study_suggestion = progress["weakest_topics"][0]
    except Exception:
        pass

    # KB health suggestions
    kb_suggestions = []
    try:
        from kuro.skills.review.scripts.kb_health import kb_health_report
        report = kb_health_report(user_id)
        kb_suggestions = report.get("suggestions", [])[:2]
    except Exception:
        pass

    return {
        "streak": streak_data,
        "recent_concepts": recent_concepts,
        "recent_articles": recent_articles,
        "pending_goals": [{"id": g["id"], "content": g["content"], "created_at": g["created_at"]} for g in pending_goals],
        "study_suggestion": study_suggestion,
        "kb_suggestions": kb_suggestions,
    }
