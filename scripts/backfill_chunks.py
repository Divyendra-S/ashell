"""One-time backfill: chunk the already-ingested article into article_chunks."""
from kuro.memory import store
from kuro.memory.files import get_article, chunk_text

article = store.get_article_by_url("https://every.to/source-code/compound-engineering-camp-every-step-from-scratch")
if not article:
    print("Article not found — nothing to backfill.")
else:
    content = get_article(article["file_path"])
    chunks = chunk_text(content)
    store.insert_article_chunks(article["id"], chunks)
    print(f"Backfilled {len(chunks)} chunks for article '{article['title']}' (id={article['id']})")
