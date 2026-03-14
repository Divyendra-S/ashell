# Kuro — Phase-wise Execution Plan

**Database:** Supabase (PostgreSQL + pgvector)
**Starting point:** `agent.py` (311 lines) — Gemini tool-call loop, shell sandbox, file ops
**Reference architecture:** `kuro-flow.md`

---

## Phase 1: Core + Storage + Basic Capture/Retrieve (CLI)

**Goal:** Tell it things → it remembers. Ask it things → it answers from memory. Persistent via Supabase.

### Files to create

| File | What | Reference |
|------|------|-----------|
| `kuro/__init__.py` | Package init | — |
| `kuro/config.py` | API keys, Supabase URL/key, model config | New |
| `kuro/core/__init__.py` | Package init | — |
| `kuro/core/llm.py` | Gemini REST client + tool-call loop | Extract from `agent.py:183-273` |
| `kuro/core/types.py` | Pydantic models (Entity, Fact, Relation) | New |
| `kuro/memory/__init__.py` | Package init | — |
| `kuro/memory/store.py` | Supabase CRUD: entities, facts, relations + full-text search | `kuro-flow.md` Phase 1 schema, adapted for PostgreSQL |
| `kuro/agents/__init__.py` | Package init | — |
| `kuro/agents/ingest.py` | NL → extract entities + facts + relations via Gemini | `kuro-flow.md` Phase 5a (Ingest Agent) |
| `kuro/agents/query.py` | Full-text search → Gemini synthesizes answer | `kuro-flow.md` Phase 5b (Query Agent), simplified for Phase 1 |
| `kuro/cli.py` | Interactive CLI with auto-routing | Inspired by `agent.py:276-311` |

### Supabase schema (Phase 1 subset)

Replaces SQLite FTS5 with PostgreSQL `tsvector` + GIN indexes.

```sql
-- Run in Supabase SQL editor

CREATE TABLE entities (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,        -- person | company | concept | project | article
    summary     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE facts (
    id         BIGSERIAL PRIMARY KEY,
    entity_id  BIGINT REFERENCES entities(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    source     TEXT DEFAULT 'user',   -- "user", article URL, "discussion"
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE relations (
    id            BIGSERIAL PRIMARY KEY,
    source_id     BIGINT REFERENCES entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,       -- works_at | interested_in | related_to | part_of
    target_id     BIGINT REFERENCES entities(id) ON DELETE CASCADE,
    context       TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Full-text search indexes (replaces SQLite FTS5)
ALTER TABLE entities ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(summary, ''))) STORED;
CREATE INDEX idx_entities_fts ON entities USING GIN(search_vector);

ALTER TABLE facts ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
CREATE INDEX idx_facts_fts ON facts USING GIN(search_vector);
```

### Key implementation details

**`kuro/core/llm.py`** — extracted from `agent.py:183-273`:
- `call_gemini(contents, tools)` → raw HTTP POST (`agent.py:183-199`)
- `extract_parts(response)` → pull parts from response (`agent.py:202-207`)
- `call_with_tools(contents, tools, tool_handlers)` → agent loop (`agent.py:210-273`)
- Handles `thoughtSignature` passthrough for Gemini 3 (`agent.py:238-241`)

**`kuro/memory/store.py`** — Supabase client:
- Uses `supabase-py` client library
- `add_entity(name, entity_type, summary)` → upsert to `entities`
- `add_fact(entity_id, content, source)` → insert to `facts`
- `add_relation(source_id, relation_type, target_id, context)` → insert to `relations`
- `search_entities(query)` → `select * from entities where search_vector @@ plainto_tsquery(query)`
- `search_facts(query)` → `select * from facts where search_vector @@ plainto_tsquery(query)`
- `get_entity_by_name(name)` → exact match lookup
- `get_facts_for_entity(entity_id)` → facts by entity
- `get_relations_for_entity(entity_id)` → relations where source or target

**`kuro/agents/ingest.py`** — see `kuro-flow.md` Phase 5a:
- System prompt tells Gemini to extract entities, facts, relations from NL input
- Tools: `store_entity`, `store_fact`, `store_relation` (wrappers over `store.py`)
- Uses `call_with_tools()` from `llm.py` for the agent loop

**`kuro/agents/query.py`** — simplified from `kuro-flow.md` Phase 5b:
- Phase 1: standard tool-call loop (PTC comes in Phase 3)
- Tools: `search_entities`, `search_facts`, `get_facts_for_entity`, `get_relations_for_entity`
- Gemini searches → gets results → synthesizes answer

**`kuro/cli.py`** — routing:
- Simple heuristic: ends with `?` → query agent, else → ingest agent
- Or single cheap Gemini call: "Is this STORE or QUERY or CHAT?"

### Dependencies to add

```toml
# pyproject.toml additions
"pydantic>=2.0",
"supabase>=2.0",
```

### Test criteria

```
You: Met John at the AI conference. He's a PM at Stripe, interested in our API.
Kuro: Saved. John — PM at Stripe, interested in API product.

You: Who works at Stripe?
Kuro: John — PM at Stripe. You met him at the AI conference.

[restart CLI]

You: Who did I meet recently?
Kuro: John — PM at Stripe (met at AI conference).
```

---

## Phase 2: Article Ingestion + Filesystem

**Goal:** Save URLs → scrape → extract concepts → link to knowledge graph.

### Files to create/modify

| File | What | Reference |
|------|------|-----------|
| `kuro/memory/files.py` | Save article markdown to `data/articles/<topic>/` | `kuro-flow.md` Phase 1 `files.py` |
| `kuro/agents/ingest.py` | **Extended:** detect URLs → scrape → extract concepts → store | `kuro-flow.md` Phase 5a (URL flow) |

### Supabase schema additions

```sql
CREATE TABLE articles (
    id         BIGSERIAL PRIMARY KEY,
    url        TEXT,
    title      TEXT NOT NULL,
    file_path  TEXT NOT NULL,          -- path to markdown on disk
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Key implementation details

**`kuro/memory/files.py`** — see `kuro-flow.md` Phase 1 `files.py`:
- `ArticleStore.save_article(title, content, topic)` → writes to `data/articles/<topic>/<slug>.md`
- `ArticleStore.get_article(file_path)` → read markdown
- `ArticleStore.list_topics()` → list topic directories

**`kuro/agents/ingest.py`** extended — see `kuro-flow.md` Phase 5a (URL flow):
- New tools: `scrape_url`, `save_article`, `extract_concepts`
- `scrape_url` uses `httpx` + `beautifulsoup4` + `markdownify` to fetch → clean → markdown
- Gemini extracts concepts from article, stores as entities, links to article

### Dependencies to add

```toml
"beautifulsoup4>=4.12",
"markdownify>=0.11",
"httpx>=0.27",
```

### Test criteria

```
You: Save this: https://jalammar.github.io/illustrated-transformer/
Kuro: Saved "The Illustrated Transformer". Extracted 6 concepts.

You: What do I know about attention mechanisms?
Kuro: From "The Illustrated Transformer": Self-Attention computes...
```

---

## Phase 3: Search Interface + Graph Traversal

**Goal:** Query agent stops getting results pre-loaded — it gets search tools and builds its own context. Add graph traversal so the agent can follow relationships.

> *Lesson from Claude Code: "Claude went from not being able to build its own context, to doing nested search across several layers of files to find the exact context it needed." Search tools > pre-loaded context. Progressive disclosure > fat prompts.*

### What changes from Phase 1/2

```
Phase 1-2 (current):
  User asks question → we run FTS → dump all results into prompt → Gemini synthesizes
  Problem: no filtering, context bloat as knowledge base grows

Phase 3:
  User asks question → Gemini gets search tools → it decides what to search →
  follows leads through tool calls → synthesizes from what it found

  The model searches its own knowledge base, like Claude Code searches codebases.
```

**Progressive disclosure — 3 layers, via regular tool calls:**
- **Layer 1:** `search_entities(query)` / `search_facts(query)` — broad search, returns summaries
- **Layer 2:** `get_relations(entity_id)` / `get_facts(entity_id)` — drill into a specific entity
- **Layer 3:** `read_article(file_path)` — load full content on demand

The agent starts broad, follows leads, stops when it has enough. No pre-loading.

### Files to create/modify

| File | What | Reference |
|------|------|-----------|
| `kuro/memory/store.py` | **Extended:** `traverse()`, `get_knowledge_index()` | `kuro-flow.md` Phase 1 store functions |
| `kuro/agents/query.py` | **Rewritten:** search-based, agent builds its own context via tool calls | `kuro-flow.md` Phase 5b, simplified |

### Key implementation details

**`kuro/agents/query.py`** rewritten:
- Agent gets search tools, not search results
- Uses standard Gemini tool-call loop (same `call_with_tools` from `llm.py`)
- Tools available to the query agent:

| Tool | Returns | Layer |
|------|---------|-------|
| `search_entities(query)` | FTS matches: `[{id, name, type, summary}]` | 1 — broad |
| `search_facts(query)` | FTS matches: `[{id, content, entity_name}]` | 1 — broad |
| `get_relations(entity_id)` | `[{relation_type, target_name, context}]` | 2 — drill down |
| `get_facts(entity_id)` | `[{content, source}]` | 2 — drill down |
| `get_knowledge_index()` | All entity names + types (~200 tokens) | 1 — overview |
| `read_article(file_path)` | Full article markdown | 3 — full content |

- The model calls tools in whatever order makes sense for the query
- Simple queries ("Who is John?") → 1-2 tool calls
- Complex queries ("How does John connect to X?") → search → get_relations → follow chain

**`kuro/memory/store.py`** extended:
- `traverse(entity_id, depth)` → BFS through relations, returns neighborhood
- `get_knowledge_index()` → lightweight list of all entities (name + type only)

### No new dependencies

Uses same Gemini tool-call loop from Phase 1. No PTC, no embeddings, no new libraries.

### Test criteria

```
# Verify the agent searches instead of getting pre-loaded results:

"Who is John?"
  → Agent calls search_entities("John") → gets result → synthesizes
  → Does NOT receive all entities in its prompt

"Who works at Stripe?"
  → Agent calls search_entities("Stripe") → get_relations(stripe_id) → synthesizes
  → Follows the graph through tool calls

"What do I know about attention?"
  → Agent calls search_facts("attention") → maybe read_article(...) → synthesizes
  → Only loads article content if needed

# After 20 queries, context should stay bounded
# (tool results are just search results, not full DB dumps)
```

---

## Phase 4: Context Engineering

**Goal:** Long conversations don't degrade. Session memory persists across restarts.

### Files to create/modify

| File | What | Reference |
|------|------|-----------|
| `kuro/context/__init__.py` | Package init | — |
| `kuro/context/compaction.py` | 3-level context compression | `kuro-flow.md` Phase 4 `compaction.py` |
| `kuro/context/builder.py` | Per-agent prompt assembly | `kuro-flow.md` Phase 4 `builder.py` |
| `kuro/memory/scratchpad.py` | Per-task working memory | `kuro-flow.md` Phase 1 `scratchpad.py` |
| `kuro/memory/episodic.py` | Session summaries | `kuro-flow.md` Phase 1 `episodic.py` |
| `kuro/memory/store.py` | **Extended:** scratchpad + episodes tables | `kuro-flow.md` Phase 1 schema |

### Supabase schema additions

```sql
CREATE TABLE episodes (
    id                 BIGSERIAL PRIMARY KEY,
    session_id         TEXT NOT NULL,
    summary            TEXT NOT NULL,
    key_decisions      JSONB,            -- array of decisions made
    entities_mentioned JSONB,            -- array of entity IDs
    topics_covered     JSONB,            -- array of topic names
    created_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scratchpad (
    task_id    TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (task_id, key)
);
```

### Key implementation details

**Compaction levels** — see `kuro-flow.md` Phase 4 `compaction.py`:
1. Tool result clearing (>8K tokens) — replace old tool outputs with one-liners
2. Turn summarization (>16K tokens) — LLM summarizes old turns, keep last 5
3. Full compaction (>32K tokens) — compress everything, keep last exchange

**Context builder** — see `kuro-flow.md` Phase 4 `builder.py`:
- Assembles per-agent: role + skill docs + scratchpad + episodes + compacted history
- Different context shape per agent type

**Session lifecycle:**
- Task starts → scratchpad active
- Task ends → scratchpad cleared
- Session ends → episode generated → facts extracted

### Test criteria

```
20+ turn conversation → compaction triggers → restart → "what did we discuss?" works
```

---

## Phase 5: Multi-Agent Orchestration

**Goal:** Proper orchestrator replaces the simple heuristic router from Phase 1. Each agent gets only the context it needs.

### Files to create/modify

| File | What | Reference |
|------|------|-----------|
| `kuro/agents/orchestrator.py` | LLM classifier → routes to specialist | `kuro-flow.md` Phase 5e |
| `kuro/agents/code.py` | Shell/file ops (wrap existing `agent.py`) | `kuro-flow.md` Phase 5d |
| `kuro/skills/registry.py` | Skill index — agent names + triggers (~200 tokens) | `kuro-flow.md` Phase 5e `SKILL_INDEX` |
| `kuro/skills/definitions/*.md` | Per-skill instruction docs (loaded on demand) | New |

### Key implementation details

**Orchestrator** — single cheap Gemini Flash call:
- Sees: user message + `SKILL_INDEX` (just agent names + trigger descriptions, ~200 tokens)
- Returns: `{agent: "ingest"|"query"|"study"|"code"}`
- Does NOT see: full skill docs, knowledge base, conversation history
- Cost: ~0.001¢ per classification

**Skill files** — same progressive disclosure pattern from Phase 3, applied to agent instructions:
- Orchestrator picks the agent → agent's skill file is loaded into its system prompt
- Skill files can reference data the agent should load via its tools (articles, entities, etc.)
- This keeps each agent's prompt lean — only loads instructions relevant to the current task

**Code agent** — wraps existing `agent.py` logic:
- Same tools: `shell`, `read_file`, `edit_file`, `create_file`
- Same sandbox (`srt`) integration
- Just refactored to be callable by orchestrator instead of running standalone

### Test criteria

```
"Met John at conference"   → routes to ingest agent
"Who works at Stripe?"     → routes to query agent
"Run ls -la"               → routes to code agent
"Let's discuss attention"  → routes to study agent (Phase 6)
Mixed: "Save this and tell me what it's about" → orchestrator picks ingest
```

---

## Phase 6: Study Features

**Goal:** Socratic discussion, quizzes with SM-2 spaced repetition.

### Files to create/modify

| File | What | Reference |
|------|------|-----------|
| `kuro/agents/study.py` | Discussion + quiz + revision modes | `kuro-flow.md` Phase 5c |
| `kuro/retrieval/web.py` | Web search wrapper (Tavily) | `kuro-flow.md` Phase 3 `web.py` |
| `kuro/memory/store.py` | **Extended:** concepts table with SM-2 fields | `kuro-flow.md` Phase 1 schema |

### Supabase schema additions

```sql
CREATE TABLE concepts (
    id          BIGSERIAL PRIMARY KEY,
    entity_id   BIGINT REFERENCES entities(id) ON DELETE CASCADE,
    article_id  BIGINT REFERENCES articles(id) ON DELETE SET NULL,
    confidence  REAL DEFAULT 0.0,
    next_review DATE,
    easiness    REAL DEFAULT 2.5,       -- SM-2 easiness factor
    interval    INTEGER DEFAULT 1,      -- days until next review
    repetitions INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
```

### Key implementation details

**SM-2 algorithm** — see `kuro-flow.md` Phase 5c:
- `sm2_update(concept, quality)` — quality 0-5, updates easiness/interval/repetitions/next_review

**Study modes** — see `kuro-flow.md` Phase 5c:
- **DISCUSS:** Load articles + concepts → Socratic questions → update confidence
- **QUIZ:** Get due concepts → ask questions → evaluate → update SM-2 scores
- **REVISE:** Find lowest-confidence concepts → explain → quiz
- **PLAN:** Web search for resources on weak topics

### Dependencies to add

```toml
# Only if using Tavily for web search
"httpx>=0.27",  # (already added in Phase 2)
```

### Test criteria

```
Quiz on saved concepts → SM-2 scores update → next quiz shows spaced intervals
```

---

## Phase 7: Web UI

**Goal:** Browser chat interface.

### Files to create/modify

| File | What | Reference |
|------|------|-----------|
| `kuro/web/app.py` | FastAPI + SSE streaming | New |
| `kuro/web/static/index.html` | Single-page chat UI (vanilla JS) | New |

### Dependencies to add

```toml
"sse-starlette>=1.6",
```

### Test criteria

```
Open browser → chat → same capabilities as CLI → streaming responses
```

---

## Summary

| Phase | What You Get | Key New Files | DB Changes |
|-------|-------------|---------------|------------|
| **1** | Capture + query + CLI | `config`, `llm`, `types`, `store`, `ingest`, `query`, `cli` | `entities`, `facts`, `relations` + FTS indexes |
| **2** | URL scraping + concept extraction | `files.py`, extend `ingest.py` | `articles` table |
| **3** | Search interface + graph traversal | Rewrite `query.py`, extend `store.py` | — (no new tables) |
| **4** | Compaction + scratchpad + episodes | `compaction.py`, `builder.py`, `scratchpad.py`, `episodic.py` | `episodes`, `scratchpad` tables |
| **5** | Orchestrator + multi-agent routing | `orchestrator.py`, `code.py`, `registry.py`, skill docs | — |
| **6** | Study: discuss + quiz + SM-2 | `study.py`, `web.py` | `concepts` table |
| **7** | Browser UI | `web/app.py`, `web/static/index.html` | — |

### Future optimizations (when we see where basic search fails)

| Optimization | What | When to add |
|-------------|------|-------------|
| **PTC** | Model writes Python to run multiple searches in 1 exec → 2 LLM calls instead of N | When query agent consistently needs 4+ tool-call round trips |
| **Semantic search** | pgvector embeddings for meaning-based queries | When keyword + graph clearly fails on "concepts related to X" type queries |
| **Hybrid retrieval** | Combine keyword + semantic + graph scores | When we have enough data to compare strategy quality |

## Why Supabase over SQLite

| Feature | SQLite | Supabase (PostgreSQL) |
|---------|--------|-----------------------|
| Full-text search | FTS5 (custom syntax) | `tsvector` + GIN (standard SQL) |
| Vector search | sqlite-vec (C extension, fragile) | pgvector (first-class, maintained) |
| Hosting | local file, lost if machine changes | cloud, accessible anywhere |
| Concurrent access | single-writer lock | full MVCC |
| JSON support | basic `json_extract` | JSONB with indexing |
| Auth/RLS | none | built-in row-level security |
| Cost | free | free tier (500MB, 50K rows) |

**Trade-off:** Adds network latency per query (~50-100ms). Acceptable since Gemini calls are 1-3s anyway.

---

**Phase 1 is the immediate priority.** Get capture + retrieve working with Supabase, then iterate.
