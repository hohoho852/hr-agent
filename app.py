"""Streamlit UI — HR Agent."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PRODUCT_NAME, PRODUCT_TAGLINE
from src.query import get_query_engine, index_needs_build

st.set_page_config(page_title=PRODUCT_NAME, page_icon="📋", layout="centered")

st.title(PRODUCT_NAME)
st.caption(PRODUCT_TAGLINE)
st.write(
    "Ask **company policy** questions and **how to complete standard HR actions** "
    "(leave, profile, expenses). Every answer includes **citations** from the handbook pack."
)

with st.sidebar:
    st.header("About")
    st.markdown(
        """
**Users:** Employees  
**Operators:** People Ops / HRIS  

**Job:** Policy Q&A + how-to for standard HR actions  

**Not this product:** multi-vendor implementation guidance  
(see `hcm-impl-copilot`)

**Controls**
- Citations always on
- Local embeddings (BGE)
- Generation only on retrieved snippets (DeepSeek)
- Informs only — does not submit workflows

**Stack**
- LLM: DeepSeek
- Embeddings: local `BAAI/bge-small-en-v1.5`
- Vector store: Chroma
- Orchestration: LlamaIndex
"""
    )
    st.divider()
    st.markdown("**Try asking**")
    st.markdown(
        """
- How many annual leave days do I get?
- How do I request time off in SuccessFactors?
- How do I update my home address?
- Can I work from overseas?
- How do I submit an expense claim?
- When should I contact HR instead of self-serve?
"""
    )
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

st.info(
    "Human-in-the-loop: policy guidance only. Does not submit leave, change pay, "
    "or grant exceptions — escalate those to HR.",
    icon="⚠️",
)

query = st.text_input(
    "Your question:",
    placeholder="e.g. How do I request annual leave in SuccessFactors?",
)
ask = st.button("Ask", type="primary")

if ask and query.strip():
    with st.spinner("Retrieving sources and generating answer..."):
        try:
            response = engine.query(query.strip())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Query failed: {exc}")
            st.stop()

    st.subheader("Answer")
    st.write(response.response)

    with st.expander("Sources (verify before acting)", expanded=True):
        if not response.source_nodes:
            st.write("No sources returned — do not act on an ungrounded answer.")
        for i, node in enumerate(response.source_nodes, 1):
            meta = node.metadata or {}
            fname = meta.get("file_name") or meta.get("filename") or "Unknown"
            score = node.score if node.score is not None else 0.0
            st.markdown(f"**Source {i}** — `{fname}` (score: {score:.3f})")
            content = node.node.get_content()
            st.write((content[:500] + "...") if len(content) > 500 else content)
            st.divider()
elif ask:
    st.warning("Enter a question first.")
