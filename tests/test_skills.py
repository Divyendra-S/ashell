"""
Test skill auto-detection, routing, data persistence, and (optionally) full Gemini flow.

Run: uv run python tests/test_skills.py
"""
import json
import sys
import time
import traceback

# ── Helpers ──────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0

def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} — {detail}")


# ── 1. Skill Loading ────────────────────────────────────────────────────────

print("\n═══ 1. SKILL LOADING ═══")
from kuro.skills import load_skills, get_skill, get_skill_index

skills = load_skills()
expected = {"study", "explain", "summarize", "compare", "deep-research", "ingest-url",
            "review", "daily-digest", "teach", "flashcard"}
check("All 10 skills loaded", set(skills.keys()) == expected,
      f"got {set(skills.keys())}")

for name in expected:
    s = get_skill(name)
    check(f"  get_skill('{name}') returns data", s is not None and "body" in s)

index = get_skill_index()
check("Skill index contains all skills", all(f"/{n}" in index for n in expected))


# ── 2. Auto-Detection via classify() ────────────────────────────────────────

print("\n═══ 2. AUTO-DETECTION (classify) ═══")
from kuro.cli import classify

test_cases = [
    # (input_text, expected_mode, expected_skill)
    ("quiz me on Python",                "query",  "study"),
    ("test me on databases",             "query",  "study"),
    ("practice React hooks",             "query",  "study"),
    ("explain how caching works",        "query",  "explain"),
    ("help me understand transformers",  "query",  "explain"),
    ("what is a knowledge graph",        "query",  "explain"),
    ("summarize the project",            "query",  "summarize"),
    ("give me an overview of AI",        "query",  "summarize"),
    ("compare React vs Vue",             "query",  "compare"),
    ("difference between SQL and NoSQL", "query",  "compare"),
    ("Tesla vs SpaceX",                  "query",  "compare"),
    ("research distributed systems",     "query",  "deep-research"),
    ("deep dive into Kubernetes",        "query",  "deep-research"),
    ("investigate memory leaks",         "query",  "deep-research"),
    ("review my KB",                     "query",  "review"),
    ("KB stats",                         "query",  "review"),
    ("knowledge health",                 "query",  "review"),
    ("daily digest",                     "query",  "daily-digest"),
    ("what's new",                       "query",  "daily-digest"),
    ("catch me up",                      "query",  "daily-digest"),
    ("let me teach you about React",     "ingest", "teach"),
    ("I want to tell you about my project", "ingest", "teach"),
    ("flashcard review please",            "query",  "flashcard"),
    ("what should I review",             "query",  "flashcard"),
    ("spaced repetition session",        "query",  "flashcard"),
    ("save this article http://x.com",   "ingest", "ingest-url"),
]

for text, exp_mode, exp_skill in test_cases:
    mode, skill = classify(text)
    ok = mode == exp_mode and skill == exp_skill
    check(f"'{text[:40]:40s}' → {exp_mode}/{exp_skill}",
          ok, f"got {mode}/{skill}")


# ── 3. Slash Command Routing ────────────────────────────────────────────────

print("\n═══ 3. SLASH COMMANDS ═══")
slash_cases = [
    ("/study Python",       "query",  "study"),
    ("/explain caching",    "query",  "explain"),
    ("/summarize AI",       "query",  "summarize"),
    ("/compare X vs Y",     "query",  "compare"),
    ("/deep-research K8s",  "query",  "deep-research"),
    ("/review",             "query",  "review"),
    ("/daily-digest",       "query",  "daily-digest"),
    ("/teach React",        "ingest", "teach"),
    ("/flashcard",          "query",  "flashcard"),
    ("/ingest-url http://", "ingest", "ingest-url"),
]

for text, exp_mode, exp_skill in slash_cases:
    mode, skill = classify(text)
    ok = mode == exp_mode and skill == exp_skill
    check(f"'{text:30s}' → {exp_mode}/{exp_skill}", ok, f"got {mode}/{skill}")


# ── 4. Skill Data Persistence ───────────────────────────────────────────────

print("\n═══ 4. SKILL DATA PERSISTENCE (per-user) ═══")
from kuro.skills import get_skill_data_dir, read_skill_data, append_skill_data
import os, shutil
from pathlib import Path

# Test directory creation with user_id
d_alice = get_skill_data_dir("_test_skill", user_id="alice")
d_bob = get_skill_data_dir("_test_skill", user_id="bob")
check("Alice data dir created", d_alice.exists() and d_alice.is_dir())
check("Bob data dir created", d_bob.exists() and d_bob.is_dir())
check("Dirs are different (per-user)", d_alice != d_bob)
check("Alice path contains user_id", "alice" in str(d_alice))
check("Bob path contains user_id", "bob" in str(d_bob))

# Test per-user write isolation
append_skill_data("_test_skill", "test.jsonl", {"score": 5, "topic": "math"}, user_id="alice")
append_skill_data("_test_skill", "test.jsonl", {"score": 3, "topic": "history"}, user_id="alice")
append_skill_data("_test_skill", "test.jsonl", {"score": 1, "topic": "science"}, user_id="bob")

# Test per-user read isolation
alice_records = read_skill_data("_test_skill", "test.jsonl", user_id="alice")
bob_records = read_skill_data("_test_skill", "test.jsonl", user_id="bob")
check("Alice has 2 records", len(alice_records) == 2, f"got {len(alice_records)}")
check("Bob has 1 record", len(bob_records) == 1, f"got {len(bob_records)}")
check("Alice first record correct", alice_records[0] == {"score": 5, "topic": "math"})
check("Bob record correct", bob_records[0] == {"score": 1, "topic": "science"})

# Users can't see each other's data
check("Alice can't see Bob's data", {"score": 1, "topic": "science"} not in alice_records)
check("Bob can't see Alice's data", {"score": 5, "topic": "math"} not in bob_records)

# Test reading non-existent file
empty = read_skill_data("_test_skill", "nonexistent.jsonl", user_id="alice")
check("Non-existent file returns []", empty == [])

# Cleanup
data_root = Path("/Users/divyendra/ashell/data/skill_data")
shutil.rmtree(data_root / "alice", ignore_errors=True)
shutil.rmtree(data_root / "bob", ignore_errors=True)
check("Cleanup succeeded", not d_alice.exists() and not d_bob.exists())


# ── 5. Gotchas Present in Skills ────────────────────────────────────────────

print("\n═══ 5. GOTCHAS IN SKILLS ═══")
for name in expected:
    s = get_skill(name)
    has_gotchas = "## Gotchas" in s["body"] or "## Gotcha" in s["body"]
    check(f"/{name} has Gotchas section", has_gotchas)


# ── 6. Progressive Disclosure Sub-Files ─────────────────────────────────────

print("\n═══ 6. PROGRESSIVE DISCLOSURE ═══")
from pathlib import Path

skills_dir = Path("/Users/divyendra/ashell/kuro/skills")
check("deep_research/report_template.md exists",
      (skills_dir / "deep_research" / "report_template.md").exists())
check("deep_research/examples/good_report.md exists",
      (skills_dir / "deep_research" / "examples" / "good_report.md").exists())
check("study/question_types.md exists",
      (skills_dir / "study" / "question_types.md").exists())

# Verify skills reference their sub-files
dr = get_skill("deep-research")
check("deep-research body references report_template.md",
      "report_template.md" in dr["body"])
study = get_skill("study")
check("study body references /explain for low scores",
      "/explain" in study["body"])


# ── 7. Tool Declarations ────────────────────────────────────────────────────

print("\n═══ 7. TOOL DECLARATIONS ═══")
from kuro.agents.query import TOOLS as Q_TOOLS, SKILL_DATA_TOOLS as Q_SD_TOOLS, SKILL_HELPER_TOOLS
from kuro.agents.ingest import TOOLS as I_TOOLS, SKILL_DATA_TOOLS as I_SD_TOOLS

q_tool_names = [t["name"] for t in Q_TOOLS[0]["functionDeclarations"]]
check("Query agent has 11 base tools", len(q_tool_names) == 11, f"got {len(q_tool_names)}")

q_sd_names = [t["name"] for t in Q_SD_TOOLS[0]["functionDeclarations"]]
check("Query skill data tools: read + append",
      set(q_sd_names) == {"read_skill_data", "append_skill_data"})

i_tool_names = [t["name"] for t in I_TOOLS[0]["functionDeclarations"]]
check("Ingest agent has lookup_entity tool", "lookup_entity" in i_tool_names)
check("Ingest agent has 6 tools total", len(i_tool_names) == 6, f"got {len(i_tool_names)}: {i_tool_names}")

i_sd_names = [t["name"] for t in I_SD_TOOLS[0]["functionDeclarations"]]
check("Ingest skill data tools: read + append",
      set(i_sd_names) == {"read_skill_data", "append_skill_data"})


# ── 7b. Helper Tool Declarations ──────────────────────────────────────────

print("\n═══ 7b. HELPER TOOL DECLARATIONS ═══")
check("study has helper tools", "study" in SKILL_HELPER_TOOLS)
check("review has helper tools", "review" in SKILL_HELPER_TOOLS)
study_helper_names = [t["name"] for t in SKILL_HELPER_TOOLS["study"][0]["functionDeclarations"]]
check("study helper: analyze_study_progress", "analyze_study_progress" in study_helper_names)
review_helper_names = [t["name"] for t in SKILL_HELPER_TOOLS["review"][0]["functionDeclarations"]]
check("review helper: kb_health_report", "kb_health_report" in review_helper_names)

# ── 7c. update_profile in base tools ─────────────────────────────────────

print("\n═══ 7c. UPDATE_PROFILE TOOL ═══")
check("update_profile in query base tools", "update_profile" in q_tool_names)


# ── 8. Skill Composition ────────────────────────────────────────────────────

print("\n═══ 8. SKILL COMPOSITION ═══")
study_body = get_skill("study")["body"]
check("study references /explain", "/explain" in study_body)

flashcard_body = get_skill("flashcard")["body"]
check("flashcard references /explain", "/explain" in flashcard_body)

teach_body = get_skill("teach")["body"]
check("teach references /study", "/study" in teach_body)


# ── 8b. User Profile System ────────────────────────────────────────────────

print("\n═══ 8b. USER PROFILE SYSTEM ═══")
from kuro.memory.store import read_user_profile, update_user_profile

# Test write and read
test_profile = "# User Profile: _test_user\n\n## Background\n- Test user for automated tests"
update_user_profile("_test_profile_user", test_profile)
read_back = read_user_profile("_test_profile_user")
check("Profile write+read roundtrip", read_back == test_profile)

# Test empty profile
empty = read_user_profile("_nonexistent_user_xyz")
check("Non-existent profile returns empty string", empty == "")

# Cleanup
shutil.rmtree(Path("/Users/divyendra/ashell/data/user_profiles/_test_profile_user"), ignore_errors=True)
check("Profile cleanup succeeded",
      not Path("/Users/divyendra/ashell/data/user_profiles/_test_profile_user").exists())


# ── 8c. Guard System ──────────────────────────────────────────────────────

print("\n═══ 8c. GUARD SYSTEM ═══")
from kuro.skills import get_skill_guards, GUARD_REGISTRY

# Test guard registry
check("read_only guard registered", "read_only" in GUARD_REGISTRY)

# Test review skill has guards
review_skill = get_skill("review")
check("review skill has guards in frontmatter", len(review_skill.get("guards", [])) > 0)
check("review skill guard is read_only", "read_only" in review_skill.get("guards", []))

# Test guard function
review_guards = get_skill_guards("review")
check("get_skill_guards returns guards for review", len(review_guards) > 0)

# Test guard blocks write tools
guard_fn = review_guards[0]
check("Guard blocks store_entity", guard_fn("store_entity", {}) is not None)
check("Guard blocks store_fact", guard_fn("store_fact", {}) is not None)
check("Guard blocks save_memory", guard_fn("save_memory", {}) is not None)
check("Guard allows get_facts_for_entity", guard_fn("get_facts_for_entity", {}) is None)
check("Guard allows list_articles", guard_fn("list_articles", {}) is None)
check("Guard allows kb_health_report", guard_fn("kb_health_report", {}) is None)

# Test non-guarded skill
study_guards = get_skill_guards("study")
check("study skill has no guards", len(study_guards) == 0)


# ── 8d. Cross-Reference Instructions ──────────────────────────────────────

print("\n═══ 8d. CROSS-REFERENCE INSTRUCTIONS ═══")
study_body = get_skill("study")["body"]
check("study mentions append_skill_data", "append_skill_data" in study_body)
check("study mentions save_memory for cross-ref", "save_memory" in study_body)
check("study mentions sessions.jsonl", "sessions.jsonl" in study_body)

flashcard_body = get_skill("flashcard")["body"]
check("flashcard mentions append_skill_data", "append_skill_data" in flashcard_body)
check("flashcard mentions save_memory for cross-ref", "save_memory" in flashcard_body)

dr_body = get_skill("deep-research")["body"]
check("deep-research mentions append_skill_data", "append_skill_data" in dr_body)
check("deep-research mentions save_memory for cross-ref", "save_memory" in dr_body)
check("deep-research mentions research_log.jsonl", "research_log.jsonl" in dr_body)


# ── 8e. Helper Scripts Exist ──────────────────────────────────────────────

print("\n═══ 8e. HELPER SCRIPTS ═══")
check("study/scripts/analyze_progress.py exists",
      (skills_dir / "study" / "scripts" / "analyze_progress.py").exists())
check("review/scripts/kb_health.py exists",
      (skills_dir / "review" / "scripts" / "kb_health.py").exists())

# Test analyze_progress with no data (should return empty)
from kuro.skills.study.scripts.analyze_progress import analyze_progress
result = analyze_progress("_nonexistent_test_user")
check("analyze_progress with no data returns 0 sessions", result["total_sessions"] == 0)
check("analyze_progress returns empty topics", result["topics"] == {})


# ── 9. API Endpoint (skills list) ───────────────────────────────────────────

print("\n═══ 9. API SKILLS ENDPOINT ═══")
try:
    import requests
    resp = requests.get("http://localhost:8000/api/skills", timeout=5)
    if resp.status_code == 200:
        api_skills = resp.json()["skills"]
        api_names = {s["name"] for s in api_skills}
        check("API returns all 10 skills", api_names == expected,
              f"got {api_names}")
    else:
        check("API /api/skills responds 200", False, f"status {resp.status_code}")
except Exception as e:
    check("API /api/skills reachable", False, str(e))


# ── 10. Full Gemini Flow (if quota available) ───────────────────────────────

print("\n═══ 10. FULL GEMINI FLOW ═══")

def test_gemini_flow(label, message, user_id, expected_skill, expected_mode):
    """Test a full chat round-trip through the API."""
    try:
        import requests
        resp = requests.post(
            "http://localhost:8000/api/chat",
            json={"message": message, "user_id": user_id},
            timeout=120,
        )
        if resp.status_code == 429 or (resp.status_code == 500):
            # Could be Gemini quota — check
            check(f"{label}: API call", False, f"status {resp.status_code} (likely Gemini quota)")
            return False
        data = resp.json()
        skill_ok = data.get("skill") == expected_skill
        mode_ok = data.get("mode") == expected_mode
        has_response = bool(data.get("response", "").strip())
        check(f"{label}: skill={expected_skill}", skill_ok, f"got skill={data.get('skill')}")
        check(f"{label}: mode={expected_mode}", mode_ok, f"got mode={data.get('mode')}")
        check(f"{label}: non-empty response", has_response,
              f"response length: {len(data.get('response', ''))}")
        if has_response:
            print(f"    📝 Response preview: {data['response'][:150]}...")
        return True
    except Exception as e:
        check(f"{label}: request succeeded", False, str(e))
        return False

# Quick quota check first
try:
    import requests as _r
    from kuro.config import GEMINI_API_KEY, GEMINI_API_URL
    _resp = _r.post(
        GEMINI_API_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": "hi"}]}]},
    )
    if _resp.status_code == 429:
        print("  ⚠️  Gemini API quota exceeded — skipping full flow tests")
        print("     Run again when quota resets to test end-to-end")
    else:
        print("  ✅ Gemini API available — running full flow tests")
        # Test each skill with natural language (no slash commands)
        skills_to_test = [
            ("study",        "quiz me on Compound Engineering",              "div",       "study",        "query"),
            ("explain",      "help me understand what FeatureBase does",     "div",       "explain",      "query"),
            ("summarize",    "summarize Dan Shipper",                        "div",       "summarize",    "query"),
            ("compare",      "Tesla vs SpaceX",                             "test_user", "compare",      "query"),
            ("deep-research","investigate Compound Engineering approach",    "div",       "deep-research","query"),
            ("review",       "review my KB",                                "div",       "review",       "query"),
            ("daily-digest", "daily digest",                                "div",       "daily-digest", "query"),
            ("teach",        "let me teach you about my new project Kuro",  "div",       "teach",        "ingest"),
            ("flashcard",    "what should I review",                        "div",       "flashcard",    "query"),
            ("ingest-url",   "save this article https://example.com",       "div",       "ingest-url",   "ingest"),
        ]
        for label, msg, uid, exp_skill, exp_mode in skills_to_test:
            print(f"\n  --- Testing /{label} ---")
            ok = test_gemini_flow(label, msg, uid, exp_skill, exp_mode)
            if not ok:
                print(f"    ⚠️  Stopping full flow tests (quota likely hit)")
                break
            time.sleep(2)  # gentle delay between calls
except Exception as e:
    print(f"  ⚠️  Could not check Gemini quota: {e}")


# ── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'═' * 50}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'═' * 50}")
sys.exit(1 if FAIL > 0 else 0)
