# HR Agent — Operations

Production-readiness notes for the **public Streamlit demo** and local ops. This is not a private tenant deploy (no SSO, no Path A/B packaging). For real company hosting, see [`DEPLOY-A-vs-B.md`](DEPLOY-A-vs-B.md).

**Live demo:** https://hr-agent-hohoho852.streamlit.app/

**Architecture diagram:** [`diagrams/deployed-system-architecture.html`](diagrams/deployed-system-architecture.html)

---

## Secrets

Never commit API keys or Streamlit secrets to git.

| Surface | Where |
|---------|--------|
| Local dev | `.env` (gitignored) — copy from `.env.example` |
| Streamlit Community Cloud | App **Secrets** (TOML) in the Streamlit dashboard |

Required for generation:

```toml
LLM_API_KEY = "your_key_here"
LLM_MODEL = "deepseek-v4-flash"          # optional
LLM_API_BASE = "https://api.deepseek.com/v1"  # optional
```

Aliases accepted: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_API_BASE`. Legacy `DEEPSEEK_API_KEY` alone still works for existing demos.

Embeddings run locally (`BAAI/bge-small-en-v1.5`); only retrieved handbook snippets and the employee question are sent to the LLM.

---

## Demo limits

The public demo caps spend and abuse via session guards (configured in `src/config.py`):

| Variable | Default | Effect |
|----------|---------|--------|
| `DEMO_LIMITS` | `1` | Set `0` / `false` to disable all limits |
| `DEMO_SESSION_LIMIT` | `10` | Max model calls per browser session |
| `DEMO_COOLDOWN_SEC` | `5` | Minimum seconds between questions |

Limits apply to **attempted model calls**, not page views. Clone and run locally with your own key for unlimited use.

---

## Eval gate

Regression suite on the bundled sample handbook:

```bash
source .venv/bin/activate   # if using a venv
python -m src.eval
```

Pass criteria (unchanged): keyword + retrieval hits on all cases in `eval/golden_questions.json` (**7/7** on the sample pack).

Report written to `eval/last_report.json`, including:

- `pass_rate`, `avg_latency_s`, `p95_latency_s`
- `total_est_cost_usd`, `avg_est_cost_usd`
- Per-case `prompt_tokens`, `completion_tokens`, `est_cost_usd`, `usage_source`

Exit code `0` only when `pass_rate == 1.0`.

---

## Request logging (`runs/query_events.jsonl`)

Every chat or CLI query that hits the LLM appends one JSON line (success **or** failure). Logging is **fail-open** — I/O errors never block an answer.

Default path: `runs/query_events.jsonl` (gitignored).

| Field | Meaning |
|-------|---------|
| `ts` | UTC ISO timestamp |
| `latency_ms` | End-to-end request time |
| `model` | Configured LLM model id |
| `prompt_tokens` | Prompt/input tokens |
| `completion_tokens` | Completion/output tokens |
| `est_cost_usd` | Estimated USD (see cost env vars) |
| `usage_source` | `provider` — token counts from API/LlamaIndex response; `estimate` — heuristic when provider omits usage |
| `ok` | `true` if the query completed without exception |
| `error_type` | Exception class name when `ok` is false |
| `n_sources` | Number of retrieved source nodes |
| `question_len` | Character length of the question (no full question text logged) |

Full question text, full answers, and handbook chunks are **not** logged by default.

Quick summary of recent events:

```bash
python -m src.ops_report          # last 50 events
python -m src.ops_report -n 200
```

---

## Cost environment variables

USD rates are **estimates** for ops visibility, not provider invoices. Override per 1M tokens:

| Variable | Default (DeepSeek-ish) | Applies to |
|----------|------------------------|------------|
| `LLM_COST_USD_PER_1M_PROMPT` | `0.14` | Prompt / input tokens |
| `LLM_COST_USD_PER_1M_COMPLETION` | `0.28` | Completion / output tokens |

Implementation: `src/cost.py` → `estimate_cost(prompt_tokens, completion_tokens, model?)`.

When the OpenAI-compatible API returns usage metadata, `usage_source` is `provider`. Otherwise token counts and cost use a character-based heuristic (`usage_source: estimate`).

---

## Limitations (explicit)

| This repo (Community Cloud) | Private tenant (Path A / B) |
|-----------------------------|-----------------------------|
| Public Streamlit URL | SSO + private app URL |
| Shared demo handbook | Customer handbook in tenant storage |
| Session question limits | Per-tenant rate limits / audit |
| JSONL on local/container disk | Central log store + retention policy |
| Operator-managed API key in secrets | Customer-owned model endpoint + key |

Community Cloud proves the product loop (RAG + citations + eval + cost/latency visibility). It is **not** a substitute for Path A/B production deploy. See [`DEPLOY-A-vs-B.md`](DEPLOY-A-vs-B.md) for IT packaging (container, IdP, tenant index, audit).

---

## Local run checklist

```bash
python -m src.ingest                 # once, or auto on first app start
streamlit run app.py
python -m src.eval                   # before release / after prompt changes
python -m src.ops_report             # inspect live traffic locally
```

Stack: Streamlit (`app.py`), LlamaIndex query path (`src/query.py`), local Chroma + BGE embeddings, OpenAI-compatible LLM.
