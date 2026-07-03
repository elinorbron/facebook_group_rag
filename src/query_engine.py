from __future__ import annotations

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
from src.query_parsing import format_docs, iso_to_int, is_summary_query, parse_month_year, parse_single_date

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


def _docs_from_results(results: dict) -> list[Document]:
    return [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(results.get("documents", []), results.get("metadatas", []))
    ]


def _retrieve_docs(store: Chroma, question: str, k: int = 8) -> list[Document]:
    single_date = parse_single_date(question)
    month_range = None if single_date else parse_month_year(question)
    summarize = is_summary_query(question)

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
                    {"post_date_int": {"$gte": iso_to_int(start)}},
                    {"post_date_int": {"$lt": iso_to_int(end)}},
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
        context = format_docs(docs)
        chain = SUMMARY_PROMPT | llm
        return chain.invoke({"context": context, "question": question}).content

    batch_size = 10
    partials: list[str] = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        context = format_docs(batch)
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

    if is_summary_query(question):
        answer = _batch_summarize(llm, docs, question)
    else:
        context = format_docs(docs)
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
