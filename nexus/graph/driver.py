import logging

from neo4j import GraphDatabase

from nexus.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

log = logging.getLogger("nexus.graph")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def run_query(cypher: str, **params) -> list[dict]:
    with get_driver().session() as session:
        result = session.run(cypher, **params)
        return [record.data() for record in result]


def run_write(cypher: str, **params) -> list[dict]:
    with get_driver().session() as session:
        result = session.run(cypher, **params)
        return [record.data() for record in result]


def init_schema():
    constraints = [
        "CREATE CONSTRAINT concept_slug_user IF NOT EXISTS FOR (c:Concept) REQUIRE (c.slug, c.user_id) IS UNIQUE",
        "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
        "CREATE CONSTRAINT profile_id IF NOT EXISTS FOR (p:Profile) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT entity_name_user IF NOT EXISTS FOR (e:Entity) REQUIRE (e.name, e.user_id) IS UNIQUE",
    ]
    indexes = [
        "CREATE INDEX concept_user IF NOT EXISTS FOR (c:Concept) ON (c.user_id)",
        "CREATE INDEX article_user IF NOT EXISTS FOR (a:Article) ON (a.user_id)",
        "CREATE INDEX article_url IF NOT EXISTS FOR (a:Article) ON (a.url)",
        "CREATE INDEX memory_user IF NOT EXISTS FOR (m:Memory) ON (m.user_id)",
        "CREATE INDEX profile_user IF NOT EXISTS FOR (p:Profile) ON (p.user_id)",
        "CREATE FULLTEXT INDEX concept_fts IF NOT EXISTS FOR (c:Concept) ON EACH [c.name, c.content]",
        "CREATE FULLTEXT INDEX article_fts IF NOT EXISTS FOR (a:Article) ON EACH [a.title, a.content]",
    ]
    for stmt in constraints + indexes:
        try:
            run_write(stmt)
        except Exception as e:
            log.debug(f"Schema init (may already exist): {e}")
    log.info("Neo4j schema initialized")
