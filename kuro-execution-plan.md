# Kuro — Phase-wise Execution Plan

**Database:** Supabase (PostgreSQL + pgvector)
**Starting point:** `agent.py` (311 lines) — Gemini tool-call loop, shell sandbox, file ops
**Reference architecture:** `kuro-flow.md`

---

## Phase 1: Core + Storage + Basic Capture/Retrieve (CLI) ✅

**Status:** Complete

Built the foundational knowledge capture & retrieval system:
- `kuro/config.py` — API keys, Supabase config, model selection
- `kuro/core/llm.py` — Gemini REST client + `run_agent_loop()` + embeddings
- `kuro/core/types.py` — Pydantic models (Entity, Fact, Relation, Article)
- `kuro/memory/store.py` — Supabase CRUD for entities, facts, relations + FTS
- `kuro/agents/ingest.py` — NL → extract entities + facts + relations via Gemini
- `kuro/agents/query.py` — FTS search → Gemini synthesizes answer
- `kuro/cli.py` — Interactive CLI with auto-routing (regex heuristic)

**DB:** `entities`, `facts`, `relations` tables with `tsvector` + GIN indexes

---

## Phase 2: Article Ingestion + Filesystem ✅

**Status:** Complete

- `kuro/memory/files.py` — Save articles to `data/articles/<topic>/`, chunking, grep
- `kuro/memory/scraper.py` — URL scraping with httpx + BeautifulSoup + markdownify
- Extended `ingest.py` with `scrape_url` and `save_article` tools
- Article chunking (~500 words) + Gemini embeddings (768-dim)

**DB:** `articles`, `article_chunks` tables

---

## Phase 3: Search Interface + Graph Traversal ✅

**Status:** Complete

- Rewrote `query.py` — agent gets search tools, builds its own context
- `store.py` extended with `traverse()` BFS, `get_relations_for_entity_enriched()`
- 6 tools: `get_facts_for_entity`, `get_relations_for_entity`, `traverse_relations`, `grep_articles`, `read_article`, `list_articles`
- Progressive disclosure: broad search → drill into entity → load full article

---

## Phase 4: Semantic Search + Hybrid Retrieval ✅

**Status:** Complete

- `kuro/core/retrieval.py` — query rewriting, hybrid retrieve (FTS + vector), RRF merge
- Embeddings via Gemini `gemini-embedding-2-preview` (768-dim)
- `match_chunks` RPC for pgvector cosine similarity search
- `search_knowledge` RPC for unified FTS across entities, facts, article_chunks
- Rank reciprocal fusion (RRF) to merge and deduplicate results

---

## Phase 5: Web UI + API ✅

**Status:** Complete

- `kuro/api.py` — FastAPI with `/api/chat`, `/api/ingest`, `/api/query`, `/api/entities`
- `frontend/` — Next.js 16 + Tailwind CSS 4 chat interface
- Auto-classification (query vs ingest), mode badges, suggestion buttons
- API proxy via Next.js rewrites

---

## Phase 6: Per-User Memory & Full Multi-Tenancy ✅

**Status:** Complete

- Added `user_id` column to all 5 tables (entities, facts, relations, articles, article_chunks)
- Created `user_memories` table (preference, context, instruction types)
- Updated all RPCs (`search_knowledge`, `match_chunks`) with `p_user_id` filter
- Updated `store.py` — `user_id` param on all functions + 4 memory CRUD functions
- Updated `query.py` — 3 memory tools (save/list/delete), auto-detect prompt, closure pattern
- Updated `ingest.py` — closure pattern with `user_id` passthrough
- Updated `retrieval.py` — `user_id` passthrough to FTS + vector search
- Updated `api.py` — `user_id` in all request models
- Updated `cli.py` — username prompt on startup
- Frontend: login page (`/login`), auth context (localStorage), logout button, user isolation

**DB migrations:** 3 applied (add user_id columns, create user_memories, update RPCs)

---

## Phase 7: Agent Skills

**Status:** Not started

**Goal:** Composable, reusable skill definitions that give the agent specialized multi-step workflows. Skills go beyond single tools — they define HOW to approach a type of task.

See detailed plan below.

---

## Summary

| Phase | What | Status |
|-------|------|--------|
| **1** | Core + Storage + CLI | ✅ Done |
| **2** | Article Ingestion + Filesystem | ✅ Done |
| **3** | Search Interface + Graph Traversal | ✅ Done |
| **4** | Semantic Search + Hybrid Retrieval | ✅ Done |
| **5** | Web UI + API | ✅ Done |
| **6** | Per-User Memory & Multi-Tenancy | ✅ Done |
| **7** | Agent Skills | ⬜ Next |

---

## Current Architecture

```
frontend/ (Next.js 16)
  app/login/page.tsx    → username login
  app/page.tsx          → chat UI (auth-gated)
  lib/api.ts            → API client (sends user_id)
  lib/user.tsx          → UserProvider (localStorage)

kuro/
  config.py             → env vars, model config
  api.py                → FastAPI endpoints (user_id in all requests)
  cli.py                → CLI with username prompt

  core/
    llm.py              → Gemini client + agent loop + embeddings
    retrieval.py        → query rewriting, hybrid retrieve, RRF merge
    types.py            → Pydantic models

  agents/
    ingest.py           → extract entities/facts/relations + scrape URLs
    query.py            → knowledge retrieval + user memory tools

  memory/
    store.py            → Supabase CRUD (all user-scoped) + user memory CRUD
    files.py            → article file storage + chunking + grep
    scraper.py          → URL → markdown

DB (Supabase):
  entities, facts, relations, articles, article_chunks (all with user_id)
  user_memories (per-user preferences, context, instructions)
  RPCs: search_knowledge(p_user_id), match_chunks(p_user_id)
```
