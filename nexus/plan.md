# Nexus — Knowledge Base with Graph RAG

## What We're Building

A drop-in replacement for Kuro's backend — same frontend, same API contract, but powered by **Neo4j** instead of Supabase. All knowledge (concepts, articles, memories, profile) lives in a graph database, enabling real graph traversal and relationship-aware retrieval.

**Stack**: Python (FastAPI) + Google Gemini + Neo4j

**Frontend**: We reuse the existing Next.js frontend as-is — no new frontend code. The frontend talks to the backend via REST + SSE APIs. We just need to match the same API contract (endpoints + response shapes) so it works without any changes.

---

## Architecture

```
Existing Next.js Frontend (Chat | Dashboard | Progress | Voice)
        │ SSE + REST (same API contract)
        ▼
FastAPI Backend (nexus/)
  ┌─────────────────────────────────┐
  │         Unified Agent           │ ← agent loop + tools (same as Kuro)
  │   (chat, ingest, query, etc.)  │
  └──────────┬──────────────────────┘
             │
     Graph Operations Layer
             │
          Neo4j DB
```

No multi-agent orchestrator. One unified agent with tools, same as Kuro.

---

## Neo4j Setup

- **Neo4j Desktop** (local)
- Instance: `nexus`, version 2026.03.1
- Browser: `http://localhost:7474`
- Bolt: `bolt://localhost:7687`

### `.env`
```
GEMINI_API_KEY=<key>
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=nexus123
```

---

## Graph Schema

```cypher
// Core knowledge nodes
(:Concept {slug, name, summary, content, created_at, updated_at})
(:Article {id, title, url, file_path, summary, is_read, created_at})
(:Memory  {id, content, updated_at})          // user memories
(:Profile {id, content, updated_at})          // user profile
(:Chunk   {id, text, source_type, source_id}) // text chunks for RAG

// Relationships
(c1:Concept)-[:LINKS_TO]->(c2:Concept)       // backlinks between concepts
(c:Concept)-[:EXTRACTED_FROM]->(a:Article)    // concept came from article
(chunk:Chunk)-[:CHUNK_OF]->(source)           // chunk belongs to concept/article
(:Concept)-[:HAS_TAG]->(t:Tag)               // optional tagging

// Entity extraction (Graph RAG enhancement)
(:Entity {name, type, description})           // extracted entities (Person, Tech, Org, etc.)
(:Entity)-[:RELATES_TO {context}]->(:Entity)  // relationships between entities
(:Entity)-[:MENTIONED_IN]->(:Chunk)           // entity appears in chunk
```

---

## API Contract (must match frontend)

These endpoints must return the exact same response shapes as Kuro.

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/chat` | Chat (full response) |
| POST | `/api/chat/stream` | Chat with SSE streaming |
| GET | `/api/skills` | List available skills |
| GET | `/api/graph?user_id=` | Knowledge graph for visualization |
| GET | `/api/concept/{slug}?user_id=` | Concept detail with backlinks |
| GET | `/api/stats?user_id=` | KB stats |
| GET | `/api/stats/growth?user_id=&days=` | Daily growth data |
| GET | `/api/articles?user_id=` | List articles |
| GET | `/api/check-article?url=&user_id=` | Check if URL saved |
| POST | `/api/ingest-article` | Save + ingest article |
| GET | `/api/progress/timeline?user_id=&days=` | Timeline entries |
| GET | `/api/progress/streak?user_id=` | Streak data |
| PATCH | `/api/goals/{entry_id}/complete?user_id=` | Mark goal done |
| GET | `/api/digest?user_id=` | Daily digest |
| POST | `/api/notes` | Append note to concept |
| POST | `/api/offer` | WebRTC voice (later) |
| PATCH | `/api/offer` | WebRTC ICE candidates (later) |
| GET | `/api/voice/sessions?user_id=` | Voice sessions (later) |

### Response Shapes (from frontend types)

```typescript
// GET /api/graph
{ entities: [{id, name, entity_type, summary, fact_count}], relations: [{id, source_id, target_id, relation_type, context, source_name, target_name}] }

// GET /api/concept/{slug}
{ slug, name, summary, content, backlinks: [{name, slug}], incoming_backlinks: [{name, slug}], notes, created_at, updated_at }

// GET /api/stats
{ concept_count, backlink_count, article_count, new_concepts_7d, new_articles_7d, health_score }

// GET /api/stats/growth
{ data: [{date, concepts, articles}] }

// GET /api/articles
{ articles: [{id, title, url, file_path, is_read, read_at, created_at}] }

// GET /api/progress/timeline
{ timeline: [{type, date, data}] }

// GET /api/progress/streak
{ current, longest, total_active_days }

// GET /api/digest
{ streak, recent_concepts, recent_articles, pending_goals, study_suggestion, kb_suggestions }

// SSE events from /api/chat/stream
event: step  → {"tool", "args", "status": "running"|"done"}
event: delta → {"text"}
event: done  → {"skill"}
event: error → {"message"}
```

---

## Project Structure

```
nexus/
├── plan.md
├── pyproject.toml
├── .env
│
├── core/
│   ├── __init__.py
│   ├── config.py             # env vars (GEMINI_API_KEY, NEO4J_*)
│   ├── llm.py                # call_gemini(), stream_gemini(), agent loops
│   └── scraper.py            # URL → markdown (trafilatura)
│
├── graph/
│   ├── __init__.py
│   ├── driver.py             # Neo4j driver, run_query() helper
│   ├── wiki.py               # concept CRUD, backlinks, wiki index, stats
│   ├── articles.py           # article CRUD, summaries
│   ├── memories.py           # profile + memories CRUD
│   ├── progress.py           # timeline, streaks, goals, digest
│   └── search.py             # full-text + graph traversal queries
│
├── agents/
│   ├── __init__.py
│   └── unified.py            # tools, executor, system prompt, chat()
│
├── skills/                   # skill definitions (YAML or dicts)
│   └── __init__.py
│
├── api.py                    # FastAPI routes (mirrors Kuro's)
└── main.py                   # uvicorn entry
```

---

## Agent Tools (same as Kuro)

| Tool | Description |
|------|-------------|
| `read_wiki_page` | Read a concept page by path |
| `write_wiki_page` | Write/update a concept page |
| `list_wiki_pages` | List all concept pages |
| `grep_wiki` | Search concepts by keyword |
| `search_knowledge` | Full-text search across concepts + articles |
| `update_memories` | Update user memories |
| `update_wiki_index` | Update the wiki index |
| `update_wiki_recent` | Update recent changes log |
| `scrape_url` | Fetch URL → markdown |
| `save_article` | Save article to DB |
| `grep_articles` | Search articles by keyword |
| `read_article` | Read full article content |
| `list_articles` | List saved articles |
| `update_profile` | Update user profile |

### Graph RAG Enhancement Tools (new)

| Tool | Description |
|------|-------------|
| `search_graph` | Traverse graph to find related entities/concepts |
| `find_connections` | Find paths between two concepts/entities |

---

## What Changes vs Kuro

| Aspect | Kuro | Nexus |
|--------|------|-------|
| Storage | Supabase (Postgres + file storage) | Neo4j |
| Concepts | Markdown files in Supabase storage | `:Concept` nodes in Neo4j |
| Backlinks | Parsed from `[[wiki-links]]` in markdown | `:LINKS_TO` relationships |
| Articles | `articles` table in Supabase | `:Article` nodes |
| Memories | Markdown file in Supabase storage | `:Memory` node |
| Profile | Markdown file in Supabase storage | `:Profile` node |
| Graph view | Derived from wiki backlinks at query time | Native graph queries |
| Search | Text search across files | Neo4j full-text index + graph traversal |
| RAG | Index lookup + keyword fallback | Graph traversal + entity relationships |

## What Stays the Same

- Frontend (zero changes)
- API contract (same endpoints, same response shapes)
- Agent loop pattern (functional, closures, guards)
- LLM provider (Gemini)
- Tool definitions (declarative JSON)
- SSE streaming format
- Skills system
- System prompt structure

---

## Dependencies

```toml
[project]
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "google-genai",
    "neo4j",
    "python-multipart",
    "pydantic",
    "pydantic-settings",
    "trafilatura",          # URL scraping
    "httpx",
]
```

---

## Implementation Phases

### Phase 1: Core + Neo4j Foundation ✅
- [x] `core/config.py` — load env vars
- [x] `core/llm.py` — copy from Kuro (call_gemini, stream_gemini, agent loops, embeddings)
- [x] `graph/driver.py` — Neo4j driver, `run_query()`, `run_write()`
- [x] `graph/wiki.py` — concept CRUD (create, read, update, list, search), backlinks, stats, growth
- [x] `graph/articles.py` — article CRUD (insert, list, get_by_url, search)
- [x] `graph/memories.py` — profile + memories (read, write)
- [x] Schema init — create indexes + constraints on startup
- [ ] **Test**: create a concept, read it back, verify in Neo4j browser

### Phase 2: Agent + Chat ✅
- [x] `agents/unified.py` — system prompt, tool definitions, executor factory, chat(), chat_streaming()
- [x] `core/scraper.py` — URL → markdown
- [x] `skills/__init__.py` — skill loading (copy structure from Kuro)
- [x] `api.py` — all REST + SSE endpoints matching Kuro's contract
- [x] `main.py` — uvicorn entry
- [ ] **Test**: start backend, point frontend at it, send a chat message, verify streaming works

### Phase 3: Full Feature Parity ✅
- [x] `graph/progress.py` — timeline, streaks, goals, digest
- [x] Search — full-text search via Neo4j fulltext indexes (built into wiki.py)
- [x] Wiki index + recent changes (stored as Concept nodes with special slugs)
- [x] Article ingestion with auto-extract
- [x] Notes endpoint
- [ ] **Test**: all frontend pages work (dashboard, progress, entity detail)

### Phase 4: Graph RAG Enhancement
- [ ] Entity extraction on ingest (LLM-based)
- [ ] `search_graph` tool — multi-hop graph traversal for answers
- [ ] `find_connections` tool — shortest path between concepts
- [ ] Hybrid retrieval: graph traversal + text chunk matching
- [ ] **Test**: ask questions that require connecting information across multiple documents

### Phase 5: Voice + Polish
- [ ] Voice agent integration (Pipecat WebRTC)
- [ ] Error handling, edge cases
- [ ] Performance tuning (Neo4j query optimization)

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph DB | Neo4j | Native relationships, Cypher, vector indexes |
| No multi-agent | Single unified agent | Same as Kuro — simpler, proven |
| Same API contract | Exact match | Zero frontend changes |
| Concept storage | Full content in Neo4j node properties | No external file storage needed |
| Backlinks | Real graph edges | No parsing needed, native traversal |
| Pattern | Functional agent loop | No classes — closures, dicts, pure functions |
