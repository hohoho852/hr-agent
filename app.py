"""Streamlit UI — HR Agent (minimal chat shell)."""

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
    SAMPLE_COMPANY_NAME,
    SAMPLE_COMPANY_NOTE,
    demo_cooldown_sec,
    demo_limits_enabled,
    demo_session_limit,
)
from src.query import (
    chat_query,
    condensed_question_from_response,
    get_chat_engine,
    index_needs_build,
)

EXAMPLE_QUESTIONS = [
    "How many annual leave days do I get?",
    "How do I request time off?",
    "How do I update my home address?",
    "What is the default hybrid work pattern?",
    "How do I submit an expense claim?",
    "When should I contact HR instead of self-serve?",
]

EMPTY_STATE_TAGLINE = "Policy and HR how-tos, with sources. Inform only."

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    #MainMenu, footer, header[data-testid="stHeader"] {
        visibility: hidden;
    }
    .block-container {
        padding-top: 0.75rem;
        padding-bottom: 0.5rem;
        max-width: 760px;
    }
    .hr-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.35rem 0 1rem;
        border-bottom: 1px solid #ececec;
        margin-bottom: 0.5rem;
    }
    .hr-header-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0;
        letter-spacing: -0.01em;
    }
    .empty-state {
        text-align: center;
        padding: 3.5rem 1rem 2rem;
    }
    .empty-state h1 {
        font-size: 1.75rem !important;
        font-weight: 650 !important;
        letter-spacing: -0.03em;
        margin: 0 0 0.5rem !important;
        color: #1a1a1a;
    }
    .empty-state p {
        color: #6b7280;
        font-size: 0.95rem;
        margin: 0 0 1.75rem;
        line-height: 1.5;
    }
    .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
        max-width: 640px;
        margin: 0 auto;
    }
    div[data-testid="column"] .stButton > button {
        border-radius: 999px;
        border: 1px solid #e0e0e0;
        background: #fafafa;
        color: #374151;
        font-size: 0.85rem;
        padding: 0.35rem 0.85rem;
        white-space: normal;
        height: auto;
        min-height: 2.25rem;
        line-height: 1.3;
    }
    div[data-testid="column"] .stButton > button:hover {
        border-color: #c8c8c8;
        background: #f3f3f3;
        color: #111;
    }
    [data-testid="stChatMessage"] {
        max-width: 100%;
    }
    section[data-testid="stSidebar"] {
        background: #fafafa;
    }
    .hr-subtle {
        color: #6b7280;
        font-size: 0.85rem;
        line-height: 1.45;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- session state ---
if "history" not in st.session_state:
    st.session_state.history = []
if "ask_count" not in st.session_state:
    st.session_state.ask_count = 0
if "last_ask_ts" not in st.session_state:
    st.session_state.last_ask_ts = 0.0
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def _new_chat() -> None:
    st.session_state.history = []
    st.session_state.pending_question = None


# ---------- Sidebar (minimal) ----------
with st.sidebar:
    if st.button("New chat", use_container_width=True):
        _new_chat()
        st.rerun()
    if demo_limits_enabled():
        limit = demo_session_limit()
        st.caption(
            f"{st.session_state.ask_count}/{limit} questions · "
            f"{int(demo_cooldown_sec())}s cooldown"
        )
    with st.expander("About"):
        st.markdown(
            f"""
**Sample employer:** {SAMPLE_COMPANY_NAME} (fictional).

{SAMPLE_COMPANY_NOTE}

**Boundary:** Informs only — does not submit leave, change pay, or approve exceptions.
"""
        )


@st.cache_resource(show_spinner=False)
def load_engine():
    return get_chat_engine()


try:
    if index_needs_build():
        with st.spinner(
            "Preparing the handbook index (first start may take a few minutes)…"
        ):
            engine = load_engine()
    else:
        with st.spinner("Loading assistant…"):
            engine = load_engine()
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not start the assistant: {exc}")
    st.info(
        "Set `LLM_API_KEY` (or `OPENAI_API_KEY`) in `.env` / Streamlit Secrets. "
        "Optional: `LLM_MODEL`, `LLM_API_BASE` for your provider. "
        "Ensure policy documents exist under `data/`."
    )
    st.stop()


def _limits_block() -> str | None:
    if not demo_limits_enabled():
        return None
    limit = demo_session_limit()
    if limit and st.session_state.ask_count >= limit:
        return (
            f"Demo session limit reached ({limit} questions). "
            "Clone the repo and run locally with your own `LLM_API_KEY` for unlimited use."
        )
    cooldown = demo_cooldown_sec()
    elapsed = time.time() - float(st.session_state.last_ask_ts or 0.0)
    if st.session_state.last_ask_ts and cooldown and elapsed < cooldown:
        wait = int(cooldown - elapsed) + 1
        return f"Please wait {wait}s before the next question."
    return None


def _keyword_terms(*texts: str) -> list[str]:
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

    window_start = max(0, hit - max_len // 3)
    heading = lower.rfind("\n## ", 0, hit + 1)
    if heading >= 0 and hit - heading < max_len:
        window_start = heading + 1

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
    rows.sort(key=lambda r: (-r["term_hits"], -r["score"]))
    for r in rows:
        r.pop("term_hits", None)
    return rows


def _render_sources(sources: list[dict]) -> None:
    with st.expander("Sources — verify before acting", expanded=False):
        if not sources:
            st.write("No sources returned — do not act on an ungrounded answer.")
            return
        for j, src in enumerate(sources, 1):
            st.markdown(
                f"**Source {j}** · `{src['file']}` · relevance {src['score']:.2f}"
            )
            st.write(src["snippet"])
            if j < len(sources):
                st.divider()


def _queue_user_message(question: str) -> None:
    q = (question or "").strip()
    if not q:
        return
    st.session_state.history.append({"role": "user", "content": q})
    block = _limits_block()
    if block:
        st.session_state.history.append(
            {
                "role": "assistant",
                "content": block,
                "sources": [],
                "system_note": True,
            }
        )


def _generate_assistant_reply() -> None:
    turns = st.session_state.history
    if not turns or turns[-1]["role"] != "user":
        return

    q = turns[-1]["content"]
    prior = turns[:-1]
    response = chat_query(engine, q, prior)
    answer = response.response or ""
    snippet_q = condensed_question_from_response(response) or q
    sources = _source_payload(response, question=snippet_q, answer=answer)
    st.session_state.history.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
    st.session_state.ask_count += 1
    st.session_state.last_ask_ts = time.time()


def _render_empty_state() -> None:
    st.markdown(
        f"""
<div class="empty-state">
  <h1>{PRODUCT_NAME}</h1>
  <p>{EMPTY_STATE_TAGLINE}</p>
</div>
""",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        with cols[i % 2]:
            if st.button(q, key=f"chip_{i}"):
                st.session_state.pending_question = q
                st.rerun()


# ---------- Main ----------
hdr_left, hdr_right = st.columns([5, 1])
with hdr_left:
    st.markdown(f'<p class="hr-header-title">{PRODUCT_NAME}</p>', unsafe_allow_html=True)
with hdr_right:
    if st.button("New chat", key="header_new_chat"):
        _new_chat()
        st.rerun()

if not st.session_state.history:
    _render_empty_state()
else:
    for turn in st.session_state.history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn["role"] == "assistant" and "sources" in turn:
                _render_sources(turn.get("sources") or [])

if st.session_state.pending_question:
    _queue_user_message(st.session_state.pending_question)
    st.session_state.pending_question = None
    st.rerun()

if (
    st.session_state.history
    and st.session_state.history[-1]["role"] == "user"
):
    with st.spinner("Finding sources and drafting an answer…"):
        try:
            _generate_assistant_reply()
        except Exception as exc:  # noqa: BLE001
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "content": f"Sorry, I could not answer that: {exc}",
                    "sources": [],
                    "system_note": True,
                }
            )
    st.rerun()

if prompt := st.chat_input(
    "Ask anything about leave, hybrid work, expenses…"
):
    _queue_user_message(prompt)
    st.rerun()
