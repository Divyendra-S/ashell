"""Re-ingest Claude docs with real content (WebFetch got full content, scraper got 'Loading...')."""
import json
import sys

sys.path.insert(0, ".")

from kuro.memory import store
from kuro.memory.files import save_article, chunk_text

DOCS = [
    {
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling",
        "title": "Programmatic tool calling - Claude API Docs",
        "topic": "claude-docs",
    },
    {
        "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool",
        "title": "Web fetch tool - Claude API Docs",
        "topic": "claude-docs",
    },
    {
        "url": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
        "title": "Prompt caching - Claude API Docs",
        "topic": "claude-docs",
    },
]

# Read the real content from WebFetch results saved to disk
CONTENT_FILES = {
    "programmatic-tool-calling": "/Users/divyendra/.claude/projects/-Users-divyendra-ashell/f85b72c7-49a2-47f9-a55a-fe88f5af8313/tool-results/toolu_01HR3pGPW6d973KQ5kxZ49Aw.txt",
}

for doc in DOCS:
    url = doc["url"]
    print(f"\nProcessing: {doc['title']}")

    # Delete old article + chunks from DB
    existing = store.get_article_by_url(url)
    if existing:
        aid = existing["id"]
        print(f"  Deleting old article id={aid} and its chunks...")
        store.supabase.table("article_chunks").delete().eq("article_id", aid).execute()
        store.supabase.table("articles").delete().eq("id", aid).execute()

print("\nOld records cleaned up. Now re-ingesting from content files...")
