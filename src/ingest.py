from __future__ import annotations

import shutil
import sys

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from src.config import COLLECTION_NAME, EMBED_MODEL, INDEX_DIR, OLLAMA_BASE_URL, parse_group_filters
from src.fb_parser import load_posts


REQUIRED_METADATA_KEYS = frozenset(
    {"post_date", "post_date_int", "group_name", "post_type", "post_id"}
)


def build_documents():
    posts = load_posts()
    documents = []
    for post in posts:
        documents.append(
            Document(
                page_content=post.to_document_text(),
                metadata={
                    "post_id": post.post_id,
                    "post_date": post.post_date,
                    "post_date_int": int(post.post_date.replace("-", "")),
                    "group_name": post.group_name,
                    "author": post.author,
                    "post_type": post.post_type,
                    "title": post.title,
                    "source_file": post.source_file,
                },
            )
        )
    return documents


def verify_index(expected_count: int) -> None:
    """Integration smoke test: confirm the index is readable after ingest."""
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(INDEX_DIR),
    )

    actual_count = store._collection.count()
    if actual_count != expected_count:
        raise RuntimeError(
            f"Index verification failed: expected {expected_count} documents, found {actual_count}"
        )

    sample = store.get(limit=1, include=["metadatas"])
    metadatas = sample.get("metadatas") or []
    if not metadatas:
        raise RuntimeError("Index verification failed: could not read any stored documents")

    missing = REQUIRED_METADATA_KEYS - set(metadatas[0].keys())
    if missing:
        raise RuntimeError(f"Index verification failed: missing metadata keys {sorted(missing)}")

    print(f"Index verification passed ({actual_count} documents, metadata OK)")


def ingest(reset: bool = True) -> int:
    documents = build_documents()
    if not documents:
        raise RuntimeError("No posts parsed from data/. Check your Facebook export.")

    if reset and INDEX_DIR.exists():
        shutil.rmtree(INDEX_DIR)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(INDEX_DIR),
    )

    print(f"Ingested {len(documents)} posts into {INDEX_DIR}")
    verify_index(len(documents))
    return len(documents)


def main():
    filters = parse_group_filters()
    if filters:
        print(f"Group filter: {', '.join(filters)}")
    else:
        print("Group filter: (none — indexing all posts)")
    count = ingest(reset=True)
    print(f"Done. {count} posts indexed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Ingestion failed due to error: {exc}", file=sys.stderr)
        raise
