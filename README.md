# HR Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Employee-facing assistant for **company policy** and **standard HR how-tos**.

Answers common questions (leave, hybrid work, expenses, profile updates) with **citations** from the employer handbook pack. Built so People Ops can deflect repetitive Tier-1 volume without the bot approving leave, changing pay, or handling exceptions.

**Live demo:** [hr-agent-hohoho852.streamlit.app](https://hr-agent-hohoho852.streamlit.app/)

---

## What it does

| | |
|---|---|
| **Problem** | The same policy and “how do I…?” questions hit HR every day |
| **Users** | Employees |
| **Operators** | People Ops / HRIS |
| **Behavior** | Retrieve handbook + how-to sources → answer with citations |
| **Hard rule** | **Inform ≠ execute** — no workflow submission; exceptions go to HR |

Design notes: [`docs/PRODUCT.md`](docs/PRODUCT.md)

---

## Example

```text
You:  How do I request annual leave?
Bot:  Open Time Off → Request Time Off → choose Annual Leave → dates → Submit…
      + source citations from the leave how-to and policy pack
```

Other prompts that work well:

- How many annual leave days do full-time employees get?
- When do I need a medical certificate for sick leave?
- How do I update my home address?
- What is the default hybrid work pattern?
- How do I submit an expense claim?
- When should I contact HR instead of self-serve?

---

## Source documents (what clients typically provide)

Real deployments start from **existing employer documents** — handbooks, leave policies, HRIS how-tos — usually PDF or Word from People Ops.

This repo includes a **sample client pack** under [`source/`](source/):

| File | Role |
|------|------|
| `Demo_HK_Employee_Handbook_Overview.pdf` | Handbook overview / channels |
| `Demo_HK_Leave_and_Time_Off_Policy.pdf` | Leave entitlements & rules |
| `Demo_HK_Time_Off_Employee_Guide.pdf` | Time Off request steps (generic HR system) |
| `Demo_HK_Personal_Data_and_Profile_Policy.pdf` | What employees may change |
| `Demo_HK_Hybrid_Work_Policy.pdf` | Hybrid / attendance default |
| `Demo_HK_Expense_Claim_Guide.pdf` | Expense claim steps |
| `Demo_HK_HR_Contact_and_Escalation.pdf` | Self-serve vs HR ticket |

**Demo Hong Kong Limited is fictional** — sample content for demo only, not a real employer and not legal/HR advice. How-tos use a generic company HR system / People Portal (not a named vendor).

Runtime indexing uses the machine-readable pack in [`data/`](data/) (same policies as markdown for reliable local builds). For a production tenant, replace both with **your licensed** PDFs/DOCX/MD and run ingest.

---

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Generation | **Your** OpenAI-compatible chat model | Customer brings model + key (OpenAI, Azure OpenAI, DeepSeek, gateway, vLLM, …) |
| Embeddings | Local `BAAI/bge-small-en-v1.5` | Handbook text stays on-machine |
| Vector store | Chroma | Persistent local index |
| Orchestration | LlamaIndex | Ingest / retrieve / query path |
| UI | Streamlit | Multi-turn chat with citations per reply |

Company deploy (private + SSO): IT picks **Path A** (cloud-neutral) or **Path B** (Azure/M365) — same product. See [`docs/DEPLOY-A-vs-B.md`](docs/DEPLOY-A-vs-B.md), step-by-step [`docs/DEPLOY-GUIDE.md`](docs/DEPLOY-GUIDE.md), and diagrams under [`docs/diagrams/`](docs/diagrams/).

---

## Quickstart

**Requirements:** Python 3.10+, an API key for **any OpenAI-compatible** chat endpoint

```bash
git clone https://github.com/hohoho852/hr-agent.git
cd hr-agent

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# set LLM_API_KEY=...   optional: LLM_MODEL, LLM_API_BASE

python -m src.ingest               # build local vector index from data/
python -m src.query --question "How do I request annual leave?"
streamlit run app.py               # chat UI — follow-ups supported in-session
python -m src.eval                 # regression suite
```

First ingest downloads the local embedding model (one-time).

### Model configuration

| Variable | Required | Purpose |
|----------|----------|--------|
| `LLM_API_KEY` | yes* | Customer key (`OPENAI_API_KEY` alias OK) |
| `LLM_MODEL` | no | Model / deployment name |
| `LLM_API_BASE` | no | OpenAI-compatible base URL |

\*Legacy `DEEPSEEK_API_KEY` alone still works for existing demos (implies DeepSeek base + `deepseek-v4-flash`).

---

## Deploy on Streamlit Community Cloud

No Docker required. Point Streamlit at this repo with **Main file:** `app.py`.

**Public demo:** open so visitors can try the product from the README. The API key stays in Streamlit Secrets (never in the repo or browser). Protect spend with a **demo-only key**, provider billing alerts, and app session limits (10 questions per browser session, 5s cooldown — override via `DEMO_SESSION_LIMIT`, `DEMO_COOLDOWN_SEC`, or set `DEMO_LIMITS=0` to disable).

**Secrets (TOML):**

```toml
LLM_API_KEY = "your_key_here"
LLM_MODEL = "deepseek-v4-flash"
LLM_API_BASE = "https://api.deepseek.com/v1"
```

Or any other OpenAI-compatible provider — set `LLM_MODEL` / `LLM_API_BASE` to match. Legacy `DEEPSEEK_API_KEY` alone is still accepted.

**First boot:** the app downloads the local BGE embedding model and builds the Chroma index from `data/` automatically (several minutes on a cold container). The vector store is not committed — each new container rebuilds on first start.

**Requirements:** Python 3.10+ (set in Streamlit app settings if needed). Dependencies are in `requirements.txt`.

---

## Layout

```text
hr-agent/
├── app.py                 # Streamlit UI
├── source/                # Client-style sample PDFs (audience-facing inputs)
├── data/                  # Runtime corpus (markdown; same sample policies)
├── docs/
│   ├── PRODUCT.md
│   ├── OPS.md                 # ops / logging / eval gate
│   ├── DEPLOY-A-vs-B.md       # IT decision one-pager
│   ├── DEPLOY-GUIDE.md        # Path A/B step-by-step
│   └── diagrams/              # demo + production architecture HTML
├── eval/
│   ├── golden_questions.json
│   └── last_report.json
├── src/
│   ├── config.py
│   ├── cost.py
│   ├── ingest.py
│   ├── query.py
│   ├── query_log.py
│   ├── eval.py
│   └── ops_report.py
├── .env.example
├── LICENSE                # MIT
└── README.md
```

---

## Sample corpus (`data/`)

Indexed content for local/demo runs (mirrors the PDF pack in `source/`):

| File | Content |
|------|---------|
| `01_employee_handbook_overview.md` | Purpose, channels, principles |
| `02_leave_and_time_off_policy.md` | AL/SL rules, carry-over, notice |
| `03_how_to_request_time_off.md` | Time Off request steps (generic HR system) |
| `04_personal_data_and_profile_policy.md` | What employees may change |
| `05_how_to_update_personal_info.md` | Address / emergency / bank steps |
| `06_hybrid_work_and_attendance_policy.md` | 3/2 hybrid default |
| `07_how_to_submit_expense_claim.md` | Expense steps + receipt threshold |
| `08_hr_contact_and_escalation.md` | Self-serve vs HR ticket |

Replace `data/` (and preferably `source/`) with your own licensed policies for a real deployment.

**Public demo limits:** the live Streamlit app caps questions per browser session (default 10) with a short cooldown to control API spend. Set `DEMO_LIMITS=0` locally to disable. Override with `DEMO_SESSION_LIMIT` / `DEMO_COOLDOWN_SEC`.

---

## Evaluation

```bash
python -m src.eval
```

| Check | Meaning |
|-------|---------|
| Retrieval hit | Expected source file appears in top sources |
| Keyword coverage | Answer contains domain anchor phrases |
| Latency | End-to-end query time |

On the sample pack: **7/7** pass. Report: `eval/last_report.json` (latency + cost rollups).

---

## Operations

Live demo, secrets, demo limits, eval gate, request logging, and cost env vars: **[`docs/OPS.md`](docs/OPS.md)**.

```bash
python -m src.eval        # regression gate (7/7 on sample pack)
python -m src.ops_report  # summarize runs/query_events.jsonl
```

**Live demo:** [hr-agent-hohoho852.streamlit.app](https://hr-agent-hohoho852.streamlit.app/)

**Architecture (HTML, open in browser):**
- Demo (Streamlit Cloud): [`docs/diagrams/demo-streamlit-architecture.html`](docs/diagrams/demo-streamlit-architecture.html)
- Production Path A/B: [`docs/diagrams/production-deploy-architecture.html`](docs/diagrams/production-deploy-architecture.html)

**Private deploy:** [`docs/DEPLOY-GUIDE.md`](docs/DEPLOY-GUIDE.md) (steps) · [`docs/DEPLOY-A-vs-B.md`](docs/DEPLOY-A-vs-B.md) (choose path)

---

## Operating controls

- Local embeddings; only retrieved snippets + question go to the LLM
- Citations always shown in the UI
- No workflow execution; no invented personal leave balances
- Escalation copy for exceptions, payroll, grievances
- Public demo: session limits count **attempted model calls** (default 10/session, 5s cooldown)
- `.env` is gitignored — never commit API keys

For a live tenant deploy, add SSO, DLP/redaction, customer-owned model endpoint/key, and deflection analytics as needed. IT deploy choice: [`docs/DEPLOY-A-vs-B.md`](docs/DEPLOY-A-vs-B.md); full steps: [`docs/DEPLOY-GUIDE.md`](docs/DEPLOY-GUIDE.md).

---

## License

MIT — see [LICENSE](LICENSE).

Sample policy text is for illustration only and is not legal or HR advice.
