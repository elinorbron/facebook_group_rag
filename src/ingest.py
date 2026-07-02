from __future__ import annotations

import shutil

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from src.config import COLLECTION_NAME, EMBED_MODEL, GROUP_FILTER, INDEX_DIR, OLLAMA_BASE_URL, parse_group_filters
from src.fb_parser import load_posts


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
    main()
