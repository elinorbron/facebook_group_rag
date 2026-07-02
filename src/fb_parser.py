from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from src.config import (
    DATA_DIR,
    GROUP_FILTER,
    GROUP_HTML_FILES,
    GROUP_JSON_FILES,
    parse_group_filters,
)

POSTED_IN_RE = re.compile(r"posted in (.+?)\.\s*$", re.IGNORECASE)
GROUP_LABEL_RE = re.compile(r"^Group:\s*", re.IGNORECASE)


@dataclass
class GroupPost:
    post_id: str
    title: str
    group_name: str
    author: str
    post_date: str  # ISO date YYYY-MM-DD
    timestamp_raw: str
    body: str
    post_type: str  # celebration, revelation, comment, post, other
    source_file: str

    def to_document_text(self) -> str:
        return (
            f"Date: {self.post_date}\n"
            f"Group: {self.group_name}\n"
            f"Type: {self.post_type}\n"
            f"Title: {self.title}\n\n"
            f"{self.body}"
        )


def _classify_post(body: str, title: str) -> str:
    text = f"{title}\n{body}".lower()
    if "revelation" in text or "distinction" in text:
        return "revelation"
    if "celebrat" in text or "grateful" in text or "thankful" in text:
        return "celebration"
    if "comment" in title.lower() or "replied" in title.lower():
        return "comment"
    return "post"


def _parse_facebook_date(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    dt = date_parser.parse(raw)
    return dt.date().isoformat(), raw


def _extract_group_from_title(title: str) -> str:
    match = POSTED_IN_RE.search(title)
    if match:
        return match.group(1).strip()
    return ""


def _extract_author(title: str) -> str:
    if " posted " in title:
        return title.split(" posted ", 1)[0].strip()
    if " commented" in title:
        return title.split(" commented", 1)[0].strip()
    if " replied" in title:
        return title.split(" replied", 1)[0].strip()
    return ""


def _best_body_from_section(section) -> str:
    pins = section.find_all("div", class_="_2pin")
    candidates: list[str] = []
    for pin in pins:
        inner = pin.find("div", recursive=False)
        if not inner:
            continue
        text = inner.get_text("\n", strip=True)
        if not text:
            continue
        text = GROUP_LABEL_RE.sub("", text)
        if text not in candidates:
            candidates.append(text)
    if not candidates:
        return ""
    return max(candidates, key=len)


def _extract_group_from_body(body: str) -> str:
    for line in body.splitlines():
        if line.lower().startswith("group:"):
            return line.split(":", 1)[1].strip()
    return ""


def parse_html_file(path: Path) -> list[GroupPost]:
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    posts: list[GroupPost] = []

    for idx, section in enumerate(soup.find_all("section", class_="_a6-g")):
        h2 = section.find("h2")
        title = h2.get_text(" ", strip=True) if h2 else "Untitled"
        footer = section.find("footer")
        date_div = footer.find("div", class_="_a72d") if footer else None
        timestamp_raw = date_div.get_text(strip=True) if date_div else ""
        if not timestamp_raw:
            continue

        body = _best_body_from_section(section)
        if not body:
            continue

        group_name = _extract_group_from_title(title) or _extract_group_from_body(body)
        author = _extract_author(title)
        post_date, timestamp_raw = _parse_facebook_date(timestamp_raw)
        post_type = _classify_post(body, title)
        post_id = f"{path.stem}-{idx}-{post_date}"

        posts.append(
            GroupPost(
                post_id=post_id,
                title=title,
                group_name=group_name,
                author=author,
                post_date=post_date,
                timestamp_raw=timestamp_raw,
                body=body,
                post_type=post_type,
                source_file=path.name,
            )
        )

    return posts


def _walk_json_posts(node, source_file: str, posts: list[GroupPost], idx_start: int = 0) -> int:
  idx = idx_start
  if isinstance(node, dict):
    if "timestamp" in node and ("data" in node or "post" in node):
      timestamp = int(node["timestamp"])
      dt = datetime.utcfromtimestamp(timestamp)
      post_date = dt.date().isoformat()
      timestamp_raw = dt.isoformat()

      data = node.get("data", [])
      body_parts = []
      if isinstance(data, list):
        for item in data:
          if isinstance(item, dict):
            for val in item.values():
              if isinstance(val, str):
                body_parts.append(val)
          elif isinstance(item, str):
            body_parts.append(item)
      body = "\n".join(body_parts).strip()

      title = node.get("title", "")
      group_name = _extract_group_from_title(title) or node.get("group", "")
      author = _extract_author(title)

      if body or title:
        post_type = _classify_post(body, title)
        posts.append(
          GroupPost(
            post_id=f"{source_file}-{idx}-{post_date}",
            title=title or "Facebook group post",
            group_name=str(group_name),
            author=author,
            post_date=post_date,
            timestamp_raw=timestamp_raw,
            body=body or title,
            post_type=post_type,
            source_file=source_file,
          )
        )
        idx += 1

    for value in node.values():
      idx = _walk_json_posts(value, source_file, posts, idx)

  elif isinstance(node, list):
    for item in node:
      idx = _walk_json_posts(item, source_file, posts, idx)

  return idx


def parse_json_file(path: Path) -> list[GroupPost]:
    data = json.loads(path.read_text(encoding="utf-8"))
    posts: list[GroupPost] = []
    _walk_json_posts(data, path.name, posts)
    return posts


def find_export_files(data_dir: Path) -> tuple[list[Path], list[Path]]:
    html_files = sorted({p for name in GROUP_HTML_FILES for p in data_dir.rglob(name)})
    json_files = sorted({p for name in GROUP_JSON_FILES for p in data_dir.rglob(name)})
    return html_files, json_files


def _matches_group_filter(group_name: str, filters: list[str]) -> bool:
    if not filters:
        return True
    group_lower = group_name.lower()
    return any(f.lower() in group_lower for f in filters)


def load_posts(data_dir: Path | None = None, group_filter: str | None = None) -> list[GroupPost]:
    data_dir = data_dir or DATA_DIR
    filters = parse_group_filters(GROUP_FILTER if group_filter is None else group_filter)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    html_files, json_files = find_export_files(data_dir)
    if not html_files and not json_files:
        raise FileNotFoundError(
            f"No Facebook group export files found under {data_dir}. "
            "Expected group_posts_and_comments.html or .json"
        )

    posts: list[GroupPost] = []
    for path in html_files:
        posts.extend(parse_html_file(path))
    for path in json_files:
        posts.extend(parse_json_file(path))

    if filters:
        posts = [p for p in posts if _matches_group_filter(p.group_name, filters)]

    # Deduplicate by content + date
    seen: set[tuple[str, str, str]] = set()
    unique: list[GroupPost] = []
    for post in sorted(posts, key=lambda p: (p.post_date, p.post_id)):
        key = (post.post_date, post.group_name, post.body[:200])
        if key in seen:
            continue
        seen.add(key)
        unique.append(post)

    return unique


def posts_to_dicts(posts: Iterable[GroupPost]) -> list[dict]:
    return [asdict(p) for p in posts]
