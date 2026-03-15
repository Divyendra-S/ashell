"""Embed all existing article_chunks that lack embeddings."""
from kuro.memory.store import get_chunks_without_embeddings, update_chunk_embedding
from kuro.core.llm import embed_texts


def backfill():
    chunks = get_chunks_without_embeddings()
    if not chunks:
        print("All chunks already have embeddings.")
        return
    print(f"Embedding {len(chunks)} chunks...")
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = embed_texts([c["content"] for c in batch])
        for chunk, emb in zip(batch, embeddings):
            update_chunk_embedding(chunk["id"], emb)
        print(f"  Done {i + len(batch)}/{len(chunks)}")
    print("Done.")


if __name__ == "__main__":
    backfill()
