"""Build persistent Chroma index from employee policy + how-to docs in ./data."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import chromadb
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    PERSIST_DIR,
    configure_settings,
    project_root,
)


def _ensure_root() -> None:
    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def build_index(reset: bool = True):
    configure_settings()
    data_path = DATA_DIR
    persist_path = PERSIST_DIR

    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    documents = SimpleDirectoryReader(
        input_dir=str(data_path),
        recursive=False,
        required_exts=[".pdf", ".txt", ".md", ".docx"],
    ).load_data()
    if not documents:
        raise RuntimeError(f"No documents in {data_path}. Add policy/how-to files.")

    print(f"Loaded {len(documents)} documents from {data_path}")

    if reset and persist_path.exists():
        shutil.rmtree(persist_path)
        print(f"Reset index at {persist_path}")

    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:  # noqa: BLE001
            pass
    collection = client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[splitter],
        show_progress=True,
    )
    print(
        f"Index ready · collection={COLLECTION_NAME} · "
        f"vectors≈{collection.count()} · chunk={CHUNK_SIZE}/{CHUNK_OVERLAP}"
    )
    return index


def main(argv: list[str] | None = None) -> None:
    _ensure_root()
    parser = argparse.ArgumentParser(description="Ingest HR Agent corpus")
    parser.add_argument("--no-reset", action="store_true", help="Do not wipe existing index")
    args = parser.parse_args(argv)
    build_index(reset=not args.no_reset)


if __name__ == "__main__":
    _ensure_root()
    main()
