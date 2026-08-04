"""Streamlit UI — HR Agent (employee self-serve chat demo)."""

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

WELCOME_MESSAGE = (
    "I answer questions about **company policy** and **standard HR how-tos** "
    "using your handbook pack, with sources on every reply.\n\n"
    "**Hard boundary:** I inform only — I do **not** submit leave, change pay, "
    "update your profile, or approve exceptions. For those, use your HR system or "
    "open an HR ticket."
)

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 1rem;
        max-width: 820px;
    }
    h1 {
        font-weight: 650 !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.15rem !important;
    }
    [data-testid="stCaption"] {
        color: #5b6570 !important;
        font-size: 0.98rem !important;
    }
    section[data-testid="stSidebar"] {
        background: #f4f6f9;
        border-right: 1px solid #e4e8ef;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        letter-spacing: -0.01em;
    }
    .hr-kicker {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #3d5a80;
        background: #e8eef6;
        border-radius: 999px;
        padding: 0.22rem 0.65rem;
        margin-bottom: 0.55rem;
    }
    .hr-subtle {
        color: #6b7280;
        font-size: 0.9rem;
        line-height: 1.45;
    }
    [data-testid="stChatMessage"] {
        max-width: 100%;
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

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f"### {PRODUCT_NAME}")
    st.caption(PRODUCT_TAGLINE)
    st.markdown(
        f"""
**What this is**  
An employee assistant for **company policy** and **standard HR how-tos**, with a citation on every answer.

**Who uses it**  
- Employees — self-serve answers  
- People Ops — deflect repetitive Tier-1 volume  

**Hard boundary**  
Informs only. Does **not** submit leave, change pay, or approve exceptions.

**Sample employer**  
{SAMPLE_COMPANY_NAME} (fictional). Not a real company handbook.

**Source documents**  
Client-style PDFs live in the repo `source/` folder (what an HR team would typically provide). The runtime index is built from `data/` (same content, machine-readable).
"""
    )
    if demo_limits_enabled():
        limit = demo_session_limit()
        st.caption(
            f"Demo session: {st.session_state.ask_count}/{limit} questions · "
            f"{int(demo_cooldown_sec())}s between asks"
        )
    st.divider()
    st.markdown("**Try a question**")
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if st.button(q, key=f"ex_{i}", use_container_width=True):
            st.session_state.pending_question = q
            st.rerun()
    if st.button("New conversation", use_container_width=True):
        # Clear transcript only; keep ask_count so demo session limits still apply.
        st.session_state.history = []
        st.session_state.pending_question = None
        st.rerun()
    st.caption(
        "Replace `data/` with your licensed policies for a real tenant. "
        "Rebuild: `python -m src.ingest`."
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


# ---------- Main ----------
st.markdown('<div class="hr-kicker">Employee self-serve</div>', unsafe_allow_html=True)
st.title(PRODUCT_NAME)
st.caption(PRODUCT_TAGLINE)
st.markdown(
    f'<p class="hr-subtle">{SAMPLE_COMPANY_NOTE}</p>',
    unsafe_allow_html=True,
)

if not st.session_state.history:
    with st.chat_message("assistant"):
        st.markdown(WELCOME_MESSAGE)

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

if prompt := st.chat_input("Ask about leave, hybrid work, expenses, or profile updates…"):
    _queue_user_message(prompt)
    st.rerun()
