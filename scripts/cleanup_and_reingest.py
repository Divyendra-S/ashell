"""Clean up bad articles and re-ingest from fixed files on disk."""
import sys
sys.path.insert(0, ".")

from kuro.memory import store
from kuro.memory.files import chunk_text, get_article

URLS = [
    "https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling",
    "https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool",
    "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
]

# Step 1: Delete old bad articles from DB
for url in URLS:
    existing = store.get_article_by_url(url)
    if existing:
        aid = existing["id"]
        print(f"Deleting old article id={aid}: {existing['title']}")
        store.supabase.table("article_chunks").delete().eq("article_id", aid).execute()
        store.supabase.table("articles").delete().eq("id", aid).execute()
    else:
        print(f"Not found in DB: {url}")

# Step 2: Insert from new files (already written to claude-docs/)
NEW_DOCS = [
    {
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling",
        "title": "Programmatic tool calling - Claude API Docs",
        "file_path": "data/articles/claude-docs/programmatic-tool-calling.md",
    },
    {
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool",
        "title": "Web fetch tool - Claude API Docs",
        "file_path": "data/articles/claude-docs/web-fetch-tool.md",
    },
    {
        "url": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
        "title": "Prompt caching - Claude API Docs",
        "file_path": "data/articles/claude-docs/prompt-caching.md",
    },
]

print("\nRe-ingesting from real content files...")
for doc in NEW_DOCS:
    try:
        content = get_article(doc["file_path"])
        if len(content) < 200:
            print(f"  SKIP (content too short, {len(content)} chars): {doc['title']}")
            continue
        row = store.insert_article(doc["url"], doc["title"], doc["file_path"])
        chunks = chunk_text(content)
        store.insert_article_chunks(row["id"], chunks)
        print(f"  OK: '{doc['title']}' → {len(chunks)} chunks ({len(content)} chars)")
    except Exception as e:
        print(f"  FAIL: {doc['title']} → {e}")
