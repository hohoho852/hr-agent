"""Streamlit UI — HR Agent (ChatGPT-style chat shell)."""

from __future__ import annotations

import sys
import time
import uuid
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
TITLE_MAX_LEN = 40

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    #MainMenu, footer, header[data-testid="stHeader"] {
        visibility: hidden;
    }
    section[data-testid="stSidebar"] {
        background: #f7f7f8;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }
    .sidebar-brand {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0 0 0.75rem;
        letter-spacing: -0.01em;
    }
    .main .block-container {
        padding-top: 0.75rem;
        padding-bottom: 0.5rem;
        max-width: 780px;
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
    /* Assistant: default left alignment */
    [data-testid="stChatMessage"] {
        max-width: 100%;
    }
    /* User: bubble on the right (ChatGPT / Grok pattern) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stChatMessageContent"] {
        background: #f4f4f4;
        border-radius: 1.25rem;
        padding: 0.65rem 1rem;
        max-width: min(75%, 42rem);
        margin-left: auto;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
    [data-testid="stChatMessageContent"] {
        max-width: min(85%, 46rem);
    }
</style>
""",
    unsafe_allow_html=True,
)


def _new_conversation_id() -> str:
    return uuid.uuid4().hex[:12]


def _empty_conversation() -> dict:
    now = time.time()
    return {
        "title": "New chat",
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }


def _init_session_state() -> None:
    if "conversations" not in st.session_state:
        cid = _new_conversation_id()
        st.session_state.conversations = {cid: _empty_conversation()}
        st.session_state.active_conversation_id = cid
    if "ask_count" not in st.session_state:
        st.session_state.ask_count = 0
    if "last_ask_ts" not in st.session_state:
        st.session_state.last_ask_ts = 0.0
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None


_init_session_state()


def _active_conversation() -> dict:
    cid = st.session_state.active_conversation_id
    return st.session_state.conversations[cid]


def _active_messages() -> list:
    return _active_conversation()["messages"]


def _title_from_message(text: str) -> str:
    t = (text or "").strip().replace("\n", " ")
    if not t:
        return "New chat"
    if len(t) <= TITLE_MAX_LEN:
        return t
    return t[: TITLE_MAX_LEN - 1].rstrip() + "…"


def _start_new_chat() -> None:
    cid = _new_conversation_id()
    st.session_state.conversations[cid] = _empty_conversation()
    st.session_state.active_conversation_id = cid
    st.session_state.pending_question = None


def _switch_chat(conversation_id: str) -> None:
    if conversation_id in st.session_state.conversations:
        st.session_state.active_conversation_id = conversation_id
        st.session_state.pending_question = None


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f'<p class="sidebar-brand">{PRODUCT_NAME}</p>', unsafe_allow_html=True)
    if st.button("New chat", use_container_width=True, type="primary"):
        _start_new_chat()
        st.rerun()

    st.markdown("---")
    active_id = st.session_state.active_conversation_id
    sorted_chats = sorted(
        st.session_state.conversations.items(),
        key=lambda item: item[1]["updated_at"],
        reverse=True,
    )
    for cid, conv in sorted_chats:
        label = conv["title"] or "New chat"
        if st.button(
            label,
            key=f"conv_{cid}",
            use_container_width=True,
            type="primary" if cid == active_id else "secondary",
        ):
            if cid != active_id:
                _switch_chat(cid)
                st.rerun()

    st.markdown("---")
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
        "a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "do",
        "we", "i", "my", "is", "are", "how", "many", "much", "what", "when",
        "where", "who", "with", "from", "this", "that", "have", "has", "get",
        "got", "can", "you", "your", "our", "me", "please", "about", "does", "did",
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
    conv = _active_conversation()
    if not conv["messages"]:
        conv["title"] = _title_from_message(q)
    conv["messages"].append({"role": "user", "content": q})
    conv["updated_at"] = time.time()
    block = _limits_block()
    if block:
        conv["messages"].append(
            {
                "role": "assistant",
                "content": block,
                "sources": [],
                "system_note": True,
            }
        )


def _generate_assistant_reply() -> None:
    messages = _active_messages()
    if not messages or messages[-1]["role"] != "user":
        return

    q = messages[-1]["content"]
    prior = messages[:-1]
    response = chat_query(engine, q, prior)
    answer = response.response or ""
    snippet_q = condensed_question_from_response(response) or q
    sources = _source_payload(response, question=snippet_q, answer=answer)
    conv = _active_conversation()
    conv["messages"].append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
    conv["updated_at"] = time.time()
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


# ---------- Main thread ----------
messages = _active_messages()

if not messages:
    _render_empty_state()
else:
    for turn in messages:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn["role"] == "assistant" and "sources" in turn:
                _render_sources(turn.get("sources") or [])

if st.session_state.pending_question:
    _queue_user_message(st.session_state.pending_question)
    st.session_state.pending_question = None
    st.rerun()

if messages and messages[-1]["role"] == "user":
    with st.spinner("Finding sources and drafting an answer…"):
        try:
            _generate_assistant_reply()
        except Exception as exc:  # noqa: BLE001
            conv = _active_conversation()
            conv["messages"].append(
                {
                    "role": "assistant",
                    "content": f"Sorry, I could not answer that: {exc}",
                    "sources": [],
                    "system_note": True,
                }
            )
            conv["updated_at"] = time.time()
    st.rerun()

if prompt := st.chat_input(
    "Ask anything about leave, hybrid work, expenses…"
):
    _queue_user_message(prompt)
    st.rerun()
