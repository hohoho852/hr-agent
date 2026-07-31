"""Runtime config — HR Agent (Track B portfolio product).

Single product. No implementation-consultant / multi-SaaS code paths.
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
PRODUCT_TAGLINE = "Company policy + standard HR how-tos — deflect Tier-1 tickets"


def project_root() -> Path:
    return PROJECT_ROOT


def require_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not api_key or api_key.lower().startswith("your_"):
        raise RuntimeError(
            "DEEPSEEK_API_KEY missing. Copy .env.example to .env and set your key."
        )
    return api_key


def configure_settings() -> None:
    api_key = require_api_key()
    Settings.llm = DeepSeek(model=LLM_MODEL_NAME, api_key=api_key, temperature=0)
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
