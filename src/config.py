from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
INDEX_DIR = Path(os.getenv("INDEX_DIR", PROJECT_ROOT / "index"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "facebook_group_posts")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Optional comma-separated substring filters, e.g. "group1,group2"
GROUP_FILTER = os.getenv("GROUP_FILTER", "")


def parse_group_filters(filter_str: str | None = None) -> list[str]:
    """Return non-empty filter substrings from a comma-separated env value."""
    raw = GROUP_FILTER if filter_str is None else filter_str
    if not raw or not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]

# Files to look for inside the Facebook export
GROUP_HTML_FILES = (
    "group_posts_and_comments.html",
    "your_comments_in_groups.html",
)
GROUP_JSON_FILES = (
    "group_posts_and_comments.json",
    "your_posts_in_groups.json",
    "your_comments_in_groups.json",
)
