"""Runtime config — HR Agent.

Employee self-serve only. No implementation-consultant / multi-SaaS code paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.deepseek import DeepSeek

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PERSIST_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "employee_hr_selfserve"  # legacy id — do not rename (breaks local Chroma index)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
SIMILARITY_TOP_K = 4

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
LLM_MODEL_NAME = "deepseek-chat"

PRODUCT_NAME = "HR Agent"
PRODUCT_TAGLINE = "Company policy + standard HR how-tos, with citations"


def project_root() -> Path:
    return PROJECT_ROOT


def _api_key_from_streamlit() -> str | None:
    try:
        import streamlit as st
    except ImportError:
        return None
    try:
        secrets = st.secrets
        if "DEEPSEEK_API_KEY" in secrets:
            return str(secrets["DEEPSEEK_API_KEY"]).strip()
        if hasattr(secrets, "get"):
            val = secrets.get("DEEPSEEK_API_KEY")
            if val:
                return str(val).strip()
    except Exception:
        return None
    return None


def require_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not api_key or api_key.lower().startswith("your_"):
        api_key = (_api_key_from_streamlit() or "").strip()
    if not api_key or api_key.lower().startswith("your_"):
        raise RuntimeError(
            "DEEPSEEK_API_KEY missing. For local runs, copy .env.example to .env and set your key. "
            "On Streamlit Community Cloud, add DEEPSEEK_API_KEY to app Secrets (TOML)."
        )
    return api_key


def configure_settings() -> None:
    api_key = require_api_key()
    Settings.llm = DeepSeek(model=LLM_MODEL_NAME, api_key=api_key, temperature=0)
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
