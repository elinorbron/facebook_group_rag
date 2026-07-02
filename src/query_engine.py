from __future__ import annotations

import re
from datetime import datetime

from dateutil import parser as date_parser
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings

from src.config import (
    CHAT_MODEL,
    COLLECTION_NAME,
    EMBED_MODEL,
    INDEX_DIR,
    OLLAMA_BASE_URL,
)

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

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a thoughtful assistant helping someone reflect on their past "
            "Facebook group posts from a coaching community. Answer using ONLY the "
            "provided posts. Cite dates when relevant. If the posts do not contain "
            "enough information, say so clearly.",
        ),
        (
            "human",
            "Posts:\n\n{context}\n\nQuestion: {question}",
        ),
    ]
)

SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Summarize the themes, celebrations, and revelations in these coaching "
            "group posts. Be specific and reference dates where helpful.",
        ),
        (
            "human",
            "Posts to summarize:\n\n{context}\n\nSummary request: {question}",
        ),
    ]
)


def get_vector_store() -> Chroma:
    if not INDEX_DIR.exists():
        raise FileNotFoundError(
            "Index not found. Run `make ingest` after adding your Facebook export to data/."
        )

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(INDEX_DIR),
    )


def get_llm() -> ChatOllama:
    return ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.2)


def _is_summary_query(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("summarize", "summary", "overview", "themes", "recap"))


def _parse_month_year(question: str) -> tuple[str, str] | None:
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


def _parse_single_date(question: str) -> str | None:
    # Try explicit dates like Sep 02, 2025 or 2025-09-02
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


def _iso_to_int(iso_date: str) -> int:
    return int(iso_date.replace("-", ""))


def _docs_from_results(results: dict) -> list[Document]:
    return [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(results.get("documents", []), results.get("metadatas", []))
    ]


def _format_docs(docs: list[Document]) -> str:
    blocks = []
    for doc in docs:
        meta = doc.metadata
        blocks.append(
            f"[{meta.get('post_date', 'unknown date')} | {meta.get('group_name', '')} | {meta.get('post_type', '')}]\n"
            f"{doc.page_content}"
        )
    return "\n\n---\n\n".join(blocks)


def _retrieve_docs(store: Chroma, question: str, k: int = 8) -> list[Document]:
    single_date = _parse_single_date(question)
    month_range = None if single_date else _parse_month_year(question)
    summarize = _is_summary_query(question)

    if single_date and not summarize:
        results = store.get(where={"post_date": single_date})
        docs = _docs_from_results(results)
        if docs:
            return docs

    if month_range:
        start, end = month_range
        results = store.get(
            where={
                "$and": [
                    {"post_date_int": {"$gte": _iso_to_int(start)}},
                    {"post_date_int": {"$lt": _iso_to_int(end)}},
                ]
            }
        )
        docs = _docs_from_results(results)
        if docs:
            return docs

    retriever = store.as_retriever(search_kwargs={"k": k if not summarize else min(k * 2, 20)})
    return retriever.invoke(question)


def _batch_summarize(llm: ChatOllama, docs: list[Document], question: str) -> str:
    if len(docs) <= 12:
        context = _format_docs(docs)
        chain = SUMMARY_PROMPT | llm
        return chain.invoke({"context": context, "question": question}).content

    batch_size = 10
    partials: list[str] = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        context = _format_docs(batch)
        chain = SUMMARY_PROMPT | llm
        partial = chain.invoke(
            {"context": context, "question": "Summarize key themes in this batch."}
        ).content
        partials.append(partial)

    final_context = "\n\n".join(f"Batch {i + 1}:\n{p}" for i, p in enumerate(partials))
    chain = SUMMARY_PROMPT | llm
    return chain.invoke({"context": final_context, "question": question}).content


def ask(question: str) -> dict:
    store = get_vector_store()
    llm = get_llm()
    docs = _retrieve_docs(store, question)

    if not docs:
        return {
            "answer": "I could not find any posts matching that question in your indexed data.",
            "sources": [],
        }

    if _is_summary_query(question):
        answer = _batch_summarize(llm, docs, question)
    else:
        context = _format_docs(docs)
        chain = ANSWER_PROMPT | llm
        answer = chain.invoke({"context": context, "question": question}).content

    sources = [
        {
            "date": d.metadata.get("post_date", ""),
            "group": d.metadata.get("group_name", ""),
            "type": d.metadata.get("post_type", ""),
            "preview": d.page_content[:300],
        }
        for d in docs[:10]
    ]

    return {"answer": answer, "sources": sources}
