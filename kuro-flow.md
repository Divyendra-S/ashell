# Kuro — Complete Implementation Flow

## Directory Structure

```
kuro/
  __init__.py
  config.py                    # API keys, paths, DB location
  core/
    __init__.py
    llm.py                     # Provider-agnostic LLM client (Gemini default, swappable)
    ptc.py                     # PTC executor: restricted exec() with injected tool functions
    types.py                   # Pydantic models for entities, facts, tool results
  memory/
    __init__.py
    store.py                   # SQLite operations: entities, facts, relations, concepts, episodes, scratchpad
    files.py                   # Markdown file management for articles on disk
    scratchpad.py              # Per-task working memory (read/write/clear)
    episodic.py                # Session summaries: auto-generate episodes at session end
  retrieval/
    __init__.py
    semantic.py                # Vector search via sqlite-vec + sentence-transformers
    web.py                     # Web search API wrapper (SerpAPI / Tavily)
  context/
    __init__.py
    builder.py                 # Per-agent prompt assembly (role + skills + memory + tools)
    compaction.py              # Context compression: 3 levels of summarization
  agents/
    __init__.py
    orchestrator.py            # Classifies input → routes to specialist
    ingest.py                  # Parse facts from text OR scrape URLs → extract concepts
    query.py                   # Multi-strategy retrieval via PTC (4 strategies in one exec)
    study.py                   # Discussion + quiz + spaced repetition (SM-2)
    code.py                    # Shell commands, file ops (existing agent.py logic)
  skills/
    registry.py                # Tier 1: lightweight skill index for progressive disclosure
    definitions/               # Tier 2: full skill docs loaded on demand by agents
      knowledge_storage.md
      article_ingestion.md
      knowledge_retrieval.md
      study_discussion.md
      quiz_review.md
      code_assistance.md
  web/
    app.py                     # FastAPI chat endpoints (replaces current main.py)
    static/
      index.html               # Single-page chat UI
```

---

## Phase 1: Memory System

The foundation. Everything else depends on this.

### SQLite Schema (`kuro/memory/store.py`)

```sql
-- Core entities: people, companies, concepts, projects, articles
CREATE TABLE entities (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,        -- person | company | concept | project | article
    summary     TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Facts attached to entities (Tier 3: durable knowledge)
CREATE TABLE facts (
    id         INTEGER PRIMARY KEY,
    entity_id  INTEGER REFERENCES entities(id),
    content    TEXT NOT NULL,
    source     TEXT,                  -- "user", article URL, "discussion"
    created_at TEXT DEFAULT (datetime('now'))
);

-- Relationships between entities
CREATE TABLE relations (
    id            INTEGER PRIMARY KEY,
    source_id     INTEGER REFERENCES entities(id),
    relation_type TEXT NOT NULL,       -- works_at | interested_in | related_to | part_of
    target_id     INTEGER REFERENCES entities(id),
    context       TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- Ingested articles
CREATE TABLE articles (
    id         INTEGER PRIMARY KEY,
    url        TEXT,
    title      TEXT NOT NULL,
    file_path  TEXT NOT NULL,          -- path to markdown file on disk
    created_at TEXT DEFAULT (datetime('now'))
);

-- Concepts extracted from articles, with spaced repetition fields
CREATE TABLE concepts (
    id          INTEGER PRIMARY KEY,
    entity_id   INTEGER REFERENCES entities(id),
    article_id  INTEGER REFERENCES articles(id),
    confidence  REAL DEFAULT 0.0,      -- 0.0–1.0
    next_review TEXT,                   -- ISO date for next quiz
    easiness    REAL DEFAULT 2.5,       -- SM-2 easiness factor
    interval    INTEGER DEFAULT 1,      -- days until next review
    repetitions INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Episodic memory: session summaries (Tier 2: per-session)
CREATE TABLE episodes (
    id                 INTEGER PRIMARY KEY,
    session_id         TEXT NOT NULL,
    summary            TEXT NOT NULL,       -- LLM-generated session summary
    key_decisions      TEXT,                -- JSON array of decisions made
    entities_mentioned TEXT,                -- JSON array of entity IDs referenced
    topics_covered     TEXT,                -- JSON array of topic names
    created_at         TEXT DEFAULT (datetime('now'))
);

-- Scratchpad: per-task working memory (Tier 1: ephemeral)
CREATE TABLE scratchpad (
    task_id    TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (task_id, key)
);

-- Embedding vectors for semantic search
CREATE TABLE embeddings (
    id         INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,          -- "fact" | "article_chunk" | "entity"
    source_id  INTEGER NOT NULL,
    embedding  BLOB NOT NULL,           -- sqlite-vec float32 vector
    content    TEXT NOT NULL,            -- the text that was embedded
    created_at TEXT DEFAULT (datetime('now'))
);

-- FTS5 for keyword search
CREATE VIRTUAL TABLE facts_fts USING fts5(content, content=facts, content_rowid=id);
CREATE VIRTUAL TABLE entities_fts USING fts5(name, summary, content=entities, content_rowid=id);
```

### Three-Tier Memory Model

```
Tier 1: Scratchpad (per-task, ephemeral)
  → Current plan, intermediate retrieval results, open questions
  → Each agent reads/writes its own scratchpad during a task
  → Cleared when task completes

Tier 2: Episodes (per-session summaries)
  → "Discussed attention mechanisms. User strong on self-attention, weak on positional encoding."
  → Auto-generated at session end via LLM summarization
  → Queryable for "what did we talk about last time?"

Tier 3: Facts + Entities + Relations (durable, persist forever)
  → "John is a PM at Stripe" / "Self-Attention is part of Transformers"
  → Extracted from user input, articles, and episode summaries
  → The permanent knowledge graph
```

**Lifecycle:** Task starts → scratchpad active → task ends → episode generated → facts extracted from episode → scratchpad cleared.

### `store.py` — Key Functions

```python
class KnowledgeStore:
    def __init__(self, db_path="kuro/data/kuro.db"):
        # Opens SQLite, runs schema if needed

    # --- Write ---
    def add_entity(self, name, entity_type, summary=None) -> int
    def add_fact(self, entity_id, content, source="user") -> int
    def add_relation(self, source_id, relation_type, target_id, context=None) -> int
    def add_article(self, url, title, file_path) -> int
    def add_concept(self, entity_id, article_id) -> int

    # --- Read ---
    def search_entities(self, query) -> list[dict]        # FTS5 keyword search
    def search_facts(self, query) -> list[dict]            # FTS5 keyword search
    def get_entity(self, entity_id) -> dict
    def get_entity_by_name(self, name) -> dict | None
    def get_facts_for_entity(self, entity_id) -> list[dict]
    def get_relations_for_entity(self, entity_id) -> list[dict]

    # --- Graph traversal ---
    def traverse(self, entity_id, depth=2) -> dict         # BFS through relations
    def find_path(self, from_id, to_id) -> list[dict]      # Shortest path between entities

    # --- Spaced repetition ---
    def get_concepts_due() -> list[dict]                    # Concepts where next_review <= today
    def update_concept_score(self, concept_id, quality)     # SM-2 algorithm update

    # --- Scratchpad (Tier 1) ---
    def scratchpad_set(self, task_id, key, value)
    def scratchpad_get(self, task_id, key) -> str | None
    def scratchpad_get_all(self, task_id) -> dict
    def scratchpad_clear(self, task_id)

    # --- Episodes (Tier 2) ---
    def add_episode(self, session_id, summary, key_decisions, entities_mentioned) -> int
    def get_recent_episodes(self, limit=5) -> list[dict]
    def search_episodes(self, query) -> list[dict]          # FTS or keyword match

    # --- Embeddings (for semantic search) ---
    def add_embedding(self, source_type, source_id, embedding, content) -> int
    def search_embeddings(self, query_embedding, top_k=10) -> list[dict]  # sqlite-vec nearest neighbor
```

### `scratchpad.py` — Per-Task Working Memory

```python
class Scratchpad:
    """Thin wrapper over store.scratchpad_* for agent convenience."""

    def __init__(self, store: KnowledgeStore, task_id: str):
        self.store = store
        self.task_id = task_id

    def set(self, key: str, value: str):
        self.store.scratchpad_set(self.task_id, key, value)

    def get(self, key: str) -> str | None:
        return self.store.scratchpad_get(self.task_id, key)

    def get_all(self) -> dict:
        return self.store.scratchpad_get_all(self.task_id)

    def clear(self):
        self.store.scratchpad_clear(self.task_id)

    def to_context_string(self) -> str:
        """Format scratchpad contents for inclusion in agent prompt."""
        items = self.get_all()
        if not items:
            return ""
        return "## Current Task State\n" + "\n".join(f"- {k}: {v}" for k, v in items.items())
```

### `episodic.py` — Session Summaries

```python
class EpisodicMemory:
    def __init__(self, store: KnowledgeStore, llm):
        self.store = store
        self.llm = llm

    def generate_episode(self, session_id: str, conversation_history: list[dict]) -> dict:
        """Called at session end. LLM summarizes the session into an episode."""
        summary_prompt = """Summarize this conversation session:
        - What topics were discussed?
        - What key decisions or conclusions were reached?
        - What entities (people, concepts, projects) were mentioned?
        - What questions remain unresolved?
        Be concise. This summary will be used to restore context in future sessions."""

        summary = self.llm.call(messages=[
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": format_conversation(conversation_history)}
        ])

        episode = self.store.add_episode(
            session_id=session_id,
            summary=summary,
            key_decisions=extract_decisions(summary),
            entities_mentioned=extract_entity_ids(summary, self.store)
        )
        return episode

    def get_relevant_context(self, query: str, limit: int = 3) -> str:
        """Pull relevant past episodes to include in agent context."""
        episodes = self.store.search_episodes(query)[:limit]
        if not episodes:
            return ""
        return "## Relevant Past Sessions\n" + "\n".join(
            f"- [{e['created_at']}] {e['summary']}" for e in episodes
        )
```

### `files.py` — Article File Management

```
kuro/data/articles/
  transformers/
    illustrated-transformer.md       # Full scraped content
    concepts.md                      # Extracted concept list with links
  sequence-models/
    ...
```

```python
class ArticleStore:
    def __init__(self, base_path="kuro/data/articles"):

    def save_article(self, title, content, topic) -> str      # Returns file path
    def get_article(self, file_path) -> str                    # Read markdown
    def search_articles(self, query) -> list[str]              # Grep through files
    def list_topics(self) -> list[str]                         # List topic directories
```

---

## Phase 2: Core Engine

### LLM Client (`kuro/core/llm.py`)

Provider-agnostic LLM client. Gemini by default, swappable per agent for cost optimization.

```python
class LLMClient:
    """Provider-agnostic LLM client. Each agent can use a different model."""

    PROVIDERS = {
        "gemini":    {"base_url": "https://generativelanguage.googleapis.com/v1beta",
                      "default_model": "gemini-3.1-pro-preview"},
        "gemini-flash": {"base_url": "https://generativelanguage.googleapis.com/v1beta",
                         "default_model": "gemini-2.0-flash"},
        "anthropic": {"base_url": "https://api.anthropic.com/v1",
                      "default_model": "claude-sonnet-4-20250514"},
        "groq":      {"base_url": "https://api.groq.com/openai/v1",
                      "default_model": "llama-3.3-70b"},
    }

    def __init__(self, provider="gemini", model=None):
        self.provider = provider
        self.model = model or self.PROVIDERS[provider]["default_model"]

    def call(self, messages, tools=None, system_instruction=None) -> dict:
        """Single LLM call. Returns raw response. Routes to correct provider."""

    def call_with_tools(self, messages, tools, tool_handlers) -> str:
        """Agent loop: call model → execute tools → repeat until text response.
        Handles thoughtSignature passthrough for Gemini 3."""

    def extract_text(self, response) -> str:
        """Pull text from response parts (provider-specific parsing)."""

# Per-agent model assignment (cost optimization)
AGENT_MODELS = {
    "orchestrator": LLMClient("gemini-flash"),    # Cheap: just classification
    "ingest":       LLMClient("gemini"),           # Medium: entity extraction
    "query":        LLMClient("gemini"),            # Medium: writes PTC code
    "study":        LLMClient("gemini"),            # Strong: Socratic dialogue
    "code":         LLMClient("gemini"),            # Strong: code generation
}
```

**Interview talking point:** "Different models per agent role — cheap/fast model for the orchestrator's classification, strong model for study agent's Socratic dialogue. Swap providers with one config change."

### PTC Executor (`kuro/core/ptc.py`)

The central differentiator. Instead of N tool-call round trips, the model writes Python that orchestrates multiple tools in one execution — 2 model calls total.

```python
import io

# Restricted builtins — no file I/O, no imports, no eval
SAFE_BUILTINS = {
    "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "str": str, "int": int, "float": float, "list": list, "dict": dict,
    "set": set, "tuple": tuple, "bool": bool,
    "max": max, "min": min, "sorted": sorted, "reversed": reversed,
    "any": any, "all": all, "sum": sum, "round": round, "abs": abs,
    "isinstance": isinstance, "type": type,
    "True": True, "False": False, "None": None,
}

def execute_ptc(code: str, tools: dict[str, Callable], timeout: int = 30) -> str:
    """
    Execute model-generated Python with injected tool functions.

    The model writes code using the injected functions. All output
    goes through print() which we capture and return.

    Args:
        code: Python code written by the model
        tools: Dict of function_name → callable (the real implementations)
        timeout: Max execution time in seconds

    Returns:
        Captured stdout from the execution
    """
    output = io.StringIO()
    namespace = {
        **tools,                              # Injected real functions
        "print": lambda *a, **kw: print(*a, file=output, **kw),
        "__builtins__": SAFE_BUILTINS,
    }
    try:
        exec(code, namespace)
    except Exception as e:
        output.write(f"ERROR: {type(e).__name__}: {e}")
    return output.getvalue()
```

**How `call_with_tools` vs `execute_ptc` differ:**

```
call_with_tools (standard tool-call loop):
  Prompt → Model returns tool_call JSON → You execute → Feed result back → Model calls again → ...
  N round trips for N tool invocations. Each round trip = network latency + model inference.

execute_ptc (programmatic tool calling):
  Prompt → Model writes Python code → You exec() it with real functions injected → Return output
  2 total model calls: one to write the code, one to interpret the results.
  The model orchestrates multiple tools in a single code block.
```

**PTC tool namespaces per agent:**

| Agent | Injected Functions |
|-------|-------------------|
| Query | `keyword_search()`, `semantic_search()`, `graph_traverse()`, `graph_path()`, `web_search()`, `read_article()` |
| Study | `get_concepts()`, `get_article()`, `search_facts()`, `update_confidence()` |
| Code  | `shell()`, `read_file()`, `edit_file()`, `create_file()` |

**Example — query agent using PTC instead of tool calls:**

```
# Standard tool-call approach (4 round trips):
LLM call 1: calls search_keyword("attention") → results
LLM call 2: calls graph_traverse(entity_id=5) → more results
LLM call 3: calls search_files("attention mechanism") → article hits
LLM call 4: synthesizes all results → text response

# PTC approach (2 total calls):
LLM call 1: model writes Python:
  execute_ptc("""
    # Search across all strategies
    kw_results = keyword_search("attention")
    sem_results = semantic_search("attention mechanism", top_k=5)

    # Follow up on best entity match
    if kw_results:
        best = kw_results[0]
        graph = graph_traverse(best['id'], depth=2)
        print(f"Graph context for {best['name']}:")
        print(graph)

    print("\\nKeyword results:", kw_results)
    print("Semantic results:", sem_results)
  """)

LLM call 2: model reads captured output → synthesizes final answer
```

---

## Phase 3: Retrieval Layer

### Semantic Search (`kuro/retrieval/semantic.py`)

Embedding-based search using sentence-transformers + sqlite-vec. Complements FTS5 keyword search for meaning-based queries.

```python
from sentence_transformers import SentenceTransformer

class SemanticSearch:
    def __init__(self, store: KnowledgeStore, model_name="all-MiniLM-L6-v2"):
        self.store = store
        self.model = SentenceTransformer(model_name)  # 384-dim, ~80MB

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        return self.model.encode(text).tolist()

    def index_fact(self, fact_id: int, content: str):
        """Embed and store a fact for later retrieval."""
        embedding = self.embed(content)
        self.store.add_embedding("fact", fact_id, embedding, content)

    def index_article_chunk(self, article_id: int, chunk: str):
        """Embed an article chunk (split at ~500 tokens)."""
        embedding = self.embed(chunk)
        self.store.add_embedding("article_chunk", article_id, embedding, chunk)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Find semantically similar content via nearest-neighbor search."""
        query_embedding = self.embed(query)
        return self.store.search_embeddings(query_embedding, top_k=top_k)
```

**When to use which retrieval strategy:**

```
Keyword (FTS5/BM25): "Who is John?" — exact entity lookup
Semantic (vectors):  "concepts related to parallelism in neural networks" — meaning-based
Graph (BFS/path):    "How does John connect to transformers?" — relationship traversal
Web search:          "latest papers on mixture of experts" — external, current info
```

### Web Search (`kuro/retrieval/web.py`)

External search for information not in the knowledge store. Used by query agent (via PTC) and study agent (for finding resources).

```python
import httpx

class WebSearch:
    def __init__(self, api_key: str, provider: str = "tavily"):
        self.api_key = api_key
        self.provider = provider

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web and return structured results."""
        async with httpx.AsyncClient() as client:
            if self.provider == "tavily":
                resp = await client.post("https://api.tavily.com/search", json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": True,
                })
                data = resp.json()
                return [{
                    "title": r["title"],
                    "url": r["url"],
                    "snippet": r["content"],
                    "score": r.get("score", 0)
                } for r in data.get("results", [])]

    def search_sync(self, query: str, max_results: int = 5) -> list[dict]:
        """Sync wrapper for use inside PTC executor."""
        import asyncio
        return asyncio.run(self.search(query, max_results))
```

---

## Phase 4: Context Engineering

### Context Builder (`kuro/context/builder.py`)

Dynamic prompt assembly per agent. Each agent gets different context based on its role, active skills, and memory state.

```python
class ContextBuilder:
    """Assembles the full prompt for each agent invocation."""

    def __init__(self, store: KnowledgeStore, skills_dir: str = "kuro/skills/definitions"):
        self.store = store
        self.skills_dir = skills_dir

    def build(self, agent_name: str, user_message: str, conversation_history: list,
              task_id: str = None, skill_name: str = None) -> dict:
        """
        Build complete context for an agent call.

        Returns: {
            "system_instruction": str,    # Role + tools + memory context
            "messages": list[dict],       # Conversation with compacted history
            "tools": list[dict],          # Tool definitions for this agent
        }
        """
        parts = []

        # 1. Agent role (static per agent)
        parts.append(self._get_agent_role(agent_name))

        # 2. Tier 2: Load skill definition if agent was selected for a specific skill
        if skill_name:
            skill_doc = self._load_skill_definition(skill_name)
            if skill_doc:
                parts.append(f"## Skill Reference\n{skill_doc}")

        # 3. Scratchpad context (Tier 1 memory — current task state)
        if task_id:
            scratchpad = Scratchpad(self.store, task_id)
            scratch_ctx = scratchpad.to_context_string()
            if scratch_ctx:
                parts.append(scratch_ctx)

        # 4. Relevant episodes (Tier 2 memory — past session context)
        episodic_ctx = EpisodicMemory(self.store, None).get_relevant_context(user_message)
        if episodic_ctx:
            parts.append(episodic_ctx)

        # 5. Compact conversation history if needed
        messages = self._maybe_compact(conversation_history)

        return {
            "system_instruction": "\n\n".join(parts),
            "messages": messages,
            "tools": self._get_tools_for_agent(agent_name),
        }

    def _load_skill_definition(self, skill_name: str) -> str | None:
        """Tier 2 progressive disclosure: load full skill doc on demand."""
        path = f"{self.skills_dir}/{skill_name}.md"
        try:
            return open(path).read()
        except FileNotFoundError:
            return None

    def _maybe_compact(self, history: list) -> list:
        """Delegate to compaction module if history exceeds threshold."""
        token_count = estimate_tokens(history)
        if token_count > COMPACTION_THRESHOLD:
            return compact(history)
        return history
```

**How context differs per agent:**

```
Orchestrator: role + SKILL_INDEX (Tier 1 only, ~200 tokens) + no memory
Ingest agent: role + skill definition (Tier 2) + scratchpad + tools
Query agent:  role + skill definition + scratchpad + relevant episodes + PTC namespace docs
Study agent:  role + skill definition + scratchpad + relevant episodes + concept scores + article refs
Code agent:   role + skill definition + scratchpad + tools
```

### Compaction (`kuro/context/compaction.py`)

When conversation history exceeds the token budget, compress older context while preserving key information. Without this, any session longer than ~10 turns will degrade.

```python
# Token thresholds (for Gemini 3.1 Pro with 1M context, but budget conservatively)
TOOL_RESULT_CLEAR_THRESHOLD = 8_000    # Level 1: clear old tool results
TURN_SUMMARIZE_THRESHOLD    = 16_000   # Level 2: summarize old turns
FULL_COMPACTION_THRESHOLD   = 32_000   # Level 3: full compaction

def compact(conversation_history: list[dict], llm=None) -> list[dict]:
    """
    Three levels of compaction, applied progressively.
    Always preserve the most recent 5 turns verbatim.
    """
    token_count = estimate_tokens(conversation_history)

    # Level 1: Tool result clearing (lightest)
    # Replace tool outputs older than 5 turns with one-line summaries
    if token_count > TOOL_RESULT_CLEAR_THRESHOLD:
        conversation_history = clear_old_tool_results(conversation_history, keep_last=5)

    # Level 2: Turn summarization (medium)
    # Summarize turns 1-N into a paragraph, keep last 5 verbatim
    if estimate_tokens(conversation_history) > TURN_SUMMARIZE_THRESHOLD:
        old_turns = conversation_history[:-10]  # everything except last 5 exchanges
        recent_turns = conversation_history[-10:]
        summary = llm.call(messages=[
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": format_turns(old_turns)}
        ])
        conversation_history = [
            {"role": "system", "content": f"## Conversation Summary\n{summary}"},
            *recent_turns
        ]

    # Level 3: Full compaction (heaviest)
    # Generate comprehensive summary preserving critical info
    if estimate_tokens(conversation_history) > FULL_COMPACTION_THRESHOLD:
        summary = llm.call(messages=[
            {"role": "system", "content": FULL_COMPACTION_PROMPT},
            {"role": "user", "content": format_turns(conversation_history)}
        ])
        conversation_history = [
            {"role": "system", "content": f"## Session Context\n{summary}"},
            conversation_history[-2],  # keep only last exchange
            conversation_history[-1],
        ]

    return conversation_history

def clear_old_tool_results(history: list[dict], keep_last: int = 5) -> list[dict]:
    """Replace consumed tool outputs with brief summaries."""
    cutoff = len(history) - (keep_last * 2)
    for i, msg in enumerate(history):
        if i >= cutoff:
            break
        if msg.get("role") == "tool" or msg.get("type") == "tool_result":
            original_len = len(str(msg.get("content", "")))
            msg["content"] = f"[Tool result: {original_len} chars, consumed]"
    return history

# What gets preserved vs discarded:
FULL_COMPACTION_PROMPT = """Summarize this conversation into a compact context block.
PRESERVE:
- Decisions made and their reasoning
- User preferences and corrections
- Current plan or goal
- Unresolved questions
- Key facts learned

DISCARD:
- Raw tool outputs (already processed)
- Redundant back-and-forth
- Exploratory tangents that didn't lead anywhere
- Repeated information"""
```

---

## Phase 5: Agents

### 5a. Ingest Agent (`kuro/agents/ingest.py`)

**Two modes:**
1. **Natural language** — "Met John at the conference, PM at Stripe"
2. **URL** — "Save this: https://..."

**Tools available to ingest agent:**

| Tool | Description |
|------|-------------|
| `extract_entities` | Parse text → entities + types |
| `store_entity` | Write entity to SQLite |
| `store_fact` | Write fact to SQLite |
| `store_relation` | Write relation to SQLite |
| `scrape_url` | Fetch URL → clean HTML → markdown |
| `extract_concepts` | Parse article → concept list |
| `save_article` | Write article markdown to disk |

**System instruction (simplified):**
```
You are Kuro's ingest agent. Your job:
1. If input contains a URL: scrape it, extract concepts, save to disk and DB.
2. If input is natural language: extract entities, facts, and relationships, save to DB.
Always confirm what you saved.
```

**Flow — natural language input:**
```
User: "Met John at the conference. He's a PM at Stripe, interested in our API product."

LLM call 1: Gemini sees input + tools → calls:
  extract_entities("Met John at the conference. He's a PM at Stripe...")
    → returns: [{name: "John", type: "person"}, {name: "Stripe", type: "company"},
                {name: "API product", type: "project"}]

LLM call 2: Gemini sees extraction result → calls:
  store_entity("John", "person", "PM at Stripe")
  store_entity("Stripe", "company", null)
  store_entity("API product", "project", null)

LLM call 3: Gemini sees entity IDs → calls:
  store_fact(john_id, "Met at the conference", "user")
  store_fact(john_id, "PM at Stripe", "user")
  store_relation(john_id, "works_at", stripe_id)
  store_relation(john_id, "interested_in", api_product_id)

LLM call 4: No more tool calls → returns text:
  "Got it. Saved John — PM at Stripe, interested in your API product."
```

**Flow — URL input:**
```
User: "Save this: https://jalammar.github.io/illustrated-transformer/"

LLM call 1: Gemini sees URL → calls:
  scrape_url("https://jalammar.github.io/illustrated-transformer/")
    → returns: {title: "The Illustrated Transformer", content: "...(markdown)...", length: 15000}

LLM call 2: Gemini sees scraped content → calls:
  save_article("The Illustrated Transformer", content, "transformers")
  extract_concepts(content)
    → returns: ["Self-Attention", "Multi-Head Attention", "Positional Encoding",
                "Layer Norm", "Feed-Forward Network", "Encoder-Decoder"]

LLM call 3: Gemini stores each concept as entity + links to article:
  store_entity("Self-Attention", "concept", "...")
  store_entity("Multi-Head Attention", "concept", "...")
  ...
  store_relation("Multi-Head Attention", "part_of", "Self-Attention")

  Also checks existing entities → finds "sequence models" already in DB:
  store_relation("Self-Attention", "related_to", sequence_models_id)

  Embeddings are generated for article chunks and facts (semantic indexing).

LLM call 4: Returns text:
  "Saved. Extracted 6 concepts from 'The Illustrated Transformer'.
   Connected to your existing knowledge on sequence models."
```

---

### 5b. Query Agent (`kuro/agents/query.py`)

**PTC-based multi-strategy retrieval.** The model writes Python that calls all 4 retrieval strategies in one execution instead of N tool-call round trips.

**The agent does NOT use standard tool calls.** Instead, it gets a single `execute_code` tool that runs PTC with these injected functions:

| PTC Function | Description | Strategy |
|-------------|-------------|----------|
| `keyword_search(query)` | FTS5/BM25 over entities + facts | Keyword |
| `semantic_search(query, top_k)` | Vector nearest-neighbor over embeddings | Semantic |
| `graph_traverse(entity_id, depth)` | BFS from an entity through relations | Graph |
| `graph_path(from_id, to_id)` | Shortest path between two entities | Graph |
| `web_search(query, max_results)` | External web search API | Web |
| `read_article(file_path)` | Read saved article markdown | File |

**System instruction:**
```
You are Kuro's query agent. Given a question, write Python code to retrieve the answer.
You have these functions available:
- keyword_search(query) → list of matching entities/facts (exact terms)
- semantic_search(query, top_k=10) → list of semantically similar content
- graph_traverse(entity_id, depth=2) → entity neighborhood
- graph_path(from_id, to_id) → shortest path between entities
- web_search(query, max_results=5) → external web results
- read_article(file_path) → full article text

Write Python code using these functions. Use print() to output results.
Choose the right strategy based on the query type:
- Exact entity lookup → keyword_search
- Meaning/concept search → semantic_search
- Relationship questions → graph_traverse or graph_path
- Current/external info → web_search
- Complex queries → combine multiple strategies

Always cite your sources.
```

**Flow — simple query (still just 2 LLM calls via PTC):**
```
User: "Who did I meet that works at Stripe?"

LLM call 1: Model writes retrieval code:
  execute_code("""
    results = keyword_search("Stripe")
    for r in results:
        if r['type'] == 'entity':
            neighborhood = graph_traverse(r['id'], depth=1)
            print(f"Entity: {r['name']}")
            for rel in neighborhood.get('relations', []):
                if rel['relation_type'] == 'works_at':
                    person = rel['source_name']
                    facts = keyword_search(person)
                    print(f"  - {person} works at {r['name']}")
                    for f in facts:
                        if f['type'] == 'fact':
                            print(f"    Fact: {f['content']}")
  """)
    → captured output:
      "Entity: Stripe
         - John works at Stripe
           Fact: PM at Stripe
           Fact: Met at the conference
           Fact: interested in API product"

LLM call 2: Model reads output → synthesizes:
  "John — PM at Stripe. You met him at the conference.
   He's interested in your API product."
```

**Flow — complex multi-strategy query:**
```
User: "What concepts from my reading are related to things people I've met work on?"

LLM call 1: Model writes a multi-strategy retrieval plan:
  execute_code("""
    # Strategy: combine graph traversal with semantic search
    people = keyword_search("type:person")
    results = []
    for person in people:
        rels = graph_traverse(person['id'], depth=2)
        projects = [r for r in rels.get('relations', [])
                    if r['relation_type'] == 'interested_in']
        for proj in projects:
            # Use semantic search to find related concepts
            related = semantic_search(f"concepts related to {proj['target_name']}", top_k=5)
            if related:
                results.append({
                    'person': person['name'],
                    'project': proj['target_name'],
                    'related_concepts': [r['content'] for r in related]
                })

    for r in results:
        print(f"{r['person']} → {r['project']}:")
        for c in r['related_concepts']:
            print(f"  - {c}")
  """)

LLM call 2: Returns text:
  "John (Stripe) is interested in your API product.
   From your reading, you have related concepts: REST and GraphQL."
```

---

### 5c. Study Agent (`kuro/agents/study.py`)

**Three modes:** discussion, quiz, revision — all in one agent.

**Tools available:**

| Tool | Description |
|------|-------------|
| `get_article_content` | Read a saved article's markdown |
| `get_concepts_for_topic` | Get concepts + confidence scores for a topic |
| `get_due_concepts` | Get concepts due for spaced repetition review |
| `update_confidence` | Update SM-2 scores after quiz answer |
| `save_discussion_summary` | Compact a discussion into a summary fact |
| `web_search` | Find external resources on a topic |

**System instruction:**
```
You are Kuro's study agent. You have three modes:

DISCUSS: The user wants to talk about a topic. Pull their saved articles and concepts.
Ask Socratic questions. Challenge their understanding. Reference specific articles.
At the end, update confidence scores and save a discussion summary.

QUIZ: Pick concepts due for review (spaced repetition). Ask questions at the right
difficulty. Track right/wrong. Update SM-2 scores. Report results.

REVISE: User wants to review weak areas. Find lowest-confidence concepts.
Explain them, then quiz.

PLAN: User wants study resources. Use web_search to find articles, courses,
or tutorials on topics where they're weak.
```

**SM-2 Algorithm (for spaced repetition):**
```python
def sm2_update(concept, quality):
    """
    quality: 0-5 (0=blackout, 5=perfect)
    Updates: easiness, interval, repetitions, next_review
    """
    if quality >= 3:  # correct
        if concept.repetitions == 0:
            concept.interval = 1
        elif concept.repetitions == 1:
            concept.interval = 6
        else:
            concept.interval = round(concept.interval * concept.easiness)
        concept.repetitions += 1
    else:  # incorrect
        concept.repetitions = 0
        concept.interval = 1

    concept.easiness = max(1.3, concept.easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    concept.confidence = quality / 5.0
    concept.next_review = today + timedelta(days=concept.interval)
```

**Flow — discussion mode:**
```
User: "Let's discuss attention mechanisms"

LLM call 1: Study agent loads context:
  get_concepts_for_topic("attention")
    → returns: [
        {name: "Self-Attention", confidence: 0.4, article: "illustrated-transformer.md"},
        {name: "Multi-Head Attention", confidence: 0.2, article: "illustrated-transformer.md"},
        {name: "Positional Encoding", confidence: 0.0, article: "illustrated-transformer.md"}
      ]
  get_article_content("transformers/illustrated-transformer.md")
    → returns: full article text

LLM call 2: Returns Socratic question:
  "You read that multi-head attention uses parallel Q/K/V projections.
   Why would multiple heads be better than one large attention head?"

User answers...

LLM call 3: Evaluates answer, follows up:
  "Good intuition about different representation subspaces.
   But you mentioned that heads attend to different positions —
   can you be more precise about what 'different' means here?"

... (discussion continues, multiple turns) ...
... (compaction kicks in if discussion exceeds token threshold) ...

User: "ok let's wrap up"

LLM call N: Summarizes and updates:
  update_confidence("Self-Attention", quality=4)     # understood well
  update_confidence("Multi-Head Attention", quality=3) # partial
  update_confidence("Positional Encoding", quality=1)  # didn't come up much
  save_discussion_summary("Discussed attention mechanisms. Strong on self-attention
    intuition, partial on multi-head specifics, didn't cover positional encoding.")

Returns: "Good session. You're solid on self-attention but let's dig into
  multi-head mechanics and positional encoding next time."
```

**Flow — quiz mode:**
```
User: "Quiz me"

LLM call 1:
  get_due_concepts()
    → returns: [
        {name: "Positional Encoding", confidence: 0.0, last_reviewed: null},
        {name: "Layer Norm", confidence: 0.2, last_reviewed: "2026-03-10"},
        {name: "Self-Attention", confidence: 0.6, last_reviewed: "2026-03-11"}
      ]

LLM call 2: Returns first question (starts with weakest):
  "Question 1/3: Why do transformers need positional encoding?
   What information would be lost without it?"

User answers...

LLM call 3: Evaluates, updates, asks next:
  update_confidence("Positional Encoding", quality=4)  # good answer
  "Correct! Without positional encoding, attention treats input as a bag of tokens
   with no order information.

   Question 2/3: What does Layer Normalization do, and where is it applied
   in the transformer block?"

... (continues through all due concepts) ...

Final response:
  "Results: 2/3 correct.
   ✓ Positional Encoding — solid, next review in 6 days
   ✗ Layer Norm — review in 1 day
   ✓ Self-Attention — next review in 12 days"
```

**Flow — study planning with web search:**
```
User: "Find me good resources on positional encoding"

LLM call 1: Study agent checks current knowledge:
  get_concepts_for_topic("positional encoding")
    → returns: [{name: "Positional Encoding", confidence: 0.2}]

  web_search("positional encoding transformers tutorial explanation")
    → returns: [
        {title: "Positional Encoding in Transformers - Machine Learning Mastery", url: "..."},
        {title: "The Annotated Transformer", url: "..."},
        {title: "A Gentle Introduction to Positional Encoding", url: "..."}
      ]

LLM call 2: Returns curated recommendations:
  "Your confidence on positional encoding is low (0.2). Here are resources
   ordered by complexity:
   1. 'A Gentle Introduction to Positional Encoding' — start here
   2. 'Positional Encoding in Transformers' (ML Mastery) — deeper math
   3. 'The Annotated Transformer' — full implementation
   Want me to save any of these for study?"
```

---

### 5d. Code Agent (`kuro/agents/code.py`)

This is the existing `agent.py` logic, wrapped to match the new agent interface.

**Tools:** `shell`, `read_file`, `edit_file`, `create_file` (same as current)

No changes to behavior — just refactored to be callable by the orchestrator.

---

### 5e. Orchestrator (`kuro/agents/orchestrator.py`)

**Three-tier progressive disclosure:**

```
Tier 1: SKILL_INDEX — names + triggers (~200 tokens total)
  → Orchestrator sees this to classify input
  → Minimal context, fast classification

Tier 2: skills/definitions/*.md — full skill documentation
  → Loaded when agent is selected for a specific skill
  → Agent reads its skill file to understand detailed instructions
  → Example: study agent loads study_discussion.md for discussion mode

Tier 3: Referenced data files — articles, code files, etc.
  → Skill definitions reference data files the agent can read on demand
  → Example: study_discussion.md says "load the relevant article from data/articles/"
  → Agent calls read_article() to pull the actual content
```

**The skill registry (Tier 1):**

```python
SKILL_INDEX = {
    "STORE": {
        "name": "Knowledge Storage",
        "triggers": "User shares facts, people, events, information to remember",
        "agent": "ingest",
        "skill_file": "knowledge_storage"
    },
    "INGEST": {
        "name": "Article Ingestion",
        "triggers": "User shares a URL or article text to save and analyze",
        "agent": "ingest",
        "skill_file": "article_ingestion"
    },
    "QUERY": {
        "name": "Knowledge Retrieval",
        "triggers": "User asks a question about something they've stored",
        "agent": "query",
        "skill_file": "knowledge_retrieval"
    },
    "DISCUSS": {
        "name": "Study Discussion",
        "triggers": "User wants to discuss, explore, or understand a topic",
        "agent": "study",
        "skill_file": "study_discussion"
    },
    "QUIZ": {
        "name": "Quiz & Review",
        "triggers": "User wants to be quizzed or review material",
        "agent": "study",
        "skill_file": "quiz_review"
    },
    "CODE": {
        "name": "Code & Shell",
        "triggers": "User wants to run commands, edit files, or do code tasks",
        "agent": "code",
        "skill_file": "code_assistance"
    }
}
```

**Example Tier 2 skill file (`skills/definitions/knowledge_retrieval.md`):**

```markdown
# Knowledge Retrieval Skill

## When to use
User asks about stored knowledge, wants to find connections, or needs information retrieval.

## Available retrieval strategies
1. **Keyword search** — exact entity/fact lookup via FTS5
2. **Semantic search** — meaning-based via embeddings
3. **Graph traversal** — relationship navigation via BFS
4. **Web search** — external info when local knowledge is insufficient

## How to decide
- Named entities → keyword first
- Conceptual/vague queries → semantic first, fall back to keyword
- "How does X relate to Y?" → graph path
- "What's the latest on X?" → web search

## Referenced data
- Articles are stored in `data/articles/<topic>/<title>.md`
- Use `read_article(path)` to load full content when needed
```

**Orchestrator system instruction:**
```
You are Kuro's orchestrator. Classify the user's input into one category:
STORE, INGEST, QUERY, DISCUSS, QUIZ, or CODE.

You see only skill names and triggers, not full implementations.
Respond with ONLY the category name. Nothing else.
```

**Flow:**
```
User: "Met John at the conference. He's a PM at Stripe."

Step 1 — Orchestrator classifies (Tier 1):
  Input: user message + SKILL_INDEX (names + triggers only)
  LLM call (cheap/fast model): → "STORE"

Step 2 — Context builder assembles agent prompt (Tier 2):
  Loads skills/definitions/knowledge_storage.md
  Loads scratchpad for current task
  Loads relevant episodes
  Builds full system instruction

Step 3 — Ingest agent runs with full context:
  Agent executes its tool-call loop (see Phase 5a)
  Writes to scratchpad during execution

Step 4 — Cleanup:
  Scratchpad cleared
  Response returned to user
```

The orchestrator is a single cheap LLM call — just classification. The context builder assembles the right context. The specialist agent does all the real work.

---

## Phase 6: Web UI

### FastAPI Backend (`kuro/web/app.py`)

```python
# Endpoints:
POST /chat              # Send message → get response (SSE stream)
GET  /knowledge         # View entities + relations (for demo)
GET  /concepts          # View concepts + confidence scores (for demo)
GET  /                  # Serve chat UI
```

### Chat UI (`kuro/web/static/index.html`)

Single HTML file with inline CSS/JS. No build step, no framework.

```
+------------------------------------------+
|  Kuro                                    |
+------------------------------------------+
|                                          |
|  You: Met John at the conference...      |
|                                          |
|  Kuro: Got it. Saved John — PM at        |
|  Stripe, interested in your API product. |
|                                          |
|  You: Save this: https://jalammar...     |
|                                          |
|  Kuro: Saved. Extracted 6 concepts...    |
|                                          |
+------------------------------------------+
| [Type a message...]            [Send]    |
+------------------------------------------+
```

- Messages sent via `fetch()` to `/chat`
- Responses streamed via SSE (Server-Sent Events)
- Conversation history maintained server-side (in-memory per session)
- Compaction runs automatically when history exceeds token threshold
- Session end triggers episode generation
- Simple, functional — no bells and whistles

---

## Phase 7: Wiring It All Together

### `kuro/config.py`
```python
import os
from pathlib import Path

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.1-pro-preview"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # For web search

# Paths
DATA_DIR = Path("kuro/data")
DB_PATH = DATA_DIR / "kuro.db"
ARTICLES_DIR = DATA_DIR / "articles"
SKILLS_DIR = Path("kuro/skills/definitions")

# Compaction thresholds
COMPACTION_L1_TOKENS = 8_000
COMPACTION_L2_TOKENS = 16_000
COMPACTION_L3_TOKENS = 32_000

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim, ~80MB
```

### Entry Point (updated `main.py`)
```python
from kuro.web.app import create_app
import uvicorn

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Request Lifecycle
```
Browser → POST /chat {message: "Who works at Stripe?"}
  → app.py receives request
  → creates/loads session (with session_id for episodic memory)
  → orchestrator.classify(message) → "QUERY" (Tier 1: skill index only)
  → context_builder.build("query", message, history, task_id, "knowledge_retrieval")
    → loads Tier 2 skill definition
    → loads scratchpad (Tier 1 memory)
    → loads relevant episodes (Tier 2 memory)
    → checks if compaction needed
  → query_agent.run(context)
    → model writes PTC code using injected retrieval functions
    → execute_ptc runs: keyword_search + semantic_search + graph_traverse
    → model synthesizes results into answer
  → scratchpad cleared for this task
  → streams response back to browser via SSE
  → appends to conversation history
  → if session ending: episodic.generate_episode(session_id, history)
```

---

## Dependencies

```toml
# In pyproject.toml:
dependencies = [
    "fastapi>=0.135.1",
    "uvicorn>=0.41.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0",        # URL scraping
    "httpx>=0.27.0",                 # Async HTTP for scraping + web search
    "markdownify>=0.14.0",           # HTML → Markdown conversion
    "sse-starlette>=2.0.0",          # SSE streaming for FastAPI
    "pydantic>=2.0",                 # Data models
    "sentence-transformers>=3.0.0",  # Embedding generation (all-MiniLM-L6-v2)
    "sqlite-vec>=0.1.0",             # Vector search in SQLite (no separate DB)
]
```

No langchain. No heavy vector DB. sqlite-vec keeps everything in one SQLite file.

---

## What Gets Built In What Order

| Step | What | Why First |
|------|------|-----------|
| 1 | `config.py` + `core/llm.py` | Shared infra, provider-agnostic client |
| 2 | `core/ptc.py` | PTC executor used by query + study agents |
| 3 | `core/types.py` | Pydantic models shared across modules |
| 4 | `memory/store.py` (with scratchpad + episodes + embeddings tables) | Full 3-tier memory foundation |
| 5 | `memory/files.py` | Article storage for ingest + study |
| 6 | `memory/scratchpad.py` + `memory/episodic.py` | Working memory + session summaries |
| 7 | `retrieval/semantic.py` | Vector search (depends on store + embeddings) |
| 8 | `retrieval/web.py` | Web search wrapper |
| 9 | `context/builder.py` + `context/compaction.py` | Context engineering (depends on memory + retrieval) |
| 10 | `skills/registry.py` + `skills/definitions/` | 3-tier progressive disclosure |
| 11 | `agents/ingest.py` | Data ingestion (can't query without data) |
| 12 | `agents/query.py` (PTC-based) | Multi-strategy retrieval |
| 13 | `agents/study.py` | Discussion + quiz + SM-2 + web search |
| 14 | `agents/code.py` | Shell/file ops (wrap existing agent.py) |
| 15 | `agents/orchestrator.py` | Routes to all agents via skill index |
| 16 | `web/app.py` + `static/index.html` | UI layer last |

Each step is independently testable from the CLI before the web UI exists.

---

## Technique Coverage

Every technique from kuro-plan.md and agent-plan.md is exercised:

| Technique | Where It Lives | Interview Talking Point |
|-----------|---------------|------------------------|
| **PTC** | `core/ptc.py`, query agent writes Python | "2 model calls instead of N round trips. The model orchestrates 4 retrieval strategies in one code block." |
| **Multi-Agent Orchestration** | Orchestrator + 5 specialists | "One coordinator classifies and routes. Each agent has its own context, tools, and scratchpad." |
| **Three-Tier Memory** | scratchpad (task) + episodes (session) + facts (permanent) | "Scratchpad per task, episode summaries per session, extracted facts forever. SQLite because Letta showed filesystem beats vector stores at 74%." |
| **4-Strategy Retrieval** | FTS5 + semantic + graph + web | "BM25 for exact match, vectors for meaning, graph for relationships, web for current info. Agent decides which in code." |
| **Graph RAG** | `store.traverse()` + `store.find_path()` | "Entity graph in SQLite with BFS traversal and shortest-path queries." |
| **Progressive Disclosure (3 tiers)** | Tier 1: SKILL_INDEX → Tier 2: skill files → Tier 3: data files | "Same pattern as Claude Code's 20 tools + Microsoft's 132-skill framework. Agents discover capabilities on demand." |
| **Compaction (3 levels)** | `context/compaction.py` | "Tool-result clearing → turn summarization → full compaction. Preserves decisions, discards raw outputs." |
| **Context Builder** | `context/builder.py` | "Dynamic prompt assembly. Each agent gets different context: different tools, memory scope, skill definitions." |
| **Semantic Search** | `retrieval/semantic.py` + sqlite-vec | "sentence-transformers for embeddings, sqlite-vec for nearest-neighbor — all in one SQLite file." |
| **Web Search** | `retrieval/web.py` | "Study agent can find new resources. Query agent falls back to web when local knowledge is insufficient." |
| **Provider-Agnostic LLM** | `core/llm.py` with AGENT_MODELS | "Cheap model for orchestrator classification, strong model for study dialogue. Swap providers per agent." |
| **Spaced Repetition (SM-2)** | Study agent + concepts table | "Full SM-2 algorithm tracking easiness, intervals, and repetitions per concept." |
| **Code Sandbox** | `agents/code.py` + PTC's restricted exec | "Model-generated code runs in restricted exec() with injected functions. Shell through srt sandbox." |
| **Tool-Call Agent Loop** | `core/llm.py` call_with_tools | "Standard tool-call protocol for ingest/study. PTC for query agent." |

### Tool Evolution Story (from Claude Code blog)

Be prepared to discuss how tools evolve as models improve:

```
v1 (tool calls):  Query agent uses search_keyword, graph_traverse as separate tools.
                   4 round trips for a complex query.

v2 (PTC):         Query agent writes Python orchestrating all retrieval in one exec.
                   2 total model calls. The model IS the orchestration logic.

v3 (future):      As models get better at long-horizon planning, PTC code gets more
                   sophisticated — multi-step retrieval with conditionals, error handling,
                   and result fusion. The tool stays the same, the code quality improves.
```

This mirrors Claude Code's evolution: TodoWrite → Tasks when models got better at subagent coordination. The principle: "Revisit tools as models improve."
