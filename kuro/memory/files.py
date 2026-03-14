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


def chunk_text(text: str, max_words: int = 500) -> list[str]:
    """Split text into ~500-word chunks at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks, current, current_words = [], [], 0
    for para in paragraphs:
        words = len(para.split())
        if current_words + words > max_words and current:
            chunks.append("\n\n".join(current))
            current, current_words = [para], words
        else:
            current.append(para)
            current_words += words
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def grep_articles(pattern: str, max_results: int = 10) -> list[str]:
    """Grep across all saved article files for exact matches. Returns matching lines with context."""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "-i", "-n", "-C", "2", "--include=*.md", pattern, str(BASE_DIR)],
        capture_output=True, text=True, timeout=10
    )
    if not result.stdout:
        return []
    matches = []
    for block in result.stdout.strip().split("--"):
        lines = block.strip()
        if lines:
            matches.append(lines)
        if len(matches) >= max_results:
            break
    return matches
