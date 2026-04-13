import logging
import uuid
from datetime import datetime, timezone

from nexus.graph.driver import run_query, run_write

log = logging.getLogger("nexus.articles")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_article(url: str, title: str, file_path: str, user_id: str = "default", summary: str = "") -> dict:
    article_id = str(uuid.uuid4())[:8]
    now = _now_iso()
    rows = run_write(
        """CREATE (a:Article {id: $id, url: $url, title: $title, file_path: $file_path,
        summary: $summary, content: '', user_id: $uid, is_read: false,
        created_at: $now, updated_at: $now})
        RETURN a.id AS id, a.title AS title, a.file_path AS file_path""",
        id=article_id, url=url, title=title, file_path=file_path,
        summary=summary, uid=user_id, now=now,
    )
    return rows[0] if rows else {"id": article_id, "title": title, "file_path": file_path}


def save_article_content(article_id: str, content: str):
    run_write(
        "MATCH (a:Article {id: $id}) SET a.content = $content, a.updated_at = $now",
        id=article_id, content=content, now=_now_iso(),
    )


def get_article_by_url(url: str) -> dict | None:
    rows = run_query(
        "MATCH (a:Article {url: $url}) RETURN a {.*} AS article",
        url=url,
    )
    if not rows:
        return None
    return rows[0]["article"]


def list_articles(user_id: str = "default") -> list[dict]:
    rows = run_query(
        """MATCH (a:Article {user_id: $uid})
        RETURN a.id AS id, a.title AS title, a.url AS url,
               a.file_path AS file_path, a.summary AS summary
        ORDER BY a.created_at DESC""",
        uid=user_id,
    )
    return rows


def list_articles_enhanced(user_id: str = "default") -> list[dict]:
    rows = run_query(
        """MATCH (a:Article {user_id: $uid})
        RETURN a.id AS id, a.title AS title, a.url AS url,
               a.file_path AS file_path, a.is_read AS is_read,
               a.read_at AS read_at, a.created_at AS created_at
        ORDER BY a.created_at DESC""",
        uid=user_id,
    )
    return rows


def get_article_content(file_path: str, user_id: str = "default") -> str | None:
    rows = run_query(
        "MATCH (a:Article {file_path: $fp, user_id: $uid}) RETURN a.content AS content",
        fp=file_path, uid=user_id,
    )
    return rows[0]["content"] if rows else None


def count_articles(user_id: str = "default") -> int:
    rows = run_query(
        "MATCH (a:Article {user_id: $uid}) RETURN count(a) AS cnt",
        uid=user_id,
    )
    return rows[0]["cnt"] if rows else 0


def count_new_articles(user_id: str, cutoff: str) -> int:
    rows = run_query(
        "MATCH (a:Article {user_id: $uid}) WHERE a.created_at >= $cutoff RETURN count(a) AS cnt",
        uid=user_id, cutoff=cutoff,
    )
    return rows[0]["cnt"] if rows else 0


def grep_articles(pattern: str, max_results: int = 10, user_id: str = "default") -> list[dict]:
    try:
        words = pattern.split()
        query_str = " OR ".join(words)
        rows = run_query(
            """CALL db.index.fulltext.queryNodes('article_fts', $query)
            YIELD node, score
            WHERE node.user_id = $uid
            RETURN node.id AS id, node.title AS title, node.file_path AS file_path, score
            ORDER BY score DESC LIMIT $limit""",
            query=query_str, uid=user_id, limit=max_results,
        )
    except Exception:
        rows = run_query(
            """MATCH (a:Article {user_id: $uid})
            WHERE toLower(a.content) CONTAINS toLower($pattern)
            RETURN a.id AS id, a.title AS title, a.file_path AS file_path
            LIMIT $limit""",
            pattern=pattern, uid=user_id, limit=max_results,
        )
    return rows
