import yaml
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent
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
