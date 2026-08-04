"""Load HR Agent index and create citation-friendly query / chat engines."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import chromadb
from llama_index.core import PromptTemplate, StorageContext, VectorStoreIndex
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.chat_engine.types import AgentChatResponse, ChatMode
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

CONTEXT_PROMPT = PromptTemplate(
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context only, answer the employee question.\n"
)

# Last N user+assistant pairs passed into condensation (controls token use).
CHAT_HISTORY_TURNS = 8


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


def _load_vector_index(
    similarity_top_k: int = SIMILARITY_TOP_K,
    *,
    ensure: bool = True,
) -> VectorStoreIndex:
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
    return VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )


def _attach_qa_prompt(engine) -> None:
    """Best-effort attach of employee-assistant QA template across LlamaIndex versions."""
    try:
        engine.update_prompts({"response_synthesizer:text_qa_template": QA_PROMPT})
        return
    except Exception:
        pass
    try:
        synthesizer = getattr(engine, "_response_synthesizer", None)
        if synthesizer is None:
            return
        if hasattr(synthesizer, "update_prompts"):
            synthesizer.update_prompts({"text_qa_template": QA_PROMPT})
        elif hasattr(synthesizer, "text_qa_template"):
            synthesizer.text_qa_template = QA_PROMPT
        elif hasattr(synthesizer, "_text_qa_template"):
            synthesizer._text_qa_template = QA_PROMPT
    except Exception:
        pass


def get_query_engine(similarity_top_k: int = SIMILARITY_TOP_K, *, ensure: bool = True):
    index = _load_vector_index(similarity_top_k=similarity_top_k, ensure=ensure)
    engine = index.as_query_engine(
        similarity_top_k=similarity_top_k,
        response_mode="compact",
        text_qa_template=QA_PROMPT,
    )
    _attach_qa_prompt(engine)
    return engine


def get_chat_engine(similarity_top_k: int = SIMILARITY_TOP_K, *, ensure: bool = True):
    """CondensePlusContext chat engine: rewrite follow-ups, retrieve, answer with sources."""
    index = _load_vector_index(similarity_top_k=similarity_top_k, ensure=ensure)
    return index.as_chat_engine(
        chat_mode=ChatMode.CONDENSE_PLUS_CONTEXT,
        similarity_top_k=similarity_top_k,
        context_prompt=CONTEXT_PROMPT,
        system_prompt=QA_SYSTEM_PROMPT,
    )


def history_to_chat_messages(
    turns: list[dict[str, Any]],
    *,
    max_turns: int = CHAT_HISTORY_TURNS,
) -> list[ChatMessage]:
    """Map UI turn dicts to LlamaIndex chat messages for condensation."""
    messages: list[ChatMessage] = []
    eligible = [
        t
        for t in turns
        if t.get("role") in ("user", "assistant") and not t.get("system_note")
    ]
    for turn in eligible[-(max_turns * 2) :]:
        role = (
            MessageRole.USER if turn["role"] == "user" else MessageRole.ASSISTANT
        )
        messages.append(ChatMessage(role=role, content=turn.get("content") or ""))
    return messages


def chat_query(
    engine,
    message: str,
    history: list[dict[str, Any]] | None = None,
    *,
    max_history_turns: int = CHAT_HISTORY_TURNS,
) -> AgentChatResponse:
    """Answer with retrieval + condensation over prior turns (follow-ups supported)."""
    chat_history = history_to_chat_messages(
        history or [], max_turns=max_history_turns
    )
    return engine.chat(message, chat_history=chat_history)


def condensed_question_from_response(response: AgentChatResponse) -> str | None:
    """Retrieval query after condensation (better snippet highlighting on follow-ups)."""
    for source in response.sources or []:
        raw_input = source.raw_input or {}
        condensed = raw_input.get("message")
        if condensed:
            return str(condensed)
    return None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CLI smoke query — HR Agent")
    parser.add_argument(
        "--question",
        default="How do I request annual leave?",
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
