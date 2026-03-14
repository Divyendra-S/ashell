"""Phase 3 end-to-end test: ingest 3 new articles, then test all 7 query tools."""
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
log = logging.getLogger("test")

from kuro.memory import store
from kuro.memory.files import save_article, chunk_text, get_article, grep_articles
from kuro.memory.scraper import scrape_url

URLS = [
    "https://every.to/on-every/introducing-proof",
    "https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling",
    "https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool",
    "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
]

# ── Step 1: Ingest articles ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 1: INGESTING ARTICLES")
print("=" * 60)

for url in URLS:
    existing = store.get_article_by_url(url)
    if existing:
        print(f"  SKIP (already exists): {existing['title']}")
        continue
    try:
        print(f"  Scraping: {url}")
        data = scrape_url(url)
        title = data["title"]
        content = data["content"]
        file_path = save_article(title, content, "test")
        row = store.insert_article(url, title, file_path)
        chunks = chunk_text(content)
        store.insert_article_chunks(row["id"], chunks)
        print(f"  OK: '{title}' → {len(chunks)} chunks, file={file_path}")
    except Exception as e:
        print(f"  FAIL: {url} → {e}")

# ── Step 2: Unit-test each tool ─────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: UNIT-TESTING ALL 7 TOOLS")
print("=" * 60)

failures = []

# Tool 1: search_knowledge
print("\n--- Tool 1: search_knowledge ---")
try:
    result = store.search_knowledge_unified("prompt caching")
    print(f"  Entities: {len(result.get('entities', []))}")
    print(f"  Facts: {len(result.get('facts', []))}")
    print(f"  Article chunks: {len(result.get('article_chunks', []))}")
    if result.get("article_chunks"):
        for chunk in result["article_chunks"]:
            print(f"    → '{chunk.get('article_title', 'N/A')}' (file: {chunk.get('file_path', 'N/A')})")
    if not result.get("article_chunks"):
        failures.append("search_knowledge: no article_chunks for 'prompt caching'")
    print("  PASS")
except Exception as e:
    failures.append(f"search_knowledge: {e}")
    print(f"  FAIL: {e}")

# Tool 2: get_facts_for_entity
print("\n--- Tool 2: get_facts_for_entity ---")
try:
    # Use an entity we know exists from Phase 2
    entity = store.get_entity_by_name("Compound Engineering Camp")
    if entity:
        facts = store.get_facts_for_entity(entity["id"])
        print(f"  Entity: {entity['name']} (type={entity['entity_type']})")
        print(f"  Facts: {len(facts)}")
        for f in facts[:3]:
            print(f"    → {f['content'][:80]}...")
        print("  PASS")
    else:
        print("  SKIP: 'Compound Engineering Camp' entity not found (may not exist from Phase 2)")
except Exception as e:
    failures.append(f"get_facts_for_entity: {e}")
    print(f"  FAIL: {e}")

# Tool 3: get_relations_for_entity (enriched)
print("\n--- Tool 3: get_relations_for_entity (enriched) ---")
try:
    entity = store.get_entity_by_name("Compound Engineering Camp")
    if entity:
        rels = store.get_relations_for_entity_enriched(entity["id"])
        print(f"  Relations for '{entity['name']}': {len(rels)}")
        for r in rels[:3]:
            print(f"    → {r.get('source_name', '?')} --[{r['relation_type']}]--> {r.get('target_name', '?')}")
        print("  PASS")
    else:
        print("  SKIP: entity not found")
except Exception as e:
    failures.append(f"get_relations_for_entity_enriched: {e}")
    print(f"  FAIL: {e}")

# Tool 4: traverse_relations
print("\n--- Tool 4: traverse_relations ---")
try:
    entity = store.get_entity_by_name("Compound Engineering Camp")
    if entity:
        graph = store.traverse(entity["id"], depth=2)
        print(f"  Entities found: {len(graph['entities'])}")
        print(f"  Edges found: {len(graph['relations'])}")
        for e in graph["entities"]:
            print(f"    → {e['name']} ({e['entity_type']})")
        print("  PASS")
    else:
        print("  SKIP: entity not found")
except Exception as e:
    failures.append(f"traverse: {e}")
    print(f"  FAIL: {e}")

# Tool 5: grep_articles
print("\n--- Tool 5: grep_articles ---")
try:
    results = grep_articles("caching")
    print(f"  Matches for 'caching': {len(results)}")
    if results:
        # Show first match (truncated)
        print(f"    First match: {results[0][:120]}...")
    results2 = grep_articles("tool_use")
    print(f"  Matches for 'tool_use': {len(results2)}")
    if not results and not results2:
        failures.append("grep_articles: no results for either query")
    print("  PASS")
except Exception as e:
    failures.append(f"grep_articles: {e}")
    print(f"  FAIL: {e}")

# Tool 6: read_article
print("\n--- Tool 6: read_article ---")
try:
    articles = store.list_articles()
    if articles:
        path = articles[0]["file_path"]
        content = get_article(path)
        print(f"  Read: {path}")
        print(f"  Length: {len(content)} chars, first 100: {content[:100]}...")
        print("  PASS")
    else:
        failures.append("read_article: no articles to read")
        print("  FAIL: no articles")
except Exception as e:
    failures.append(f"read_article: {e}")
    print(f"  FAIL: {e}")

# Tool 7: list_articles
print("\n--- Tool 7: list_articles ---")
try:
    articles = store.list_articles()
    print(f"  Total articles: {len(articles)}")
    for a in articles:
        print(f"    → [{a['id']}] {a['title']} ({a['file_path']})")
    if len(articles) < 2:
        failures.append(f"list_articles: expected multiple articles, got {len(articles)}")
    print("  PASS")
except Exception as e:
    failures.append(f"list_articles: {e}")
    print(f"  FAIL: {e}")

# ── Step 3: Cross-article search test ───────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: CROSS-ARTICLE SEARCH TESTS")
print("=" * 60)

test_queries = [
    ("tool use", "Should hit Claude docs chunks"),
    ("compound engineering", "Should hit the Every article"),
    ("web fetch", "Should hit the web fetch tool doc"),
    ("caching tokens", "Should hit prompt caching doc"),
]

for query, expectation in test_queries:
    print(f"\n  Query: '{query}' — {expectation}")
    result = store.search_knowledge_unified(query)
    chunks = result.get("article_chunks", [])
    entities = result.get("entities", [])
    facts = result.get("facts", [])
    print(f"    Entities: {len(entities)}, Facts: {len(facts)}, Chunks: {len(chunks)}")
    for c in chunks[:2]:
        print(f"      → [{c.get('article_title', '?')}] {c.get('content', '')[:80]}...")

# ── Summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failures:
    print(f"FAILURES ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("ALL UNIT TESTS PASSED")
    print("=" * 60)
