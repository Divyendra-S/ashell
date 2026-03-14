# Plan: Kuro — Personal AI Assistant with Intelligent Memory

## Context

The current `ashell` project is a CLI agent (Gemini 3.1 Pro) with shell execution and sandboxing. The goal is to evolve it into a **Personal AI Assistant** — something you'd use daily — that exercises all advanced agentic techniques (PTC, multi-agent, three-tier memory, multi-strategy retrieval, progressive disclosure, compaction, Graph RAG) for an AI engineer interview.

**Core idea:** You talk to it naturally — it stores data intelligently AND acts as a full personal assistant. It's not a generic "do anything" agent; it's YOUR assistant that knows your world.

> **Related plans:**
> - [`kuro-study-plan.md`](./kuro-study-plan.md) — Study Assistant feature: Chrome extension + mobile app for ingesting articles/notes, Socratic discussions, quizzes, spaced repetition, study planning, and knowledge graph across topics.

---

## Feature Set (7 Features)

| # | Feature | Description | Key Techniques |
|---|---------|-------------|----------------|
| 1 | **Smart Ingest** | "We closed 5 deals worth $200K" → parses into entities, relations, facts | Three-tier memory, Graph data model |
| 2 | **Intelligent Query** | "How were sales this quarter?" → picks the right retrieval strategy | Multi-strategy retrieval, PTC |
| 3 | **Daily Briefing** | "Brief me" → synthesizes recent facts, open tasks, decisions | Compaction, episodic memory |
| 4 | **Research & Analyze** | "Research competitor X" / "Analyze this CSV" → multi-agent report | Multi-agent orchestration, sandbox, PTC |
| 5 | **Task Tracking** | "Remind me to follow up with John Friday" → persistent tasks | Fact memory, progressive disclosure |
| 6 | **Code Assistant** | Shell/file ops as a specialist agent (evolved from current agent.py) | Code sandbox, existing tools |
| 7 | **Live Dashboard** | Web UI with conversation, agent activity, entity graph visualization | WebSocket streaming |

---

## Project Structure

```
ashell/
├── pyproject.toml
├── .env
├── srt-settings.json
├── kuro/
│   ├── __init__.py
│   ├── cli.py                     # CLI entry point
│   ├── server.py                  # FastAPI + WebSocket
│   │
│   ├── core/
│   │   ├── agent.py               # BaseAgent: prompt + loop + tool dispatch
│   │   ├── llm.py                 # Gemini REST client (extracted from agent.py)
│   │   ├── ptc.py                 # PTC executor (restricted exec + injected tools)
│   │   └── types.py               # Pydantic models
│   │
│   ├── agents/
│   │   ├── orchestrator.py        # Routes input → specialist
│   │   ├── ingest.py              # NL → structured entities/facts
│   │   ├── query.py               # Picks retrieval strategy via PTC
│   │   ├── research.py            # Web search + synthesis
│   │   ├── code.py                # Shell/file ops (from current agent.py)
│   │   └── data.py                # CSV/data analysis via PTC
│   │
│   ├── memory/
│   │   ├── store.py               # SQLite backend (facts, entities, relations, episodes)
│   │   ├── scratchpad.py          # Per-task working memory
│   │   ├── episodic.py            # Session summaries
│   │   └── facts.py               # Entity/fact extraction + CRUD
│   │
│   ├── retrieval/
│   │   ├── router.py              # Strategy picker (exposed to PTC)
│   │   ├── keyword.py             # BM25 via SQLite FTS5 (zero deps)
│   │   ├── semantic.py            # Vector search (sqlite-vec or chromadb)
│   │   ├── graph.py               # Entity graph traversal (networkx + SQLite)
│   │   └── web.py                 # Web search API wrapper
│   │
│   ├── context/
│   │   ├── builder.py             # Assembles prompt per agent
│   │   └── compaction.py          # Summarize old turns, preserve decisions
│   │
│   ├── sandbox/
│   │   ├── executor.py            # Python exec() with restricted builtins
│   │   └── shell.py               # Shell execution with srt
│   │
│   ├── skills/
│   │   ├── registry.py            # Tier 1: skill name + description index
│   │   └── definitions/           # Tier 2: full docs loaded on demand
│   │       ├── task_management.md
│   │       ├── data_analysis.md
│   │       ├── web_research.md
│   │       └── code_assistance.md
│   │
│   └── web/
│       ├── routes.py              # REST: /chat, /memory, /tasks
│       ├── ws.py                  # WebSocket: live agent status
│       └── static/
│           └── index.html         # Single-page dashboard
│
├── data/                          # Runtime, gitignored
│   ├── kuro.db
│   └── vectors/
│
└── tests/
```

---

## Architecture

### Agent Communication Flow

```
User Input → Orchestrator (classifies: STORE | QUERY | TASK | CHAT)
    ├── STORE   → Ingest Agent → memory/facts.py → SQLite
    ├── QUERY   → Query Agent  → retrieval/router.py → [keyword|semantic|graph|web]
    ├── TASK    → Code Agent / Research Agent / Data Agent
    ├── COMPLEX → Plan (via PTC) → fan-out to multiple agents
    └── CHAT    → Direct Gemini response
```

### PTC Design (Central to Multiple Features)

Same executor, different tool namespaces per agent:
- **Query Agent** gets: `keyword_search()`, `semantic_search()`, `graph_query()`, `web_search()`
- **Data Agent** gets: `pandas`, `matplotlib`, `print()`
- **Code Agent** gets: `shell()`, `read_file()`, `edit_file()`, `create_file()`

```python
# core/ptc.py
def execute_ptc(code: str, tools: dict[str, Callable], timeout: int = 30) -> str:
    output = io.StringIO()
    namespace = {
        **tools,                          # injected real functions
        "print": lambda *a, **kw: print(*a, file=output, **kw),
        "__builtins__": SAFE_BUILTINS,    # restricted set
    }
    exec(code, namespace)
    return output.getvalue()
```

### Memory Data Model (SQLite)

```sql
-- Core entities (people, companies, projects, etc.)
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,          -- person, company, project, topic
    attributes TEXT,             -- JSON blob for flexible fields
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Relationships between entities
CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES entities(id),
    target_id TEXT REFERENCES entities(id),
    relation TEXT NOT NULL,      -- "works_at", "reports_to", "closed_deal_with"
    attributes TEXT,             -- JSON: {"value": "$200K", "date": "2026-03"}
    created_at TIMESTAMP
);

-- Individual facts (atomic pieces of knowledge)
CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,       -- "We closed 5 deals worth $200K in Q1 2026"
    entity_ids TEXT,             -- JSON array of related entity IDs
    source TEXT,                 -- "user_input" | "extracted" | "web_search"
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP,
    superseded_by TEXT           -- points to newer fact if updated
);

-- FTS5 virtual table for keyword search
CREATE VIRTUAL TABLE facts_fts USING fts5(content, content=facts, content_rowid=rowid);

-- Episodic memory (session summaries)
CREATE TABLE episodes (
    id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    key_decisions TEXT,          -- JSON array
    entities_mentioned TEXT,     -- JSON array of entity IDs
    created_at TIMESTAMP,
    session_id TEXT
);

-- Scratchpad (per-task, ephemeral)
CREATE TABLE scratchpad (
    task_id TEXT,
    key TEXT,
    value TEXT,
    updated_at TIMESTAMP,
    PRIMARY KEY (task_id, key)
);
```

### Retrieval Strategy Selection

Query agent writes Python via PTC to pick strategy:
```python
# Model sees available functions and writes code like:

# For relationship questions:
results = graph_query("John", relation="reports_to", depth=1)
print(format_results(results))

# For conceptual questions:
facts = semantic_search("sales performance Q1 2026", top_k=10)
if not facts:
    facts = keyword_search("sales deals revenue")
print(format_results(facts))

# For exact lookups:
results = keyword_search("John email")
print(format_results(results))
```

### Compaction Strategy

When conversation history exceeds token threshold:
1. **Tool result clearing** (lightest): Replace tool outputs older than 5 turns with one-line summaries
2. **Turn summarization** (medium): Summarize turns 1-N into a paragraph, keep last 5 turns verbatim
3. **Full compaction** (heaviest): Generate comprehensive summary preserving: decisions, preferences, current plan, unresolved questions

### Progressive Disclosure

Orchestrator's system prompt includes only the skill index (Tier 1):
```
Available capabilities:
- task_management: Track tasks, deadlines, follow-ups
- data_analysis: Analyze CSVs, generate charts, compute statistics
- web_research: Search the web, summarize articles
- code_assistance: Run shell commands, edit files, write code
- memory_management: Store and retrieve personal knowledge
```

When delegating to a specialist, that agent's prompt loads the full `skills/definitions/*.md` (Tier 2).

---

## Build Phases

### Phase 1: Core Engine (extract + modularize existing code)
- Extract `core/llm.py` from Gemini client in `agent.py:183-199`
- Extract `sandbox/shell.py` from `run_shell` in `agent.py:112-136`
- Build `core/agent.py` — BaseAgent with tool-call loop from `agent.py:210-273`
- Build `core/types.py` — Pydantic models
- Build `cli.py` recreating current behavior
- **Demo:** Same CLI agent, now modular

### Phase 2: Memory System
- Build `memory/store.py` — SQLite with entities, facts, relations, episodes tables
- Build `memory/facts.py` — CRUD operations
- Build `agents/ingest.py` — parses NL into structured data via Gemini
- Wire into CLI: statements go through ingest
- **Demo:** Tell it facts, restart, ask about them → facts persist

### Phase 3: Intelligent Retrieval
- Build `retrieval/keyword.py` — SQLite FTS5 (zero new deps)
- Build `retrieval/semantic.py` — sqlite-vec or chromadb
- Build `retrieval/router.py` — strategy picker
- Build `agents/query.py` — picks strategy via PTC
- Build `core/ptc.py` — restricted exec with injected tools
- **Demo:** "How were sales this quarter?" → answers from stored data

### Phase 4: Multi-Agent Orchestration
- Build `agents/orchestrator.py` — classifies + delegates
- Build `agents/code.py` — evolved shell/file specialist
- Build `context/builder.py` — prompt assembly per agent
- Build `skills/registry.py` + skill definitions
- **Demo:** Different inputs route to different specialists

### Phase 5: Compaction + Episodic Memory
- Build `context/compaction.py` — summarize old turns
- Build `memory/episodic.py` — session summaries
- Build `memory/scratchpad.py` — per-task working memory
- Wire "brief me" daily briefing
- **Demo:** Long conversations stay coherent, sessions produce summaries

### Phase 6: Research + Data Analysis
- Build `retrieval/web.py` — web search wrapper
- Build `agents/research.py` — web search + synthesis
- Build `agents/data.py` — CSV analysis via PTC (pandas in sandbox)
- Build `retrieval/graph.py` — entity graph traversal (networkx)
- Update `srt-settings.json` to allow network for web search
- **Demo:** "Research X" → markdown report. "Analyze CSV" → stats + insights.

### Phase 7: Web Dashboard
- Build `server.py` — FastAPI wrapping the core
- Build `web/ws.py` — WebSocket streaming agent events
- Build `web/static/index.html` — dashboard with entity graph visualization
- **Demo:** Browser shows live agent activity — the interview showpiece

---

## Critical Files to Extract From

| Source | Extracts To | What |
|--------|-------------|------|
| `agent.py:183-199` | `kuro/core/llm.py` | Gemini REST client |
| `agent.py:210-273` | `kuro/core/agent.py` | BaseAgent loop (preserve thoughtSignature handling!) |
| `agent.py:112-136` | `kuro/sandbox/shell.py` | Shell execution with srt |
| `agent.py:85-94` | `kuro/sandbox/shell.py` | safe_path() validation |
| `agent.py:138-180` | `kuro/agents/code.py` | File ops (read/edit/create) |
| `srt-settings.json` | Carried forward | Sandbox config (enable network in Phase 6) |
| `pyproject.toml` | Evolved | Add deps per phase |

## New Dependencies (Added Incrementally)

- Phase 2: `pydantic>=2.0`
- Phase 3: `sqlite-vec>=0.1.0` or `chromadb`, `sentence-transformers`
- Phase 6: `networkx>=3.0`, `httpx>=0.27`

---

## Verification

After each phase:
1. **Phase 1:** Run `python -m kuro.cli` → same behavior as current `python agent.py`
2. **Phase 2:** Tell it facts, restart, ask about them → facts persist
3. **Phase 3:** Ask varied questions → see different retrieval strategies used
4. **Phase 4:** Mix statements/questions/tasks → correct routing
5. **Phase 5:** Have 20+ turn conversation → compaction triggers, session summary generated
6. **Phase 6:** "Research X" and "Analyze CSV" → produce reports
7. **Phase 7:** Open browser → live dashboard with agent activity

**End-to-end demo:** Tell it 5 facts → ask 3 questions → give it a complex task → show entity graph → restart and verify memory persists.

---

## Interview Talking Points

| Technique | What You Say |
|-----------|-------------|
| **PTC** | "Instead of JSON tool calls, the model writes Python that orchestrates multiple retrieval strategies in one execution — 2 model calls instead of N round trips" |
| **Progressive Disclosure** | "Agents don't see all tools at once. They discover capabilities from a skill registry on demand — same pattern Claude Code uses" |
| **Compaction** | "When conversations exceed the token budget, I compress older context while preserving decisions and key findings" |
| **Memory** | "Three tiers — scratchpad per task, episode summaries per session, extracted facts that persist forever. SQLite because Letta showed plain filesystem beats vector stores at 74%" |
| **Retrieval** | "Four layers — BM25 for exact match, vector for semantic, graph for entity relationships, web for current info. The agent decides which to use by writing code" |
| **Multi-Agent** | "Orchestrator pattern — one coordinator classifies and routes to specialist agents. Each agent has its own context, tools, and scratchpad" |
| **Code Execution** | "Model-generated code runs in restricted exec() with injected tool functions. Shell commands go through Anthropic's srt sandbox" |
| **Tool Design** | "I revisit tool designs as models improve — started with explicit routing, moved to PTC when models got better at writing retrieval code" |

---

## What Makes This Interview-Worthy

1. **You actually use it daily** — "Let me show you my entity graph and what I tracked this week"
2. **Techniques aren't bolted on** — PTC IS how retrieval works, memory IS how it knows things
3. **Live demo flow:** Tell it 3 facts → ask questions → complex task → show dashboard → restart & verify memory
4. **Conversation starters:** "Why PTC?", "How does retrieval selection work?", "How do you handle context limits?"
