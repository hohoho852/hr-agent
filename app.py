"""Streamlit UI — HR Agent."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
    SAMPLE_COMPANY_NAME,
    SAMPLE_COMPANY_NOTE,
    demo_cooldown_sec,
    demo_limits_enabled,
    demo_session_limit,
)
from src.query import get_query_engine, index_needs_build

EXAMPLE_QUESTIONS = [
    "How many annual leave days do I get?",
    "How do I request time off in SuccessFactors?",
    "How do I update my home address?",
    "What is the default hybrid work pattern?",
    "How do I submit an expense claim?",
    "When should I contact HR instead of self-serve?",
]

st.set_page_config(page_title=PRODUCT_NAME, page_icon="📋", layout="centered")

st.title(PRODUCT_NAME)
st.caption(PRODUCT_TAGLINE)
st.write(
    "Ask **company policy** questions and **how to complete standard HR actions** "
    "(leave, profile, expenses). Every answer includes **citations** from the handbook pack."
)

st.info(
    f"**Sample employer:** {SAMPLE_COMPANY_NAME} is a **fictional** company used only for this "
    "demo handbook. Not a real employer. Not legal or HR advice. Replace `data/` with your own "
    "licensed policies for a real deployment.",
    icon="📘",
)

# --- session state ---
if "history" not in st.session_state:
    st.session_state.history = []
if "ask_count" not in st.session_state:
    st.session_state.ask_count = 0
if "last_ask_ts" not in st.session_state:
    st.session_state.last_ask_ts = 0.0
if "prefill" not in st.session_state:
    st.session_state.prefill = ""
if "auto_ask" not in st.session_state:
    st.session_state.auto_ask = False
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

with st.sidebar:
    st.header("About")
    st.markdown(
        f"""
**Users:** Employees  
**Operators:** People Ops / HRIS  

**Job:** Policy Q&A + how-to for standard HR actions  

**Sample data:** {SAMPLE_COMPANY_NAME} (fictional)

**Not this product:** multi-vendor implementation guidance  
(see `hcm-impl-copilot`)

**Controls**
- Citations always on
- Local embeddings (BGE)
- Generation only on retrieved snippets (DeepSeek)
- Informs only — does not submit workflows
"""
    )
    if demo_limits_enabled():
        limit = demo_session_limit()
        st.caption(
            f"Demo limits: {st.session_state.ask_count}/{limit} questions this session · "
            f"{int(demo_cooldown_sec())}s cooldown between asks."
        )
    st.divider()
    st.markdown("**Try asking**")
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if st.button(q, key=f"ex_{i}", use_container_width=True):
            st.session_state.prefill = q
            st.session_state.auto_ask = True
            st.session_state.input_key += 1
            st.rerun()
    st.caption(
        "Rebuild after corpus changes: `python -m src.ingest`. "
        "On Streamlit Cloud, the index builds automatically on first start."
    )


@st.cache_resource(show_spinner=False)
def load_engine():
    return get_query_engine()


try:
    if index_needs_build():
        with st.spinner(
            "First start: downloading embedding model and building index from data/ "
            "(may take several minutes)..."
        ):
            engine = load_engine()
    else:
        with st.spinner("Loading retrieval engine..."):
            engine = load_engine()
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load the query engine: {exc}")
    st.info(
        "Set `DEEPSEEK_API_KEY` in `.env` for local runs, or in Streamlit Cloud Secrets "
        "(TOML key `DEEPSEEK_API_KEY`) for deployment. Add policy/how-to docs to `data/`. "
        "Locally, run `python -m src.ingest`; on Streamlit Cloud the index builds on first start."
    )
    st.stop()

st.warning(
    "Human-in-the-loop: policy guidance only. Does not submit leave, change pay, "
    "or grant exceptions — escalate those to HR."
)


def _limits_block() -> str | None:
    if not demo_limits_enabled():
        return None
    limit = demo_session_limit()
    if limit and st.session_state.ask_count >= limit:
        return (
            f"Demo session limit reached ({limit} questions). "
            "Clone the repo and run locally with your own `DEEPSEEK_API_KEY` for unlimited use."
        )
    cooldown = demo_cooldown_sec()
    elapsed = time.time() - float(st.session_state.last_ask_ts or 0.0)
    if st.session_state.last_ask_ts and cooldown and elapsed < cooldown:
        wait = int(cooldown - elapsed) + 1
        return f"Please wait {wait}s before the next question (demo cooldown)."
    return None


def _keyword_terms(*texts: str) -> list[str]:
    """Light terms for centering citation snippets on the asked topic."""
    stop = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "do",
        "we",
        "i",
        "my",
        "is",
        "are",
        "how",
        "many",
        "much",
        "what",
        "when",
        "where",
        "who",
        "with",
        "from",
        "this",
        "that",
        "have",
        "has",
        "get",
        "got",
        "can",
        "you",
        "your",
        "our",
        "me",
        "please",
        "about",
        "does",
        "did",
    }
    seen: set[str] = set()
    out: list[str] = []
    for text in texts:
        for raw in (text or "").lower().replace("?", " ").replace(",", " ").split():
            tok = "".join(ch for ch in raw if ch.isalnum() or ch in "-_")
            if len(tok) < 3 or tok in stop or tok in seen:
                continue
            seen.add(tok)
            out.append(tok)
    return out


def _relevant_snippet(content: str, question: str, answer: str = "", max_len: int = 700) -> str:
    """Show the part of the chunk that matches the question, not always the file head.

    Large policy chunks often start with annual leave; marriage/other rows sit later.
    Truncating at char 0 made Source 1 look unrelated even when the answer was grounded.
    """
    text = (content or "").strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text

    lower = text.lower()
    terms = _keyword_terms(question, answer)
    hit = -1
    for term in terms:
        idx = lower.find(term)
        if idx >= 0:
            hit = idx
            break

    if hit < 0:
        snippet = text[:max_len].rstrip()
        return snippet + ("..." if len(text) > max_len else "")

    # Prefer starting at a nearby markdown heading so the section title is visible.
    window_start = max(0, hit - max_len // 3)
    heading = lower.rfind("\n## ", 0, hit + 1)
    if heading >= 0 and hit - heading < max_len:
        window_start = heading + 1  # keep '## '

    start = max(0, min(window_start, max(0, len(text) - max_len)))
    end = min(len(text), start + max_len)
    if hit >= end or hit < start:
        start = max(0, hit - max_len // 3)
        end = min(len(text), start + max_len)

    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def _source_payload(response, question: str = "", answer: str = "") -> list[dict]:
    rows: list[dict] = []
    terms = _keyword_terms(question, answer)
    for node in response.source_nodes or []:
        meta = node.metadata or {}
        fname = meta.get("file_name") or meta.get("filename") or "Unknown"
        score = node.score if node.score is not None else 0.0
        content = node.node.get_content()
        lower = (content or "").lower()
        term_hits = sum(1 for t in terms if t in lower)
        rows.append(
            {
                "file": fname,
                "score": float(score),
                "snippet": _relevant_snippet(content, question, answer),
                "term_hits": term_hits,
            }
        )
    # Surface chunks that actually mention the asked topic first (still keep all).
    rows.sort(key=lambda r: (-r["term_hits"], -r["score"]))
    for r in rows:
        r.pop("term_hits", None)
    return rows


def run_question(question: str) -> bool:
    """Run one Q&A. Returns True if a model call was attempted successfully."""
    q = (question or "").strip()
    if not q:\n        st.warning("Enter a question first.")
        return False

    block = _limits_block()
    if block:
        st.warning(block)
        return False

    with st.spinner("Retrieving sources and generating answer..."):
        try:
            response = engine.query(q)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Query failed: {exc}")
            return False

    answer = response.response or ""
    sources = _source_payload(response, question=q, answer=answer)
    st.session_state.history.insert(
        0,
        {"question": q, "answer": answer, "sources": sources},
    )
    st.session_state.ask_count += 1
    st.session_state.last_ask_ts = time.time()
    st.session_state.prefill = ""
    return True


# One-click example path (sidebar set auto_ask)
if st.session_state.auto_ask and st.session_state.prefill:
    q = st.session_state.prefill
    st.session_state.auto_ask = False
    run_question(q)
    st.session_state.input_key += 1
    st.rerun()

# st.form: pressing Enter submits (fixes click-only Ask bug)
with st.form(key=f"ask_form_{st.session_state.input_key}", clear_on_submit=True):
    query = st.text_input(
        "Your question:",
        value=st.session_state.prefill,
        placeholder="e.g. How do I request annual leave in SuccessFactors?",
    )
    submitted = st.form_submit_button("Ask", type="primary")

if submitted:
    if run_question(query):
        st.session_state.input_key += 1
        st.rerun()

# --- history ---
if st.session_state.history:
    st.subheader("This session")
    for i, turn in enumerate(st.session_state.history):
        st.markdown(f"**You:** {turn['question']}")
        st.markdown(f"**HR Agent:** {turn['answer']}")
        with st.expander("Sources (verify before acting)", expanded=False):
            if not turn["sources"]:
                st.write("No sources returned — do not act on an ungrounded answer.")
            for j, src in enumerate(turn["sources"], 1):
                st.markdown(
                    f"**Source {j}** — `{src['file']}` (score: {src['score']:.3f})"
                )
                st.write(src["snippet"])
                if j < len(turn["sources"]):
                    st.divider()
        if i < len(st.session_state.history) - 1:
            st.divider()
else:
    st.caption(SAMPLE_COMPANY_NOTE)
