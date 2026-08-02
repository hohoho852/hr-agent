"""Load HR Agent index and create a citation-friendly query engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

from src.config import (
    COLLECTION_NAME,
    PERSIST_DIR,
    SIMILARITY_TOP_K,
    configure_settings,
    project_root,
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
