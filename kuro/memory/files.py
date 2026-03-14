from pathlib import Path
import re

BASE_DIR = Path("data/articles")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-"))


def save_article(title: str, content: str, topic: str = "general") -> str:
    """Write markdown to data/articles/<topic>/<slug>.md. Returns relative path."""
    topic_dir = BASE_DIR / topic
    topic_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)
    path = topic_dir / f"{slug}.md"
    path.write_text(f"# {title}\n\n{content}")
    return str(path)


def get_article(file_path: str) -> str:
    return Path(file_path).read_text()


def list_topics() -> list[str]:
    if not BASE_DIR.exists():
        return []
    return [d.name for d in BASE_DIR.iterdir() if d.is_dir()]
