import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from nexus.graph.driver import run_query, run_write

log = logging.getLogger("nexus.progress")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Check-in sessions ---


def create_checkin_session(user_id: str = "default") -> dict:
    session_id = str(uuid.uuid4())[:8]
    now = _now_iso()
    rows = run_write(
        """CREATE (s:CheckinSession {id: $id, user_id: $uid, started_at: $now})
        RETURN s {.*} AS session""",
        id=session_id, uid=user_id, now=now,
    )
    return rows[0]["session"] if rows else {"id": session_id}


def end_checkin_session(session_id: str, summary: str, mood: str | None = None) -> dict:
    now = _now_iso()
    props = "s.ended_at = $now, s.summary = $summary"
    params = {"id": session_id, "now": now, "summary": summary}
    if mood:
        props += ", s.mood = $mood"
        params["mood"] = mood
    rows = run_write(
        f"MATCH (s:CheckinSession {{id: $id}}) SET {props} RETURN s {{.*}} AS session",
        **params,
    )
    return rows[0]["session"] if rows else {}


def add_checkin_entry(session_id: str, user_id: str, entry_type: str, content: str, metadata: dict | None = None) -> dict:
    entry_id = str(uuid.uuid4())[:8]
    now = _now_iso()
    rows = run_write(
        """CREATE (e:CheckinEntry {id: $id, session_id: $sid, user_id: $uid,
        entry_type: $etype, content: $content, metadata: $meta, created_at: $now})
        RETURN e {.*} AS entry""",
        id=entry_id, sid=session_id, uid=user_id,
        etype=entry_type, content=content, meta=str(metadata or {}), now=now,
    )
    return rows[0]["entry"] if rows else {"id": entry_id}


def get_session_entries(session_id: str) -> list[dict]:
    rows = run_query(
        """MATCH (e:CheckinEntry {session_id: $sid})
        RETURN e {.*} AS entry ORDER BY e.created_at""",
        sid=session_id,
    )
    return [r["entry"] for r in rows]


def get_recent_sessions(user_id: str = "default", limit: int = 7) -> list[dict]:
    rows = run_query(
        """MATCH (s:CheckinSession {user_id: $uid})
        RETURN s {.*} AS session
        ORDER BY s.started_at DESC LIMIT $limit""",
        uid=user_id, limit=limit,
    )
    sessions = [r["session"] for r in rows]
    for s in sessions:
        s["entries"] = get_session_entries(s["id"])
    return sessions


def get_last_session(user_id: str = "default") -> dict | None:
    sessions = get_recent_sessions(user_id, limit=1)
    return sessions[0] if sessions else None


def get_entries_by_type(user_id: str = "default", entry_type: str = "goal", limit: int = 10) -> list[dict]:
    rows = run_query(
        """MATCH (e:CheckinEntry {user_id: $uid, entry_type: $etype})
        RETURN e {.*} AS entry
        ORDER BY e.created_at DESC LIMIT $limit""",
        uid=user_id, etype=entry_type, limit=limit,
    )
    return [r["entry"] for r in rows]


def complete_goal(entry_id: str, user_id: str = "default") -> dict | None:
    now = _now_iso()
    rows = run_write(
        """MATCH (e:CheckinEntry {id: $id, user_id: $uid})
        SET e.completed_at = $now
        RETURN e {.*} AS entry""",
        id=entry_id, uid=user_id, now=now,
    )
    return rows[0]["entry"] if rows else None


def get_pending_goals(user_id: str = "default", limit: int = 10) -> list[dict]:
    rows = run_query(
        """MATCH (e:CheckinEntry {user_id: $uid, entry_type: 'goal'})
        WHERE e.completed_at IS NULL
        RETURN e {.*} AS entry
        ORDER BY e.created_at DESC LIMIT $limit""",
        uid=user_id, limit=limit,
    )
    return [r["entry"] for r in rows]


# --- Timeline ---


def get_timeline(user_id: str = "default", days: int = 30) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    timeline = []

    # Check-in sessions
    session_rows = run_query(
        """MATCH (s:CheckinSession {user_id: $uid})
        WHERE s.started_at >= $cutoff
        RETURN s {.*} AS session
        ORDER BY s.started_at DESC""",
        uid=user_id, cutoff=cutoff,
    )
    for r in session_rows:
        s = r["session"]
        entries = get_session_entries(s["id"])
        timeline.append({
            "type": "checkin",
            "date": s["started_at"],
            "data": {"summary": s.get("summary", ""), "mood": s.get("mood"), "entry_count": len(entries)},
        })

    # Articles
    article_rows = run_query(
        """MATCH (a:Article {user_id: $uid})
        WHERE a.created_at >= $cutoff
        RETURN a.id AS id, a.title AS title, a.url AS url, a.created_at AS created_at
        ORDER BY a.created_at DESC""",
        uid=user_id, cutoff=cutoff,
    )
    for a in article_rows:
        timeline.append({
            "type": "article",
            "date": a["created_at"],
            "data": {"title": a["title"], "url": a.get("url")},
        })

    # Concepts
    concept_rows = run_query(
        """MATCH (c:Concept {user_id: $uid})
        WHERE NOT c.slug STARTS WITH '_' AND NOT c.slug STARTS WITH 'user-'
        AND c.content <> '' AND c.created_at >= $cutoff
        RETURN c.slug AS slug, c.name AS name, c.created_at AS created_at
        ORDER BY c.created_at DESC""",
        uid=user_id, cutoff=cutoff,
    )
    for c in concept_rows:
        timeline.append({
            "type": "concept",
            "date": c["created_at"],
            "data": {"name": c["name"] or c["slug"].replace("-", " ").title()},
        })

    # Goals
    goal_rows = run_query(
        """MATCH (e:CheckinEntry {user_id: $uid, entry_type: 'goal'})
        WHERE e.created_at >= $cutoff
        RETURN e {.*} AS entry
        ORDER BY e.created_at DESC""",
        uid=user_id, cutoff=cutoff,
    )
    for r in goal_rows:
        g = r["entry"]
        timeline.append({
            "type": "goal_set",
            "date": g["created_at"],
            "data": {"content": g["content"], "id": g["id"], "completed_at": g.get("completed_at")},
        })

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline


# --- Streak ---


def get_streak(user_id: str = "default") -> dict:
    today = datetime.now(timezone.utc).date()
    activity_dates = set()

    # Collect all activity dates
    for label, field in [("CheckinSession", "started_at"), ("Article", "created_at"), ("Concept", "created_at")]:
        if label == "Concept":
            rows = run_query(
                f"""MATCH (n:{label} {{user_id: $uid}})
                WHERE NOT n.slug STARTS WITH '_' AND NOT n.slug STARTS WITH 'user-'
                AND n.content <> ''
                RETURN n.{field} AS dt""",
                uid=user_id,
            )
        else:
            rows = run_query(
                f"MATCH (n:{label} {{user_id: $uid}}) RETURN n.{field} AS dt",
                uid=user_id,
            )
        for r in rows:
            if r["dt"]:
                activity_dates.add(r["dt"][:10])

    # Current streak
    streak = 0
    check_date = today
    while check_date.isoformat() in activity_dates:
        streak += 1
        check_date -= timedelta(days=1)

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


# --- Digest ---


def get_digest(user_id: str = "default") -> dict:
    cutoff_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # Recent concepts
    concept_rows = run_query(
        """MATCH (c:Concept {user_id: $uid})
        WHERE NOT c.slug STARTS WITH '_' AND NOT c.slug STARTS WITH 'user-'
        AND c.content <> '' AND c.created_at >= $cutoff
        RETURN c.name AS name
        ORDER BY c.created_at DESC LIMIT 5""",
        uid=user_id, cutoff=cutoff_48h,
    )
    recent_concepts = [{"name": r["name"]} for r in concept_rows]

    # Recent articles
    article_rows = run_query(
        """MATCH (a:Article {user_id: $uid})
        WHERE a.created_at >= $cutoff
        RETURN a.title AS title, a.url AS url
        ORDER BY a.created_at DESC LIMIT 3""",
        uid=user_id, cutoff=cutoff_48h,
    )
    recent_articles = [{"title": r["title"], "url": r["url"]} for r in article_rows]

    pending_goals = get_pending_goals(user_id, limit=5)
    streak_data = get_streak(user_id)

    return {
        "streak": streak_data,
        "recent_concepts": recent_concepts,
        "recent_articles": recent_articles,
        "pending_goals": [{"id": g["id"], "content": g["content"], "created_at": g["created_at"]} for g in pending_goals],
        "study_suggestion": None,
        "kb_suggestions": [],
    }
