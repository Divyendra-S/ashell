# Kuro Study Assistant — Feature Plan

> Extension of the Kuro Personal AI Assistant. This feature turns Kuro into a study companion that ingests what you learn, helps you revise, asks questions, connects topics, and plans your next study session.

---

## Overview

**Three surfaces, one brain:**
- **Chrome Extension** — scrape & save articles/blogs/docs you're studying
- **Mobile App (React Native)** — write notes, voice/text discussion, revision, daily planning
- **Python Backend** — all agentic code, APIs consumed by both app and extension

This plan covers the **Python backend** and **API design**. The React Native app and Chrome extension are separate — only their features and API contracts are mentioned here.

---

## User Flows

### Flow 1: "I'm studying this" (Chrome Extension)
```
User reads a blog/article → clicks extension → "Save this"
    → Extension scrapes page content (title, text, URL, date)
    → POST /api/content/ingest
    → Backend: Content Agent parses, chunks, extracts key concepts
    → Stores in: facts table + vector index + knowledge graph
    → Tags with topic (auto-detected or user-selected)
```

### Flow 2: "Here's what I did today" (Mobile App — Notes)
```
User writes: "Studied transformer attention mechanisms. Key insight:
Q/K/V matrices project into different subspaces for multi-head attention"
    → POST /api/notes
    → Backend: Ingest Agent extracts concepts, links to existing knowledge
    → Connects to previously saved articles on transformers
    → Adds to today's study session (episodic memory)
```

### Flow 3: "Let's discuss what I learned" (Mobile App — Voice/Text Chat)
```
User: "I studied attention mechanisms today, let's discuss"
    → POST /api/chat (or WebSocket for streaming)
    → Backend: Discussion Agent retrieves today's saved content + notes
    → Asks probing questions: "You saved an article about multi-head attention.
      Can you explain why we need multiple heads instead of one?"
    → User answers → Agent follows up, corrects, goes deeper
    → At session end: generates revision notes + saves key takeaways
```

### Flow 4: "What should I study tomorrow?" (Mobile App — Planning)
```
User: "Plan my study for tomorrow"
    → POST /api/study/plan
    → Backend: Planner Agent checks:
      - What topics are in progress but incomplete
      - What was studied today (don't repeat)
      - What's connected to recent topics (deepen understanding)
      - User's stated goals ("I want to learn system design by March")
      - Spaced repetition: what needs revision (studied 3 days ago)
    → Returns: prioritized study plan with suggested resources
```

### Flow 5: "Quiz me" (Mobile App — Revision)
```
User: "Quiz me on what I studied this week"
    → POST /api/study/quiz
    → Backend: Quiz Agent retrieves this week's facts + notes
    → Generates questions at varying difficulty
    → Tracks correct/incorrect → updates confidence scores on facts
    → Identifies weak areas → suggests focused revision
```

---

## Mobile App Features (React Native — build separately, integrate via APIs)

- **Home feed**: Today's study summary, pending revisions, suggested plan
- **Notes input**: Text field to write study notes (with voice-to-text option)
- **Chat/Discussion**: Voice or text conversation with the study agent
- **Content library**: All saved articles/notes organized by topic
- **Knowledge map**: Visual graph of connected topics and concepts
- **Quiz mode**: Interactive Q&A with scoring
- **Study planner**: Tomorrow's plan with time estimates
- **Topic management**: Create/organize study topics (AI, System Design, etc.)
- **Revision schedule**: Spaced repetition reminders

## Chrome Extension Features (build separately, integrate via APIs)

- **Save page**: One-click save of current article/blog
- **Highlight & save**: Select text → save specific passages
- **Auto-tag**: Suggests topic based on content
- **Quick note**: Add a note while reading without leaving the page
- **Study status**: "Mark as studied" / "Save for later" / "Need to revisit"

---

## Python Backend Architecture

### New Agents (under `kuro/agents/`)

```
agents/
├── study/
│   ├── __init__.py
│   ├── content.py          # Content Agent: scrapes, chunks, extracts concepts
│   ├── discussion.py       # Discussion Agent: Socratic dialogue on studied material
│   ├── quiz.py             # Quiz Agent: generates questions, tracks scores
│   ├── planner.py          # Planner Agent: creates daily study plans
│   └── revision.py         # Revision Agent: spaced repetition, revision notes
```

### New API Routes (under `kuro/web/`)

```python
# Content ingestion (Chrome Extension calls these)
POST /api/content/ingest     # Save article/blog content
POST /api/content/highlight  # Save highlighted passage
POST /api/content/status     # Mark as studied/revisit/later

# Notes (Mobile App calls these)
POST /api/notes              # Save study notes
GET  /api/notes?topic=X&date=Y  # Retrieve notes

# Chat/Discussion
POST /api/chat               # Single turn (or WebSocket for streaming)
WS   /api/chat/ws            # WebSocket for real-time discussion

# Study features
POST /api/study/plan         # Generate tomorrow's study plan
POST /api/study/quiz         # Start a quiz session
POST /api/study/quiz/answer  # Submit quiz answer, get feedback
GET  /api/study/progress     # Study stats, weak areas, streaks

# Knowledge
GET  /api/knowledge/graph    # Entity graph for visualization
GET  /api/knowledge/topics   # All topics with stats
GET  /api/knowledge/search?q=X  # Search across all stored knowledge
```

### Extended Memory Schema

```sql
-- Study content (articles, blogs, docs)
CREATE TABLE study_content (
    id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT NOT NULL,
    raw_text TEXT,                -- full scraped content
    summary TEXT,                 -- agent-generated summary
    topic_id TEXT REFERENCES topics(id),
    status TEXT DEFAULT 'saved',  -- saved | studying | studied | revisit
    studied_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Study topics (user-managed categories)
CREATE TABLE topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,           -- "Transformers", "System Design", "Go Lang"
    parent_id TEXT,               -- hierarchical: "AI" > "NLP" > "Transformers"
    description TEXT,
    goal TEXT,                    -- "Master by March 2026"
    created_at TIMESTAMP
);

-- Concepts (extracted from content + notes)
CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,           -- "Multi-Head Attention", "CAP Theorem"
    definition TEXT,              -- agent-extracted definition
    topic_id TEXT REFERENCES topics(id),
    confidence REAL DEFAULT 0.0,  -- 0-1, updated by quiz performance
    last_reviewed TIMESTAMP,
    next_review TIMESTAMP,        -- spaced repetition schedule
    created_at TIMESTAMP
);

-- Concept relationships (knowledge graph edges)
CREATE TABLE concept_relations (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES concepts(id),
    target_id TEXT REFERENCES concepts(id),
    relation TEXT NOT NULL,       -- "prerequisite_of", "related_to", "part_of", "contrasts_with"
    strength REAL DEFAULT 0.5,   -- how strong the connection is
    created_at TIMESTAMP
);

-- Study sessions (episodic memory for study)
CREATE TABLE study_sessions (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    topics_covered TEXT,          -- JSON array of topic IDs
    concepts_learned TEXT,        -- JSON array of concept IDs
    notes TEXT,                   -- session summary
    discussion_summary TEXT,      -- summary of agent discussion
    revision_notes TEXT,          -- generated revision notes for next day
    quiz_score REAL,              -- if quiz was taken
    duration_minutes INTEGER,
    created_at TIMESTAMP
);

-- Quiz attempts (for tracking progress)
CREATE TABLE quiz_attempts (
    id TEXT PRIMARY KEY,
    concept_id TEXT REFERENCES concepts(id),
    question TEXT NOT NULL,
    user_answer TEXT,
    correct BOOLEAN,
    feedback TEXT,                -- agent's explanation
    created_at TIMESTAMP
);

-- FTS5 for searching study content
CREATE VIRTUAL TABLE study_content_fts USING fts5(title, raw_text, summary);
CREATE VIRTUAL TABLE concepts_fts USING fts5(name, definition);
```

### How Retrieval Techniques Apply Here

This feature is where retrieval shines because there's genuinely lots of data:

| Strategy | Use Case in Study |
|----------|-------------------|
| **BM25 (FTS5)** | "Find my notes on attention mechanisms" — exact term matching across content + notes |
| **Semantic Search** | "What did I learn about how models handle long sequences?" — meaning-based, finds related content even with different wording |
| **Graph RAG** | "How does attention relate to what I studied about RNNs last week?" — traverses concept_relations to find connections across topics |
| **Web Search** | "Find me a good resource on flash attention" — when user needs new material beyond what's saved |

**The Query Agent picks strategy via PTC:**
```python
# User asks: "How does multi-head attention connect to what I learned about CNNs?"
# Agent writes:
concept = graph_query("multi-head attention", depth=2)
related = [r for r in concept.relations if "CNN" in r.target.topic.name]
if not related:
    # Try semantic similarity
    results = semantic_search("attention mechanisms CNN relationship", top_k=5)
print(format_connections(related or results))
```

### Agent Behavior Details

#### Content Agent (`agents/study/content.py`)
When a URL/text is ingested:
1. Chunks the content (by paragraph or ~500 token chunks)
2. Calls Gemini to extract: title, summary, key concepts, prerequisite concepts
3. For each concept: checks if it already exists → update or create
4. Creates concept_relations to existing concepts (Gemini identifies connections)
5. Embeds chunks for semantic search
6. Indexes in FTS5 for keyword search
7. Returns: summary + list of new/updated concepts

#### Discussion Agent (`agents/study/discussion.py`)
When user wants to discuss:
1. Retrieves today's study_content + notes via episodic memory
2. Retrieves relevant concepts and their confidence scores
3. Uses Socratic method: asks questions rather than lecturing
4. Focuses on low-confidence concepts first
5. If user can't answer → explains, then re-asks differently
6. At session end: updates concept confidence scores, generates revision notes
7. Saves discussion summary to study_sessions

#### Quiz Agent (`agents/study/quiz.py`)
1. Retrieves concepts due for review (spaced repetition: next_review <= now)
2. Generates questions at appropriate difficulty (based on confidence)
3. Question types: definition, comparison, application, relationship
4. After each answer: provides feedback, updates confidence
5. Adjusts next_review date based on performance (SM-2 algorithm or similar)

#### Planner Agent (`agents/study/planner.py`)
1. Checks: what's due for revision (spaced repetition schedule)
2. Checks: what topics are in-progress but incomplete
3. Checks: user's stated goals and deadlines
4. Checks: what was studied recently (avoid repetition unless revision)
5. Considers: concept prerequisites (don't suggest advanced topics before basics)
6. Outputs: prioritized list with estimated time, type (new material vs revision), and suggested resources from saved content

### Spaced Repetition Logic

```python
# Simplified SM-2 algorithm for concept review scheduling
def update_review_schedule(concept_id: str, correct: bool, ease_factor: float = 2.5):
    concept = get_concept(concept_id)

    if correct:
        concept.confidence = min(1.0, concept.confidence + 0.1)
        # Increase interval: 1 day → 3 days → 7 days → 14 days → 30 days
        intervals = [1, 3, 7, 14, 30, 60]
        current_interval_idx = get_current_interval_idx(concept)
        next_idx = min(current_interval_idx + 1, len(intervals) - 1)
        concept.next_review = now() + timedelta(days=intervals[next_idx])
    else:
        concept.confidence = max(0.0, concept.confidence - 0.2)
        # Reset to 1 day
        concept.next_review = now() + timedelta(days=1)

    save_concept(concept)
```

---

## Build Order (within Kuro phases)

This feature spans across multiple Kuro phases:

| Kuro Phase | Study Feature Work |
|------------|-------------------|
| Phase 2 (Memory) | Add study tables (study_content, topics, concepts, concept_relations) to `memory/store.py` |
| Phase 3 (Retrieval) | Content Agent ingestion + FTS5/semantic indexing of study content |
| Phase 4 (Orchestration) | Discussion Agent + routing "let's discuss" to study agents |
| Phase 5 (Compaction) | Study session summaries → episodic memory, revision note generation |
| Phase 6 (Research) | Planner Agent, Quiz Agent, web search for new resources |
| Phase 7 (Web Dashboard) | Study-specific API routes, knowledge graph visualization |

**After Phase 7:** Chrome extension and React Native app connect to the APIs.

---

## Technique Coverage

| Technique | How Study Feature Uses It |
|-----------|--------------------------|
| **PTC** | Query agent writes Python to search across notes + content + concepts. Quiz agent generates questions via code. |
| **Progressive Disclosure** | Study skills (quiz, plan, discuss) loaded on demand when user enters study mode |
| **Compaction** | Long discussion sessions compressed. Study session → episode summary. |
| **Three-Tier Memory** | Scratchpad: current discussion state. Episodes: daily study sessions. Facts: concepts + definitions that persist. |
| **Multi-Strategy Retrieval** | BM25 for exact terms, semantic for conceptual queries, graph for topic connections, web for new resources |
| **Graph RAG** | Concept → concept relations, topic hierarchy, prerequisite chains |
| **Multi-Agent** | Content Agent, Discussion Agent, Quiz Agent, Planner Agent — orchestrated by main orchestrator |
| **Code Sandbox** | Quiz generation, spaced repetition calculations, data analysis on study progress |

---

## Interview Demo Flow for Study Feature

1. Show saved articles in knowledge map (graph visualization)
2. "Quiz me on transformers" → agent asks 3 questions, gives feedback
3. "What connects attention to what I studied about RNNs?" → graph traversal answer
4. "Plan my study for tomorrow" → prioritized plan with revision + new material
5. Show confidence scores changing after quiz
6. Show spaced repetition schedule
