# Kuro

A personal agent that keeps what you learn. You save articles and notes, it files them into a
wiki it writes itself, and you can ask it anything later, by text or by voice.

The repository is named `ashell`; the agent is called Kuro.

## What it does

- **Chat with your own knowledge.** One agent with 18 tools reads and writes the wiki, scrapes
  and saves articles, and updates what it remembers about you. The model decides whether a
  message is a question, something to save, or both, so there is no separate router.
- **Voice check-ins.** A real-time voice agent (speech to text, model, text to speech over
  WebRTC) runs a short daily conversation: what you learned, what you read, what you plan next.
  While you talk it calls tools to save each learning and goal separately.
- **Memory it maintains itself.** A profile and a memory file about you go into every prompt, and
  the agent rewrites them when it learns something lasting.
- **A wiki, not a pile of chunks.** Knowledge lives as markdown concept pages with
  `[[backlinks]]`, an index and a recent-changes page, all kept up to date by the agent.
- **Skills.** Ten workflows written as `SKILL.md` files (deep research, teach, flashcards,
  compare, daily digest and others), started with a slash command or a trigger phrase.
- **Browser clipper.** A Chrome extension saves the page you are reading into the wiki.
- **Progress.** Goals, streaks, an activity heatmap and a graph view of how concepts link.

## How it is built

```
Chrome clipper ──┐
Next.js app ─────┼──► FastAPI ──► agent loop (Gemini, tool calls) ──► wiki, articles,
Voice (WebRTC) ──┘        │                                           memories, goals
                          └──► Pipecat pipeline: Groq Whisper ► Gemini ► Groq TTS
```

- **The agent loop is written by hand** (`kuro/core/llm.py`): plain HTTP calls to the Gemini
  API, tool calls executed in a loop, with a streaming version that sends each tool step to the
  UI. No agent framework.
- **Voice** (`kuro/agents/voice.py`) is a [Pipecat](https://github.com/pipecat-ai/pipecat)
  pipeline: Groq `whisper-large-v3-turbo` for speech to text, `gemini-2.5-flash` for the
  conversation, Groq for speech. It shares the same memory and goals as the text agent.
- **Two storage backends behind one API.** The frontend can switch between them:
  - `kuro/` stores the wiki in Supabase (Postgres full-text search), on port 8000.
  - `nexus/` stores it as a graph in Neo4j: concepts, articles, memories and entities as nodes,
    backlinks as `LINKS_TO` edges, with full-text indexes. It runs on port 8001.
- **Skills are data.** Each skill is a folder with a `SKILL.md` (name, triggers, guards and the
  workflow as text). Adding one needs no code change.

| Part          | Technology                                                |
| ------------- | --------------------------------------------------------- |
| Agent and API | Python 3.13, FastAPI, Gemini API                          |
| Voice         | Pipecat, WebRTC, Groq (speech to text and text to speech) |
| Storage       | Supabase (Postgres) or Neo4j                              |
| Frontend      | Next.js 16, React 19, Tailwind CSS 4                      |
| Clipper       | Chrome extension (Manifest V3), Readability, Turndown     |

## Run it

Needs Python 3.13, [uv](https://docs.astral.sh/uv/) and Node.

```bash
cp .env.example .env        # add your keys
uv sync

uv run uvicorn kuro.api:app --port 8000 --reload   # Supabase backend, with voice
uv run python -m nexus.main                        # or the Neo4j backend, port 8001

cd frontend && npm install && npm run dev          # http://localhost:3000
```

- The Supabase backend expects the tables `wiki_pages`, `articles`, `checkin_sessions` and
  `checkin_entries`. The frontend and the clipper read the Supabase URL and public key from
  `frontend/lib/supabase.ts` and `kuro-clipper/config.js`; point them at your own project.
- The Neo4j backend creates its own constraints and indexes on start.
- To use the clipper, open `chrome://extensions`, turn on developer mode and load the
  `kuro-clipper` folder (`nexus-clipper` for the Neo4j backend).
- `uv run python -m kuro.cli` gives the same agent in a terminal.

## Layout

| Path                              | What is in it                                       |
| --------------------------------- | --------------------------------------------------- |
| `kuro/agents/unified.py`          | The text agent: system prompt, tools, tool executor |
| `kuro/agents/voice.py`            | The voice agent and its tools                       |
| `kuro/core/llm.py`                | The agent loop, streaming and embeddings            |
| `kuro/memory/`                    | Wiki, articles, check-ins and goals on Supabase     |
| `kuro/skills/`                    | The ten skills                                      |
| `nexus/`                          | The same agent on a Neo4j graph                     |
| `frontend/`                       | Chat, voice, dashboard, progress and graph pages    |
| `kuro-clipper/`, `nexus-clipper/` | The Chrome extensions                               |
| `learning/`, root `.md` files     | Notes and plans written while building this         |
