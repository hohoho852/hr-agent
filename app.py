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
    /* Chat bubbles via column layout (reliable vs fragile :has() avatar CSS) */
    .hr-bubble {
        border-radius: 1.15rem;
        padding: 0.7rem 1rem;
        line-height: 1.5;
        word-wrap: break-word;
    }
    .hr-bubble p { margin-bottom: 0.4rem; }
    .hr-bubble p:last-child { margin-bottom: 0; }
    .hr-bubble-user {
        background: #2563eb;
        color: #ffffff;
    }
    .hr-bubble-user p, .hr-bubble-user li, .hr-bubble-user span {
        color: #ffffff !important;
    }
    .hr-bubble-assistant {
        background: #f3f4f6;
        border: 1px solid #e5e7eb;
        color: #111827;
    }
    .hr-msg-row {
        margin: 0.35rem 0 0.85rem;
    }
    [data-testid="stChatInput"] textarea {
        border: 1px solid #e5e7eb !important;
    }
    [data-testid="stChatInput"]:focus-within textarea {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 1px #2563eb !important;
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


def _conversation_has_messages(conv: dict) -> bool:
    return bool(conv.get("messages"))


def _start_new_chat() -> bool:
    """Start a fresh chat. No-op if the active chat is already empty."""
    if not _conversation_has_messages(_active_conversation()):
        return False
    cid = _new_conversation_id()
    st.session_state.conversations[cid] = _empty_conversation()
    st.session_state.active_conversation_id = cid
    return True


def _switch_chat(conversation_id: str) -> None:
    if conversation_id in st.session_state.conversations:
        st.session_state.active_conversation_id = conversation_id


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f'<p class="sidebar-brand">{PRODUCT_NAME}</p>', unsafe_allow_html=True)
    if st.button("New chat", use_container_width=True, type="primary"):
        if _start_new_chat():
            st.rerun()

    st.markdown("---")
    st.caption("Conversation")
    active_id = st.session_state.active_conversation_id
    sorted_chats = sorted(
        (
            (cid, conv)
            for cid, conv in st.session_state.conversations.items()
            if _conversation_has_messages(conv)
        ),
        key=lambda item: item[1]["updated_at"],
        reverse=True,
    )
    for cid, conv in sorted_chats:
        label = conv["title"] or "Chat"
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


def _md_to_html(content: str) -> str:
    """Lightweight markdown → HTML for bubble bodies (bold/italic/code/breaks)."""
    import html
    import re

    text = content or ""
    # Escape first, then re-apply a few markdown patterns.
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # Numbered / bullet lines stay readable with <br>
    text = text.replace("\n", "<br>")
    return text


def _render_user_bubble(content: str) -> None:
    """User message aligned right (ChatGPT / Grok pattern)."""
    body = _md_to_html(content)
    left, right = st.columns([1, 2], gap="small")
    with right:
        st.markdown(
            f'''<div class="hr-msg-row"><div class="hr-bubble hr-bubble-user">{body}</div></div>''',
            unsafe_allow_html=True,
        )


def _render_assistant_bubble(content: str, sources: list | None = None) -> None:
    """Assistant message aligned left with optional sources."""
    body = _md_to_html(content)
    left, right = st.columns([2, 1], gap="small")
    with left:
        st.markdown(
            f'''<div class="hr-msg-row"><div class="hr-bubble hr-bubble-assistant">{body}</div></div>''',
            unsafe_allow_html=True,
        )
        if sources is not None:
            _render_sources(sources)


def _send_user_message(question: str) -> None:
    """Append user turn, render optimistically, then assistant reply in one run."""
    q = (question or "").strip()
    if not q:
        return

    conv = _active_conversation()
    if not conv["messages"]:
        conv["title"] = _title_from_message(q)
    conv["messages"].append({"role": "user", "content": q})
    conv["updated_at"] = time.time()

    _render_user_bubble(q)

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
        _render_assistant_bubble(block, sources=[])
        return

    answer = ""
    sources: list[dict] = []
    system_note = False

    with st.spinner("Finding sources and drafting an answer…"):
        try:
            prior = conv["messages"][:-1]
            response = chat_query(engine, q, prior)
            answer = response.response or ""
            snippet_q = condensed_question_from_response(response) or q
            sources = _source_payload(response, question=snippet_q, answer=answer)
        except Exception as exc:  # noqa: BLE001
            answer = f"Sorry, I could not answer that: {exc}"
            sources = []
            system_note = True

    _render_assistant_bubble(answer, sources=sources if sources else [])

    conv["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            **({"system_note": True} if system_note else {}),
        }
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
                st.session_state.chip_question = q
                st.rerun()


# ---------- Main thread ----------
messages = _active_messages()
chip_question = st.session_state.pop("chip_question", None)
prompt = st.chat_input("Ask anything about leave, hybrid work, expenses…")
incoming = chip_question or prompt

for turn in messages:
    if turn["role"] == "user":
        _render_user_bubble(turn["content"])
    else:
        src = turn.get("sources") if "sources" in turn else None
        _render_assistant_bubble(turn["content"], sources=src)

if not messages and incoming is None:
    _render_empty_state()

if incoming:
    _send_user_message(incoming)
    st.rerun()
