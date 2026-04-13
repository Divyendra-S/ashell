import logging
from datetime import datetime, timezone

from nexus.graph.driver import run_query, run_write

log = logging.getLogger("nexus.memories")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_profile(user_id: str) -> str:
    rows = run_query(
        "MATCH (p:Profile {user_id: $uid}) RETURN p.content AS content",
        uid=user_id,
    )
    return rows[0]["content"] if rows else ""


def write_profile(user_id: str, content: str) -> str:
    now = _now_iso()
    run_write(
        """MERGE (p:Profile {user_id: $uid})
        ON CREATE SET p.id = $uid, p.created_at = $now
        SET p.content = $content, p.updated_at = $now""",
        uid=user_id, content=content, now=now,
    )
    return "user/profile.md"


def read_memories(user_id: str) -> str:
    rows = run_query(
        "MATCH (m:Memory {user_id: $uid}) RETURN m.content AS content",
        uid=user_id,
    )
    return rows[0]["content"] if rows else ""


def write_memories(user_id: str, content: str) -> str:
    now = _now_iso()
    run_write(
        """MERGE (m:Memory {user_id: $uid})
        ON CREATE SET m.id = $uid, m.created_at = $now
        SET m.content = $content, m.updated_at = $now""",
        uid=user_id, content=content, now=now,
    )
    return "user/memories.md"
