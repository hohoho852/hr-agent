"""Runtime config — HR Agent.

Employee self-serve only - company policy and standard HR how-tos.
Generation model is customer-configurable (OpenAI-compatible API).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PERSIST_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "employee_hr_selfserve"  # legacy id — do not rename (breaks local Chroma index)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
SIMILARITY_TOP_K = 4

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Defaults favor a cheap OpenAI-compatible endpoint; override via env/secrets.
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
DEFAULT_LLM_API_BASE = "https://api.deepseek.com/v1"

PRODUCT_NAME = "HR Agent"
PRODUCT_TAGLINE = "Company policy + standard HR how-tos, with citations"

# Bundled handbook uses a fictional sample employer (not a real company).
SAMPLE_COMPANY_NAME = "Demo Hong Kong Limited"
SAMPLE_COMPANY_NOTE = (
    "Demo corpus uses a fictional sample employer (Demo Hong Kong Limited). "
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
7. The bundled demo corpus describes a fictional sample employer (Demo Hong Kong Limited) unless the operator replaced the data pack.
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


def _load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def _secret_get(*names: str) -> str | None:
    """Read the first non-empty value from env, then Streamlit secrets."""
    _load_env()
    for name in names:
        val = (os.environ.get(name) or "").strip()
        if val and not val.lower().startswith("your_"):
            return val

    try:
        import streamlit as st
    except ImportError:
        return None

    try:
        secrets = st.secrets
    except Exception:
        return None

    for name in names:
        try:
            if name in secrets:
                val = str(secrets[name]).strip()
                if val and not val.lower().startswith("your_"):
                    return val
            if hasattr(secrets, "get"):
                raw = secrets.get(name)
                if raw:
                    val = str(raw).strip()
                    if val and not val.lower().startswith("your_"):
                        return val
        except Exception:
            continue
    return None


def llm_model_name() -> str:
    return _secret_get("LLM_MODEL", "OPENAI_MODEL") or DEFAULT_LLM_MODEL


def llm_api_base() -> str | None:
    """Optional OpenAI-compatible base URL (Azure, DeepSeek, vLLM, gateway, etc.)."""
    return _secret_get("LLM_API_BASE", "OPENAI_API_BASE", "OPENAI_BASE_URL")


def require_api_key() -> str:
    """Customer-supplied generation key (provider-agnostic)."""
    api_key = _secret_get(
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        # Legacy demo name — still accepted so existing Streamlit secrets keep working.
        "DEEPSEEK_API_KEY",
    )
    if not api_key:
        raise RuntimeError(
            "LLM API key missing. Set LLM_API_KEY (preferred) or OPENAI_API_KEY "
            "in `.env` (local) or Streamlit Secrets (cloud). "
            "Optional: LLM_MODEL, LLM_API_BASE for non-OpenAI endpoints. "
            "Legacy DEEPSEEK_API_KEY is still accepted."
        )
    return api_key


def configure_settings() -> None:
    """Wire embeddings + customer-chosen chat model (OpenAI-compatible client).

    Uses OpenAILike (not OpenAI) so non-OpenAI model ids like deepseek-v4-flash
    are not rejected by LlamaIndex's OpenAI model-name allowlist.
    """
    api_key = require_api_key()
    model = llm_model_name()
    api_base = llm_api_base()

    # If only a legacy DeepSeek key is present and base was not set, keep demo default base + model.
    if api_base is None and _secret_get("DEEPSEEK_API_KEY") and not _secret_get(
        "LLM_API_KEY", "OPENAI_API_KEY"
    ):
        api_base = DEFAULT_LLM_API_BASE
        # Always prefer current default when caller did not pin LLM_MODEL / OPENAI_MODEL.
        if not _secret_get("LLM_MODEL", "OPENAI_MODEL"):
            model = DEFAULT_LLM_MODEL
        # Migrate retired DeepSeek ids still sitting in old secrets/env.
        elif model in {"deepseek-chat", "deepseek-reasoner"}:
            model = DEFAULT_LLM_MODEL

    # Retired DeepSeek ids even when LLM_MODEL is set explicitly in secrets.
    if model in {"deepseek-chat", "deepseek-reasoner"}:
        model = DEFAULT_LLM_MODEL

    llm_kwargs: dict = {
        "model": model,
        "api_key": api_key,
        "temperature": 0,
        "is_chat_model": True,
        "is_function_calling_model": False,
        # Generous default; override via provider docs if needed.
        "context_window": 128000,
    }
    if api_base:
        llm_kwargs["api_base"] = api_base

    Settings.llm = OpenAILike(**llm_kwargs)
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
