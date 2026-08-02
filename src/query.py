"""Load HR Agent index and create a citation-friendly query engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
from llama_index.core import PromptTemplate, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

from src.config import (
    COLLECTION_NAME,
    PERSIST_DIR,
    QA_SYSTEM_PROMPT,
    SIMILARITY_TOP_K,
    configure_settings,
    project_root,
)

QA_PROMPT = PromptTemplate(
    QA_SYSTEM_PROMPT
    + "\n\nContext information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context only, answer the employee question.\n"
    "Question: {query_str}\n"
    "Answer: "
)

REFINE_PROMPT = PromptTemplate(
    """The original query is as follows: {query_str}
We have provided an existing answer: {existing_answer}
We have the opportunity to refine the existing answer (only if needed) with some more \
context below.

Instructions (same as before):
- Answer ONLY from the retrieved context — not general knowledge.
- For how-to questions, prefer short numbered steps.
- If context is insufficient, say so and suggest an HR ticket.
- Inform ≠ execute: never claim workflow submission or approvals.
- Escalate exceptions, payroll, grievances, and sensitive cases to HR.

------------
{context_msg}
------------
Given the new context, refine the original answer to better answer the query. If the \
context isn't useful, return the original answer.
Refined Answer: """
)


def _ensure_root() -> None:
    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def index_needs_build() -> bool:
    persist_path = Path(PERSIST_DIR)
    if not persist_path.exists():
        return True
    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    return collection.count() == 0


def ensure_index() -> bool:
    """Build index from data/ when missing or empty. Returns True if ingest ran."""
    if not index_needs_build():
        return False
    from src.ingest import build_index

    build_index(reset=True)
    return True


def get_query_engine(similarity_top_k: int = SIMILARITY_TOP_K, *, ensure: bool = True):
    if ensure:
        ensure_index()
    configure_settings()
    persist_path = Path(PERSIST_DIR)
    if not persist_path.exists():
        raise FileNotFoundError(
            f"No index at {persist_path}. Run: python -m src.ingest"
        )

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    if collection.count() == 0:
        raise RuntimeError("Empty index. Run: python -m src.ingest")

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )
    return index.as_query_engine(
        similarity_top_k=similarity_top_k,
        response_mode="compact",
        text_qa_template=QA_PROMPT,
        refine_template=REFINE_PROMPT,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CLI smoke query — HR Agent")
    parser.add_argument(
        "--question",
        default="How do I request annual leave in SuccessFactors?",
    )
    args = parser.parse_args(argv)
    engine = get_query_engine()
    print(f"Q: {args.question}\n")
    response = engine.query(args.question)
    print(response)
    print("\nSources:")
    for node in response.source_nodes:
        meta = node.metadata or {}
        name = meta.get("file_name") or meta.get("filename") or "Unknown"
        score = node.score if node.score is not None else 0.0
        print(f"- {name} (score: {score:.3f})")


if __name__ == "__main__":
    _ensure_root()
    main()
