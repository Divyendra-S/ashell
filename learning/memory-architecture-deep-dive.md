# AI Agent Memory Architecture: Complete Deep Dive

How Claude Code, OpenAI, Mem0, and Letta handle memory — and how Kuro implements it.

---

## The Core Problem

LLMs have **amnesia**. Every conversation starts blank. Without memory:
- User says "I'm a Python developer" in session 1
- Session 2: agent has no idea who they are

Memory solves this by **persisting information across sessions** and **loading the right context** at the right time.

---

## The 4 Memory Types (from Cognitive Science)

Every good memory system implements some version of these:

### 1. Working Memory (RAM)
**What**: The current conversation — what you're actively thinking about.

```
User: "Explain React hooks"
Agent thinking: [user's message + system prompt + retrieved context]
```

**Who handles it**: The LLM's context window itself. No persistence needed. In Kuro, this is Gemini's `contents` list that grows during a conversation.

**No system builds this** — it's just the context window.

### 2. Semantic Memory (Encyclopedia)
**What**: Facts, knowledge, definitions. **Decontextualized** — doesn't matter when you learned it.

```
"React is a JavaScript library created by Meta"
"PostgreSQL is a relational database"
"Distributed consensus requires >50% agreement"
```

**How Claude Code does it**: Doesn't — it's a coding tool, not a knowledge base.

**How Kuro does it**: The full knowledge graph in Supabase:
```
entities -> facts -> relations -> articles -> article_chunks (with embeddings)
```

This is Kuro's **unique strength** — most memory systems don't have a structured knowledge graph.

### 3. Episodic Memory (Diary)
**What**: Specific events with **timestamps and context**. Decays over time.

```
"User scored 2/5 on React on March 15, 2026"
"User asked about Kubernetes yesterday"
"Study session: hooks were the weak area"
```

**How Claude Code does it**: MEMORY.md topic files with `project` type memories:
```markdown
---
name: auth_rewrite
type: project
---
Auth middleware rewrite driven by legal/compliance.
**Why:** Session token storage doesn't meet new requirements.
```

**How Kuro does it**: Two places —
1. **Skill data JSONL** (detailed logs): `data/skill_data/div/study/sessions.jsonl`
2. **User memories** with type `context`: summaries in Supabase for quick access

The **cross-reference pattern** bridges them:
```
Detailed log (JSONL):  {"topic": "React", "score": "2/5", "date": "2026-03-15", "weak_areas": ["hooks"]}
     | agent also saves |
Summary (Supabase):    name="study_react_latest", content="Scored 2/5 on React. Weak: hooks."
```

### 4. Procedural Memory (Muscle Memory)
**What**: How to do things — workflows, standing instructions, learned behaviors.

```
"Always check deployment guide before pushing"
"When user asks about databases, mention PostgreSQL first"
"Use the /explain skill for low study scores"
```

**How Claude Code does it**: `feedback` memories — corrections AND confirmations:
```markdown
---
name: no_mocking_db
type: feedback
---
Integration tests must hit real database, not mocks.
**Why:** Mocked tests passed but prod migration failed last quarter.
**How to apply:** Any test touching DB schemas.
```

**How Kuro does it**: User memories with type `instruction` (importance=9-10):
```python
save_memory(name="database_preference", type="instruction", importance=9,
            content="Always mention PostgreSQL first when asked about databases")
```

---

## The Two Architecture Patterns

Every system uses one of these:

### Pattern A: File-Based (Claude Code)

```
~/.claude/projects/<project>/memory/
|-- MEMORY.md              <-- Index (always loaded, first 200 lines)
|-- user_role.md           <-- Topic file (loaded on demand)
|-- feedback_testing.md
|-- project_auth.md
```

**How it works**:
1. MEMORY.md is **always loaded** at conversation start
2. Topic files are **read on demand** when relevant
3. Claude **writes** memories proactively during conversation
4. Each file has frontmatter: `name`, `description`, `type`

**Strengths**: Simple, git-friendly, human-readable
**Weaknesses**: Single-user only, no search, no scoring, doesn't scale

### Pattern B: Database-Backed (Mem0, Kuro)

```
+----------------------------------+
|      CORE (Always Loaded)        |
|  Profile + Top N Memories        |
+----------------------------------+
|      ARCHIVAL (On Demand)        |
|  All memories + KB + Skill data  |
|  Accessed via search tools       |
+----------------------------------+
```

**How it works**:
1. On every query, load **profile + top 10 memories** (scored by importance x recency)
2. Rest of memories available via `search_memories` tool
3. Knowledge base available via retrieval tools
4. Agent writes memories via `save_memory` tool calls

**Strengths**: Multi-user, searchable, scored, scales to thousands of memories
**Weaknesses**: More complex, requires DB infrastructure

**Kuro uses Pattern B** — which is the right choice for a web app.

---

## The 6 Key Techniques

### Technique 1: Importance Scoring

**Problem**: Not all memories are equal. "Always verify before deploying" matters more than "mentioned liking coffee."

**How Claude Code does it**: Doesn't. All memories are flat.

**How Mem0 does it**: Internal scoring based on frequency of access and relevance.

**How Kuro does it**: Agent assigns importance at save time:
```
9-10: Critical instructions ('never do X')
7-8:  Strong preferences ('I prefer short answers')
5-6:  Useful context ('studying React')
3-4:  Casual facts ('mentioned liking Python')
1-2:  Ephemeral notes ('debugging auth today')
```

The `save_memory` tool has an `importance` parameter:
```json
{
  "name": "save_memory",
  "args": {
    "name": "database_preference",
    "type": "instruction",
    "content": "Always mention PostgreSQL first",
    "importance": 9
  }
}
```

### Technique 2: Selective Retrieval (Core vs Archival)

**Problem**: Loading ALL memories into the system prompt wastes context and dilutes relevance.

**How Letta/MemGPT does it**:
- **Core memory** (always in context): persona + human summary + working state
- **Archival memory** (on demand): agent calls `archival_memory_search` tool

**How Kuro does it**: Same pattern —
```python
# In query(), we load only top 10:
memories = store.get_top_memories(user_id, limit=10)  # scored by importance x recency

# Scoring formula:
score = importance * recency_weight
# recency_weight: 1.0 (<7 days), 0.8 (<30 days), 0.5 (<90 days), 0.3 (older)
```

The rest are accessible via `search_memories` tool:
```json
{"name": "search_memories", "args": {"query": "React study progress"}}
```

### Technique 3: Temporal Decay

**Problem**: "User is debugging auth" from 6 months ago shouldn't affect today's conversation.

**How it works in Kuro**:
```python
def _recency_weight(updated_at):
    age_days = (now - updated_at).days
    if age_days < 7:   return 1.0   # Full weight
    if age_days < 30:  return 0.8   # Slightly faded
    if age_days < 90:  return 0.5   # Half weight
    return 0.3                       # Mostly faded
```

A memory with importance=9 scores:
- Today: 9 x 1.0 = **9.0**
- 2 weeks later: 9 x 0.8 = **7.2**
- 3 months later: 9 x 0.5 = **4.5**
- 1 year later: 9 x 0.3 = **2.7**

So high-importance instructions stay relevant longer, but casual context naturally fades.

Kuro also supports **explicit expiration**:
```json
{
  "name": "save_memory",
  "args": {
    "name": "debugging_auth",
    "content": "Currently debugging auth flow",
    "importance": 3,
    "expires_at": "2026-03-23T00:00:00Z"
  }
}
```

### Technique 4: Auto-Consolidation (the Mem0 pattern)

**Problem**: After 5 study sessions, you have 5 separate memories. They should be one evolving summary.

**How Mem0 does it**: At the storage layer — when you save a memory similar to an existing one, it auto-merges.

**How Kuro does it**: Same approach — embedding-based dedup on every save:

```
save_memory("react_hooks_study", "Studying React hooks in depth")
  |
  |-- 1. embed_text("Studying React hooks in depth") -> [0.12, -0.34, ...]
  |
  |-- 2. match_memories(embedding, threshold=0.70) via pgvector
  |       -> Found: "react_learning" with similarity 0.91
  |
  |-- 3. Similarity > 0.85 -> AUTO-MERGE
  |       -> Delete "react_learning"
  |       -> Keep higher importance from both
  |       -> Save "react_hooks_study" with new embedding
  |
  |-- Return: {"consolidated_from": [{"name": "react_learning", "action": "merged"}]}
```

The thresholds:
- **> 0.85**: Auto-merge — memories are about the same thing
- **0.70-0.85**: Conflict resolution — if same type, newer wins
- **< 0.70**: Unrelated — save as new

This is **transparent** to the agent. It just calls `save_memory` and the store layer handles dedup.

### Technique 5: Progressive Disclosure (the Claude Code pattern)

**Problem**: You can't fit everything into the system prompt. But you need a summary always available.

**How Claude Code does it**: MEMORY.md (200-line index, always loaded) -> topic files (read on demand).

**How Kuro does it**: Three levels —

```
Level 1: User Profile (always loaded)
  "Python & Go Developer, Distributed Systems, prefers PostgreSQL"
  -> Markdown file at data/user_profiles/{user_id}/profile.md
  -> Agent maintains it, updates sparingly

Level 2: Top 10 Memories (always loaded)
  -> Scored by importance x recency
  -> Injected into system prompt

Level 3: Everything Else (on demand)
  -> All memories via search_memories tool
  -> Knowledge base via retrieval tools
  -> Skill data via read_skill_data tool
```

The agent sees Level 1 + 2 in every conversation. If it needs more, it uses tools to access Level 3.

### Technique 6: Proactive Saving (the key differentiator)

**Problem**: Users don't say "remember this." The agent needs to detect what's worth saving.

**How Claude Code does it**: Auto-memory — Claude writes to MEMORY.md proactively. But it's triggered by a system instruction, not by the user.

**How Kuro does it**: The system prompt instructs the agent to save proactively:
```
When the user shares personal preferences, context about themselves, or
standing instructions, save them using save_memory. Do this proactively —
you don't need to be explicitly asked.
```

In practice, the user says "I'm a Python developer" and the agent auto-saves:
- `user_background` (context, importance=7)
- `response_preference` (preference, importance=8)
- Creates a profile document

Then when the user says "I also do Go," the agent **updates** the existing memory (upsert) and the profile.

---

## The Complete Flow (What Happens on Every Message in Kuro)

```
User sends message: "Tell me about Kubernetes"
  |
  v
1. CLASSIFY: Is this query or ingest?
   -> "Tell me about..." -> query mode
  |
  v
2. LOAD CONTEXT (before Gemini sees anything):
   |-- get_top_memories(user_id, limit=10)
   |     -> Top 10 memories by importance x recency
   |     -> Expired memories filtered out
   |
   |-- read_user_profile(user_id)
   |     -> Living markdown summary
   |
   |-- hybrid_retrieve(queries)
   |     -> FTS across entities/facts/articles
   |     -> Vector search across article chunks
   |     -> RRF merge -> top 8 results
   |
   |-- get_skill_index()
       -> Available skill descriptions for auto-detection
  |
  v
3. BUILD SYSTEM PROMPT:
   +----------------------------------------+
   | ## User Profile                        |
   | {profile markdown}                     |
   |                                        |
   | ## Your Memory (top 10)                |
   | ### Instructions                       |
   | - database_preference: Always mention  |
   |   PostgreSQL first [importance=9]      |
   | ### Preferences                        |
   | - response_preference: Detailed with   |
   |   code examples [importance=8]         |
   | ### Contexts                           |
   | - user_background: Python & Go dev     |
   |   [importance=8]                       |
   |                                        |
   | ## Retrieved Context                   |
   | {KB results about Kubernetes}          |
   |                                        |
   | ## Memory Management Instructions      |
   | {importance levels, consolidation...}  |
   +----------------------------------------+
  |
  v
4. GEMINI PROCESSES -> may call tools:
   |-- save_memory -> upsert_user_memory()
   |     |-- Embed content (768-dim)
   |     |-- Search for similar memories (pgvector)
   |     |-- Auto-merge if similarity > 0.85
   |     |-- Resolve conflicts if 0.70-0.85
   |     |-- Save with embedding
   |
   |-- update_profile -> write markdown to disk
   |
   |-- search_memories -> find older/lower-priority memories
   |
   |-- get_facts_for_entity -> drill into KB
   |
   |-- Text response to user
  |
  v
5. NEXT SESSION: All saved memories + profile are automatically
   loaded into context. User never needs to do anything.
```

---

## Where the Data Lives

| What | Where | Why |
|------|-------|-----|
| **User memories** (scored facts) | Supabase `user_memories` table | Queryable, scored, searchable, multi-user, has embeddings |
| **User profile** (living summary) | Disk `data/user_profiles/{user_id}/profile.md` | Progressive disclosure — always-loaded overview |
| **Skill data** (detailed logs) | Disk `data/skill_data/{user_id}/{skill}/` JSONL | Append-only audit trail, analyzed by helper tools |
| **Knowledge base** | Supabase (entities, facts, relations, articles, chunks) | Structured semantic memory with FTS + vector search |
| **Memory embeddings** | Supabase `user_memories.embedding` column (768-dim) | Auto-consolidation via pgvector cosine similarity |

---

## Memory Schema (user_memories table)

```sql
user_id          text        -- Multi-user isolation
name             text        -- Unique per user, used for upsert
type             text        -- 'preference' | 'context' | 'instruction'
content          text        -- The memory content
importance       integer     -- 1-10, used for scoring/retrieval
source           text        -- 'agent' | 'user' | 'skill'
embedding        vector(768) -- For auto-consolidation (pgvector)
updated_at       timestamptz -- For temporal decay scoring
last_accessed_at timestamptz -- Access tracking
access_count     integer     -- Usage tracking
expires_at       timestamptz -- Optional TTL for ephemeral memories
```

---

## Kuro vs The Industry

| Technique | Claude Code | Mem0 | Letta | ChatGPT | **Kuro** |
|-----------|------------|------|-------|---------|----------|
| Proactive saving | Yes | Yes | Yes | Partial | **Yes** |
| Importance scoring | No | Internal | No | No | **Yes (1-10)** |
| Temporal decay | No | Yes | No | No | **Yes** |
| Core/archival split | Yes (200 lines) | Yes | Yes (RAM/disk) | No | **Yes (top 10 + search)** |
| Auto-consolidation | Partial (hooks) | Yes (storage layer) | No | No | **Yes (embeddings)** |
| Conflict resolution | Manual verify | Yes | No | Belief updates | **Yes (auto-replace)** |
| Semantic memory search | No | Yes (vector) | Yes | No | **Yes (pgvector)** |
| Progressive disclosure | Yes (index -> files) | N/A | Yes (core -> archival) | No | **Yes (profile -> memories -> KB)** |
| Knowledge graph | No | Graph DB | No | No | **Yes (entities/facts/relations)** |
| Multi-user | No (CLI) | Yes | Yes | Yes | **Yes** |
| Expiring memories | No | No | No | No | **Yes (expires_at)** |

---

## Key Takeaways

1. **Memory is not one thing** — it's 4 types (working, semantic, episodic, procedural) that serve different purposes
2. **Core vs archival** is the most important architectural decision — always load a summary, retrieve details on demand
3. **Importance scoring + temporal decay** prevent memory bloat and keep context relevant
4. **Auto-consolidation at the storage layer** (not the agent level) is the most reliable way to prevent duplicates
5. **Proactive saving** is what makes memory feel magical — users shouldn't need to say "remember this"
6. **The agent should manage its own memory** (Letta's insight) — give it tools to read, write, search, and delete memories
7. **For web apps, use database-backed storage** — files don't scale for concurrency and multi-tenancy

---

## Sources

- Claude Code: memory system docs, auto-memory, MEMORY.md
- Mem0: mem0.ai, research paper (arXiv:2504.19413), 26% accuracy improvement
- Letta/MemGPT: docs.letta.com, OS-paradigm memory architecture
- IBM: "What Is AI Agent Memory?"
- Machine Learning Mastery: "3 Types of Long-term Memory AI Agents Need"
- Oracle: "Agent Memory: Why Your AI Has Amnesia and How to Fix It"
- MongoDB: "What Is Agent Memory?"
- Leonie Monigatti: "Making Sense of Memory in AI Agents"
