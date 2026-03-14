# Agentic Python: Techniques Reference & Project Blueprint

> Every technique exercised in a single interview-worthy project.

---

## The Project: **AgentForge** — A Multi-Agent Task Automation Platform

A web app where users describe a complex task in natural language, and a system of specialized agents collaborates to complete it — researching, writing code, generating files, querying data, and producing deliverables. Think of it as "your own mini Codex/Claude Code, but for general tasks, accessible via browser."

### Why Not Just a Retrieval App?

Retrieval-only projects exercise one pattern. AgentForge touches everything:

| Technique | How It's Used |
|-----------|--------------|
| PTC (Programmatic Tool Calling) | Agents write Python to orchestrate tools — not JSON tool calls |
| Progressive Disclosure | Agents discover skills/tools on demand from a skill registry |
| Compaction | Long multi-agent conversations get compressed to stay in-budget |
| Three-Tier Memory | Scratchpad per task, episodes per session, facts persist forever |
| Retrieval (RAG + Graph + Filesystem) | Research agent uses hybrid retrieval over uploaded docs AND web |
| Code Execution Sandbox | Code agent writes and runs Python/shell in isolated sandbox |
| Multi-Agent Orchestration | Orchestrator delegates to specialist agents (research, code, write, data) |
| Provider-Agnostic | Swap models per agent — cheap model for planning, strong for coding |
| Tool Design (Claude Code lessons) | Skills system, elicitation patterns, revisiting tools as models improve |

### What It Actually Does (Demo Scenarios)

**Scenario 1: "Analyze this CSV and make a report"**
- Orchestrator plans: need data agent + code agent + writer agent
- Data agent inspects CSV schema, generates summary stats (PTC → pandas code executed in sandbox)
- Code agent creates visualizations (matplotlib charts saved to filesystem)
- Writer agent composes a markdown report with charts embedded
- Output: downloadable PDF/HTML report

**Scenario 2: "Research competitor X and draft a comparison doc"**
- Orchestrator plans: need research agent + writer agent
- Research agent uses web search + retrieval from uploaded company docs
- Writer agent drafts comparison document
- Memory: facts about your company persist across sessions

**Scenario 3: "Set up a FastAPI endpoint that does Y"**
- Orchestrator routes to code agent
- Code agent writes code via PTC, executes tests in sandbox
- Iterates on failures (agentic loop — plan → code → test → fix)
- Output: working code files

**Scenario 4: "What did we decide about the database schema last week?"**
- Hits episodic memory → retrieves past session summary
- No agent loop needed, direct memory lookup

### Why This Wins in Interviews

- **Shows system design thinking** — orchestration patterns, agent communication, state management
- **Has a web UI** — interviewer opens it, types a task, watches agents work with live status
- **Produces real output** — files, reports, code, not just chat answers
- **Multi-agent is the 2025 differentiator** — 72% of enterprise AI projects now involve multi-agent architectures
- **You use it daily** — for your own research, code gen, report writing
- **Connects to your domain** — point it at SAS Migration docs, Swipiring codebase, learning notes

---

## Technique Reference (Concise)

### 1. Programmatic Tool Calling (PTC)

Instead of JSON tool-call schemas, the model writes Python code. You execute it with real functions injected.

```
System prompt: "You have these functions available. Write Python code.
Only print() output will be returned to you."

Executor:
  namespace = {"search": real_fn, "read_file": real_fn, ...}
  exec(model_code, namespace)
  return captured_stdout

Flow: prompt → model writes code → you exec → capture print() → feed back
```

**Why it matters:** Two model calls total vs N back-and-forth tool calls. The model orchestrates multiple tools in one code block. This is what the Claude Code blog means by "give it tools shaped to its own abilities" — models are good at writing code.

**Design lesson:** Claude Code's AskUserQuestion tool went through 3 iterations (bolted onto ExitPlanTool → custom markdown format → dedicated tool). The model has to "like" calling it. With PTC, you're leveraging the model's strongest ability.

---

### 2. Progressive Disclosure

Don't dump everything into context. Let agents discover what they need.

```
Tier 1: Skill index (~50-100 tokens each) — agent sees names + descriptions
Tier 2: Skill detail — loaded when agent selects one
Tier 3: Referenced files — skills reference deeper docs recursively
```

**In AgentForge:** The orchestrator sees a registry of available agents and tools. It loads specific agent instructions only when delegating to that agent. Each agent loads its own tool docs on demand.

**Source:** Claude Code uses ~20 tools and treats adding new ones as a high bar. Microsoft's Agent Skills framework uses this exact 3-tier pattern for 132+ skills. Claude Code added a Guide subagent for documentation search instead of a new tool — "add capabilities without adding tools."

---

### 3. Compaction

When context gets long, compress older content while preserving key information.

```
Lightest touch first: Tool result clearing — replace consumed tool outputs with brief summaries
Full compaction: Summarize older exchanges, keep recent 5 turns verbatim
Preserve: decisions, key findings, current plan, unresolved questions
Discard: raw tool outputs, redundant back-and-forth
```

**In AgentForge:** Multi-agent conversations get long fast. Each agent-to-agent exchange is a potential compaction point. The orchestrator maintains a running summary of what each agent has done.

**Source:** Anthropic describes this as finding "the smallest set of high-signal tokens that maximize the likelihood of your desired outcome." Claude Code preserves architectural decisions while discarding redundant outputs. Start by maximizing recall, then iterate to improve precision.

---

### 4. Three-Tier Memory

```
Scratchpad    — per-task, wiped on completion
  → Current plan, intermediate results, open questions
  → Each agent can read/write its own scratchpad

Episodic      — per-session summaries
  → "User analyzed competitor data, found pricing gap, created report"
  → Auto-generated at task completion

Fact memory   — durable knowledge, persists across sessions
  → "User's company uses FastAPI" / "User prefers concise outputs"
  → Extracted from episodes
```

**Storage:** Start with SQLite + markdown. Letta's benchmarks show plain filesystem beats specialized vector stores for most memory tasks (74% score). Add embeddings only when corpus grows.

---

### 5. Multi-Strategy Retrieval

Four layers, agent picks which to use via PTC:

```
BM25 keyword search   → exact terms, known entities (whoosh/tantivy)
Semantic vector search → meaning-based, paraphrased queries (chromadb + sentence-transformers)
Graph RAG              → cross-document reasoning, entity relationships (networkx or neo4j)
Web search             → current information, external research (API call)
```

The agent decides strategy in code:

```python
results = semantic_search(query, top_k=5)
if max(r.score for r in results) < 0.7:
    results = keyword_search(query)
if not results:
    results = web_search(query)
print(format_results(results))
```

---

### 6. Multi-Agent Orchestration

The core architectural pattern. Four approaches from industry:

```
Orchestrator pattern  → One coordinator routes tasks to specialist agents
                        (AgentForge uses this — closest to how Claude Code works)

Fan-out/fan-in        → Parallel sub-tasks, results merged
                        (Used for: research multiple topics simultaneously)

Pipeline/sequential   → Agent A output feeds Agent B input
                        (Used for: data → analysis → report)

Group chat            → Agents discuss in shared thread
                        (Used for: review/critique workflows)
```

**In AgentForge:**

```python
class Orchestrator:
    agents = {
        "research": ResearchAgent,   # web search + doc retrieval
        "code":     CodeAgent,       # writes + executes Python
        "writer":   WriterAgent,     # drafts documents
        "data":     DataAgent,       # analyzes CSVs, databases
    }
    
    def plan(self, task: str) -> list[Step]:
        """Model writes a plan selecting which agents to use."""
        # PTC: model returns code that builds a plan
        ...
    
    def execute(self, plan: list[Step]) -> str:
        """Execute steps, passing results between agents."""
        for step in plan:
            agent = self.agents[step.agent]
            result = agent.run(step.instruction, context=step.dependencies)
            self.memory.update_scratchpad(step, result)
        ...
```

**Agent communication:** Agents share context through the orchestrator's scratchpad, not by talking to each other directly. This is simpler and more debuggable than group chat for most tasks.

---

### 7. Code Execution Sandbox

```python
import subprocess, io

def exec_python(code: str, tools: dict, timeout: int = 30) -> str:
    output = io.StringIO()
    namespace = {
        **tools,
        "print": lambda *args, **kw: print(*args, file=output, **kw),
        "__builtins__": {  # restricted
            "len": len, "range": range, "enumerate": enumerate,
            "str": str, "int": int, "float": float, "list": list,
            "dict": dict, "max": max, "min": min, "sorted": sorted,
            "True": True, "False": False, "None": None,
        },
    }
    try:
        exec(code, namespace)
    except Exception as e:
        output.write(f"ERROR: {type(e).__name__}: {e}")
    return output.getvalue()

def exec_shell(cmd: str, timeout: int = 30) -> str:
    blocked = ["rm -rf", "sudo", "chmod 777"]
    if any(b in cmd for b in blocked):
        return "ERROR: blocked"
    result = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
    return f"{result.stdout}\n{result.stderr}".strip()
```

---

### 8. Provider-Agnostic Design

```python
class LLMClient:
    PROVIDERS = {
        "openai":    ("https://api.openai.com/v1", "gpt-4o"),
        "anthropic": ("https://api.anthropic.com/v1", "claude-sonnet-4-20250514"),
        "groq":      ("https://api.groq.com/openai/v1", "llama-3.3-70b"),
        "ollama":    ("http://localhost:11434/v1", "qwen2.5-coder"),
        "gemini":    ("https://generativelanguage.googleapis.com/v1beta/openai",
                      "gemini-2.0-flash"),
    }
```

**Key insight for AgentForge:** Assign different providers per agent role. Cheap/fast model (Groq/Ollama) for the orchestrator's planning step. Strong model (Claude/GPT-4o) for the code agent. This saves cost and shows you understand the tradeoff.

---

### 9. Tool Design Principles (from Claude Code Blog)

1. **Shape tools to the model's abilities** — PTC works because models write good Python
2. **Model must "like" calling the tool** — best-designed tool fails if model doesn't grok the interface
3. **Revisit tools as models improve** — TodoWrite → Tasks when models got better at subagent coordination
4. **Add capabilities without adding tools** — progressive disclosure via files/skills, not new tool schemas
5. **Read outputs, experiment, see like an agent** — it's an art, not a science

---

## Project Structure

```
agentforge/
├── app.py                      # FastAPI server + WebSocket for live updates
├── frontend/
│   └── index.html              # React/HTML UI with task input + agent status panel
├── orchestrator/
│   ├── planner.py              # Task decomposition via PTC
│   ├── router.py               # Routes steps to specialist agents
│   └── state.py                # Shared execution state
├── agents/
│   ├── base.py                 # BaseAgent class (loop, PTC, scratchpad)
│   ├── research.py             # Web search + doc retrieval agent
│   ├── code.py                 # Code writing + execution agent
│   ├── writer.py               # Document generation agent
│   └── data.py                 # Data analysis agent (CSV, SQL)
├── execution/
│   ├── sandbox.py              # Python exec + shell execution (technique 7)
│   └── safety.py               # Blocked commands, timeouts, output limits
├── retrieval/
│   ├── keyword.py              # BM25
│   ├── semantic.py             # Vector search
│   ├── graph.py                # GraphRAG
│   ├── web.py                  # Web search wrapper
│   └── ingest.py               # Document chunking pipeline
├── memory/
│   ├── scratchpad.py           # Per-task working memory
│   ├── episodic.py             # Session summaries
│   ├── facts.py                # Durable knowledge
│   └── store.py                # SQLite backend
├── context/
│   ├── builder.py              # Progressive disclosure + context assembly
│   └── compaction.py           # Summarization + token management
├── llm/
│   ├── client.py               # Provider-agnostic LLM client
│   └── config.py               # Per-agent model assignments
└── skills/
    ├── registry.py             # Skill index (tier 1 progressive disclosure)
    └── definitions/            # Skill files agents can load on demand
        ├── web_research.md
        ├── data_analysis.md
        └── code_generation.md
```

---

## Build Order

| Phase | What You Build | Techniques Exercised | Demo-able? |
|-------|---------------|---------------------|------------|
| 1 | `llm/client.py` — provider client + model switching | Provider-agnostic | No (infra) |
| 2 | `execution/sandbox.py` — PTC executor | PTC, code execution | Yes — "run any Python" |
| 3 | `agents/base.py` + `agents/code.py` — single agent loop | Agent loop, PTC | Yes — "give it a coding task" |
| 4 | `orchestrator/` — multi-agent planner + router | Multi-agent orchestration | Yes — "describe a complex task" |
| 5 | `agents/research.py` + `retrieval/` — hybrid retrieval | RAG, keyword, web search | Yes — "research a topic" |
| 6 | `agents/writer.py` + `agents/data.py` | Specialist agents, file output | Yes — "analyze CSV + write report" |
| 7 | `memory/` — three-tier memory | Scratchpad, episodic, facts | Yes — "remember across sessions" |
| 8 | `context/` — progressive disclosure + compaction | Context engineering | Yes — "long tasks stay coherent" |
| 9 | `app.py` + `frontend/` — web UI with live agent status | Full product | Yes — **the interview demo** |
| 10 | `retrieval/graph.py` — GraphRAG layer | Knowledge graphs | Yes — "cross-document reasoning" |

**By phase 4** you have a working multi-agent system.
**By phase 6** it produces real deliverables.
**By phase 9** it's a polished web app you can demo.

---

## Interview Talking Points per Technique

| Technique | What You Say |
|-----------|-------------|
| PTC | "Instead of JSON tool calls, the model writes Python that orchestrates multiple tools in one execution — 2 model calls instead of N round trips" |
| Progressive Disclosure | "Agents don't see all tools at once. They discover capabilities from a skill registry on demand — same pattern Claude Code uses for its 20+ tools" |
| Compaction | "When multi-agent conversations exceed the token budget, I compress older context while preserving decisions and key findings" |
| Memory | "Three tiers — scratchpad per task, episode summaries per session, extracted facts that persist forever. Started with SQLite because Letta showed plain filesystem beats vector stores at 74%" |
| Retrieval | "Four layers — BM25 for exact match, vector for semantic, graph for entity relationships, web for current info. The agent decides which to use in code" |
| Multi-Agent | "Orchestrator pattern — one coordinator plans and routes to specialist agents. Each agent has its own context, scratchpad, and model assignment" |
| Code Execution | "Model-generated code runs in a restricted exec() with injected tool functions. Shell commands have a blocklist and timeout" |
| Provider-Agnostic | "Different models per agent role — cheap model for planning, strong model for coding. Swap providers with one config change" |
| Tool Design | "I learned from how Claude Code evolved — they replaced TodoWrite with Tasks when models improved. I revisit my tool designs with each model upgrade" |

---

## Key Sources

- Anthropic: "Effective Context Engineering for AI Agents" — compaction, note-taking, multi-agent
- Anthropic: Claude Code blog — tool design, progressive disclosure, elicitation, TodoWrite → Tasks
- OpenAI: "Harness Engineering" — repo-as-context, invariant enforcement, agent-generated codebase
- OpenAI: Codex agent loop — durable project memory, plan→implement→validate→repair
- Microsoft: Agent Skills progressive disclosure — 3-tier loading for 132+ skills
- Microsoft: Azure AI agent orchestration patterns — orchestrator, fan-out, pipeline, group chat
- Survey: "Memory in the Age of AI Agents" (Dec 2025) — taxonomy of forms/functions/dynamics
- Mem0 paper — memory extraction and retrieval benchmarks
- LangChain: Ralph Loop pattern — harness-level hooks for multi-context-window coherence