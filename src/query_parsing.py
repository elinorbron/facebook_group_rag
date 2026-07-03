from __future__ import annotations

import re
from datetime import datetime

from dateutil import parser as date_parser
from langchain_core.documents import Document

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def is_summary_query(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("summarize", "summary", "overview", "themes", "recap"))


def parse_month_year(question: str) -> tuple[str, str] | None:
    q = question.lower()
    year_match = re.search(r"(20\d{2})", q)
    year = year_match.group(1) if year_match else str(datetime.now().year)

    for name, month_num in MONTHS.items():
        if re.search(rf"\b{name}\b", q):
            start = f"{year}-{month_num:02d}-01"
            if month_num == 12:
                end = f"{int(year) + 1}-01-01"
            else:
                end = f"{year}-{month_num + 1:02d}-01"
            return start, end
    return None


def parse_single_date(question: str) -> str | None:
    patterns = [
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            try:
                return date_parser.parse(match.group(0), fuzzy=True).date().isoformat()
            except (ValueError, OverflowError):
                continue
    return None


def iso_to_int(iso_date: str) -> int:
    return int(iso_date.replace("-", ""))


def format_docs(docs: list[Document]) -> str:
    blocks = []
    for doc in docs:
        meta = doc.metadata
        blocks.append(
            f"[{meta.get('post_date', 'unknown date')} | {meta.get('group_name', '')} | {meta.get('post_type', '')}]\n"
            f"{doc.page_content}"
        )
    return "\n\n---\n\n".join(blocks)
