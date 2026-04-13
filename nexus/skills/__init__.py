import json
import yaml
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent
_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "skill_data"
_cache: dict[str, dict] = {}


def _parse_skill_md(path: Path) -> dict:
    text = path.read_text()
    parts = text.split("---", 2)
    meta = yaml.safe_load(parts[1])
    body = parts[2].strip() if len(parts) > 2 else ""
    return {
        "name": meta["name"],
        "description": meta["description"],
        "triggers": meta.get("triggers", []),
        "mode": meta.get("mode", "query"),
        "guards": meta.get("guards", []),
        "body": body,
    }


def load_skills() -> dict[str, dict]:
    global _cache
    if _cache:
        return _cache
    for skill_dir in _SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill = _parse_skill_md(skill_dir / "SKILL.md")
            _cache[skill["name"]] = skill
    return _cache


def get_skill(name: str) -> dict | None:
    return load_skills().get(name)


def get_skill_data_dir(skill_name: str, user_id: str = "default") -> Path:
    d = _DATA_DIR / user_id / skill_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_skill_data(skill_name: str, filename: str, user_id: str = "default") -> list[dict]:
    path = get_skill_data_dir(skill_name, user_id) / filename
    if not path.exists():
        return []
    records = []
    for line in path.read_text().strip().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def append_skill_data(skill_name: str, filename: str, record: dict, user_id: str = "default") -> str:
    path = get_skill_data_dir(skill_name, user_id) / filename
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return f"Saved to {path}"


_WRITE_TOOLS = {"write_wiki_page", "update_memories", "update_wiki_index", "update_wiki_recent", "save_article", "append_skill_data", "update_profile"}


def _guard_no_store(name: str, args: dict) -> str | None:
    if name in _WRITE_TOOLS:
        return f"Tool '{name}' is blocked: this skill runs in read-only mode."
    return None


GUARD_REGISTRY: dict[str, callable] = {
    "read_only": _guard_no_store,
}


def get_skill_guards(skill_name: str) -> list[callable]:
    skill = get_skill(skill_name)
    if not skill:
        return []
    guards = []
    for guard_name in skill.get("guards", []):
        if guard_name in GUARD_REGISTRY:
            guards.append(GUARD_REGISTRY[guard_name])
    return guards


def get_skill_index() -> str:
    skills = load_skills()
    lines = ["## Available Skills"]
    for s in skills.values():
        triggers = ", ".join(s["triggers"]) if s["triggers"] else ""
        hint = f" (triggers: {triggers})" if triggers else ""
        lines.append(f"- **/{s['name']}**: {s['description']}{hint}")
    lines.append(
        "\nWhen the user's request matches a skill, announce which skill you're using "
        "and follow its workflow. The user can also invoke skills explicitly with /name."
    )
    return "\n".join(lines)
