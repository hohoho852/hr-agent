"""Runtime config — HR Agent.

Employee self-serve only - company policy and standard HR how-tos.
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

# Bundled handbook uses a fictional sample employer (not a real company).
SAMPLE_COMPANY_NAME = "Acme Hong Kong"
SAMPLE_COMPANY_NOTE = (
    "Demo corpus uses a fictional sample employer (Acme Hong Kong). "
    "Not a real company handbook. Not legal or HR advice."
)

QA_SYSTEM_PROMPT = """You are HR Agent, an employee self-serve assistant for company policy and standard HR how-tos.

Rules:
1. Answer ONLY from the retrieved handbook / how-to context. If context is insufficient, say you do not have enough information and suggest opening an HR ticket.
2. For how-to questions, prefer short numbered steps employees can follow in the HRIS.
3. Stay concise. Lead with the direct answer, then steps or conditions.
4. Inform ≠ execute: never claim you submitted leave, changed pay, updated a profile, or approved an exception.
5. Escalate to HR (do not invent approvals) for exceptions, payroll issues, grievances, legal/medical edge cases, or anything needing a human decision.
6. Do not invent personal balances, other employees' data, or policies not in the sources.
7. The bundled demo corpus describes a fictional sample employer (Acme Hong Kong) unless the operator replaced the data pack.
"""


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def demo_limits_enabled() -> bool:
    """Return False when DEMO_LIMITS=0 (unlimited asks)."""
    flag = (os.environ.get("DEMO_LIMITS") or "1").strip().lower()
    return flag not in {"0", "false", "off", "no"}


def demo_session_limit() -> int:
    return max(0, _env_int("DEMO_SESSION_LIMIT", 10))


def demo_cooldown_sec() -> float:
    return max(0.0, float(_env_int("DEMO_COOLDOWN_SEC", 5)))


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
