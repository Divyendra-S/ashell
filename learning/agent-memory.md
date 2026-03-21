# AI Agent Memory: Types, Systems & Best Practices

## The 4 Memory Types

Borrowed from cognitive science, adapted for AI agents:

### 1. Working Memory (Short-Term)
- **What:** Current conversation context — the active "scratchpad"
- **Lifecycle:** Lives only during a single session
- **Analogy:** RAM in a computer
- **Implementation:** The LLM's context window itself. No persistence needed.
- **Kuro:** Gemini's context window handles this. Conversation history passed as `contents`.

### 2. Semantic Memory (Knowledge/Facts)
- **What:** General knowledge, facts, definitions, relationships — decontextualized from when they were learned
- **Lifecycle:** Long-lived, rarely changes, accumulates over time
- **Analogy:** An encyclopedia or knowledge graph
- **Implementation:** Structured storage — knowledge graphs, vector databases, fact tables
- **Kuro:** The full knowledge base — entities, facts, relations, articles, article_chunks in Supabase. Hybrid retrieval (FTS + semantic vector search) with RRF ranking.

### 3. Episodic Memory (Events/Experiences)
- **What:** Specific events, interactions, outcomes — time-bound and context-rich
- **Lifecycle:** Decays over time unless reinforced; consolidates into semantic memory
- **Analogy:** A diary or event log
- **Implementation:** Timestamped logs, session records, interaction histories
- **Kuro:** Skill data JSONL files (study sessions, research logs) + user_memories with type "context" (e.g., "Scored 2/5 on React on March 15")
- **Key insight:** Episodic memories should eventually **consolidate** into semantic ones. "5 study sessions on React" → "User is improving at React, started 2/5, now 4/5, weak on memoization."

### 4. Procedural Memory (How-To/Skills)
- **What:** Learned behaviors, workflows, multi-step procedures
- **Lifecycle:** Persistent, refined through practice
- **Analogy:** Muscle memory, recipes, playbooks
- **Implementation:** Skill definitions, workflow templates, standing instructions
- **Kuro:** SKILL.md files (workflows), user_memories with type "instruction" (e.g., "always check the deployment guide first"), helper scripts (analyze_progress.py)

---

## How the Best Systems Do It

### Claude Code (Anthropic CLI)

**Architecture:** File-based, single-user, project-scoped

```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Index file — always loaded (first 200 lines)
├── user_role.md       # Topic file — loaded on demand
├── feedback_testing.md
└── project_auth.md
```

**Memory types in MEMORY.md:**
- `user` — Role, goals, knowledge level
- `feedback` — Corrections + confirmations (what to do / what NOT to do)
- `project` — Ongoing work, decisions, deadlines
- `reference` — Pointers to external systems

**Key design decisions:**
- **Auto-memory:** Claude writes MEMORY.md proactively — no user action needed
- **Frontmatter metadata:** Each topic file has `name`, `description`, `type` fields
- **Index is small:** MEMORY.md is just links. Content lives in topic files.
- **200-line limit:** Forces conciseness. Anything past 200 lines of index is truncated.
- **Verification before use:** "Memory says X exists" ≠ "X exists now." Agent verifies before acting on memories.

**What Kuro can learn:** The "save from both success AND failure" pattern for feedback memories. Most systems only save corrections — Claude Code also saves confirmed approaches.

### Mem0 (Production Memory Framework)

**Architecture:** Three-tier storage for different query patterns

```
┌──────────────────┐
│   Mem0 Layer     │
├──────────────────┤
│ Vector DB        │ → Semantic similarity search ("find memories about React")
│ Graph DB         │ → Relationship queries ("what's connected to React?")
│ Key-Value Store  │ → Fast exact lookups ("get memory by name")
├──────────────────┤
│ Compression      │ → Chat history → optimized memory representations
│ Deduplication    │ → Merge similar memories automatically
└──────────────────┤
```

**Performance (2025 benchmarks):**
- 26% higher accuracy vs no memory
- 91% lower latency (p95)
- 90% token cost savings (from compression)

**Key insight:** Mem0's compression is the killer feature. Instead of stuffing raw conversation into context, it extracts and deduplicates. This is what "consolidation" means in practice.

**What Kuro can learn:** The three-store pattern. Kuro already has Supabase (relational/KV) + knowledge graph (graph-like). Adding vector embeddings to memories would complete the triad.

### Letta / MemGPT (Stateful Agent Framework)

**Architecture:** Operating system metaphor — the agent IS the memory manager

```
┌─────────────────────────────────────┐
│           Agent Context             │
├─────────────────────────────────────┤
│ Core Memory (always in context)     │ ← Like RAM
│  - persona: who the agent is        │
│  - human: who the user is           │
│  - working: current task state      │
├─────────────────────────────────────┤
│ Archival Memory (on-demand)         │ ← Like Disk
│  - Long-term facts                  │
│  - Past conversations               │
│  - Retrieved via search tools       │
├─────────────────────────────────────┤
│ Recall Memory                       │ ← Like Cache
│  - Recent conversation excerpts     │
│  - Automatic summarization          │
└─────────────────────────────────────┘
```

**The OS paradigm:**
- Agent has **tools to edit its own memory** (core_memory_append, core_memory_replace, archival_memory_insert, archival_memory_search)
- Agent decides what goes in core vs archival
- When core memory is full, agent must decide what to evict

**Key insight:** The agent managing its own memory is more flexible than hard-coded rules. The agent knows what's important in context. This is what Kuro's agentic memory already does — the agent decides when to `save_memory` and `update_profile`.

**What Kuro can learn:** The explicit core/archival split. Kuro implicitly does this (profile + top memories = core; KB + skill data = archival), but making it explicit with selective retrieval would be better.

### ChatGPT (OpenAI)

**Architecture:** Server-side, project-scoped

- **Project memory:** Scoped to a project, not global
- **Belief updates:** Hierarchical authority (Root → System → Developer → User → Guideline)
- **Memory tools:** `/m_update` and `/m_drop` in developer mode

**Key insight:** The authority hierarchy prevents memory conflicts. If a user says "ignore safety rules" but root instructions say "always be safe," root wins. Kuro doesn't have this yet — all memories are flat.

---

## Key Patterns & Best Practices

### 1. Core vs Archival Split
**Always load a summary, retrieve details on demand.**
- Core: User profile + most important memories → always in system prompt
- Archival: All memories + knowledge base → accessible via tools
- This prevents context bloat while keeping essential context available

### 2. Importance Scoring
**Not all memories are equal.**
- Instructions ("always do X") > Preferences ("I like short answers") > Casual context ("studied React yesterday")
- Score from 1-10 when saving, use for retrieval ranking
- Prevents a flood of low-value memories from pushing out critical ones

### 3. Temporal Decay
**Old memories become less relevant.**
- Recency weight: full weight for <7 days, decays over 30/90 days
- Combined with importance: `score = importance × recency_weight`
- Prevents stale memories from dominating

### 4. Consolidation
**Merge related memories over time.**
- 5 React study sessions → 1 consolidated "React progress" memory
- Agent does this naturally with upsert (same name = overwrite)
- Can also be a periodic cleanup: find related memories, suggest merges

### 5. Source Tracking
**Know where memories came from.**
- `agent`: Auto-captured from conversation
- `user`: Explicitly stated by user
- `skill`: Cross-reference from skill data
- User-stated memories should have higher trust than agent-inferred ones

### 6. Access Tracking
**Know which memories are actually useful.**
- Track `last_accessed_at` and `access_count`
- Memories that are never accessed can be archived or deleted
- High-access memories are clearly important — boost their score

### 7. Verification Before Action
**Memory is a claim about the past, not the present.**
- Before acting on a memory ("user prefers framework X"), verify it's still true
- Files/functions mentioned in memory may have been renamed or removed
- Claude Code enforces this: "check the file exists before recommending it"

---

## Kuro's Memory Architecture (Current + Planned)

```
┌──────────────────────────────────────────────────┐
│                 CORE (Always Loaded)              │
├──────────────────────────────────────────────────┤
│ User Profile (markdown)                          │
│  - Background, preferences, knowledge gaps       │
│  - Agent-maintained, updated sparingly            │
│                                                   │
│ Top N Memories (by importance × recency)          │
│  - Preferences: response style, learning goals    │
│  - Instructions: standing orders                  │
│  - Context: recent important facts                │
├──────────────────────────────────────────────────┤
│               ARCHIVAL (On-Demand)                │
├──────────────────────────────────────────────────┤
│ All User Memories (via search_memories tool)      │
│  - Full history of saved memories                 │
│  - Searchable by query                            │
│                                                   │
│ Knowledge Base (via retrieval tools)              │
│  - Entities, facts, relations                     │
│  - Articles + semantic chunks                     │
│  - Hybrid search (FTS + vector)                   │
│                                                   │
│ Skill Data (via read_skill_data tool)             │
│  - Study sessions, research logs                  │
│  - Append-only JSONL on disk                      │
│  - Analyzed via helper tools                      │
└──────────────────────────────────────────────────┘
```

### Memory Flow

```
User says something
    │
    ├─→ Agent detects personal info → save_memory(importance=7, source="agent")
    ├─→ Agent detects preference    → save_memory(importance=8, source="agent", type="preference")
    ├─→ Agent detects instruction   → save_memory(importance=9, source="agent", type="instruction")
    │
    ├─→ Skill completes session     → append_skill_data() + save_memory(cross-reference summary)
    │
    ├─→ Significant new info        → update_profile (living markdown)
    │
    └─→ Notices related memories    → Consolidate (upsert with merged content)
```

### Memory Lifecycle

```
Created → Active → Accessed → Reinforced → Consolidated → Archived/Deleted
                                    │              │
                                    └─ importance ↑ │
                                                   └─ merged into summary
```

### Auto-Consolidation (Implemented)

Kuro uses embedding-based dedup at the storage layer, similar to Mem0. On every `save_memory` call:

1. **Embed** the new memory content (768-dim via gemini-embedding-2-preview)
2. **Search** existing memories using `match_memories` RPC (pgvector cosine similarity)
3. **Decide** based on similarity score:
   - **> 0.85 (merge)**: Memories are about the same thing → delete old, keep new with higher importance
   - **0.70-0.85 (conflict)**: Same topic, possibly contradicting → if same type, newer wins and old is deleted
   - **< 0.70 (unrelated)**: No action, save as new memory

```
save_memory("react_hooks_study", "Studying React hooks in depth")
  │
  ├── embed_text("Studying React hooks in depth") → [0.12, -0.34, ...]
  ├── match_memories(embedding, threshold=0.70)
  │     → Found: "react_learning" with similarity 0.91
  │
  ├── 0.91 > 0.85 → AUTO-MERGE
  │     → Delete "react_learning"
  │     → Keep higher importance
  │     → Save "react_hooks_study" with embedding
  │
  └── Return: {"status": "saved", "consolidated_from": [{"name": "react_learning", "action": "merged"}]}
```

This prevents memory bloat and resolves conflicts automatically. The agent doesn't need to manually check for duplicates — the store layer handles it transparently.

---

## Sources

- Claude Code docs: memory system, auto-memory, MEMORY.md
- Mem0: mem0.ai, research paper (arXiv:2504.19413)
- Letta/MemGPT: docs.letta.com, letta-ai/letta on GitHub
- IBM: "What Is AI Agent Memory?"
- Machine Learning Mastery: "3 Types of Long-term Memory AI Agents Need"
- Oracle: "Agent Memory: Why Your AI Has Amnesia and How to Fix It"
- MongoDB: "What Is Agent Memory? A Guide to Enhancing AI Learning and Recall"
- Leonie Monigatti: "Making Sense of Memory in AI Agents"
