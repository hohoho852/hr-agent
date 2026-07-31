# HR Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**HR Agent** — employee policy + how-to assistant (RAG). Portfolio project: a **production-style HR knowledge assistant** that answers:

1. **Company policy** questions (leave, hybrid work, expenses, privacy)
2. **How to perform standard HR actions** in the HRIS (request time off, update profile, submit expenses)

**Goal:** deflect Tier-1 tickets and relieve People Ops of repetitive answers — with **citations** on every response.

> **Scope:** employee self-serve only.  
> Multi-SaaS implementation copilot (SuccessFactors / Oracle Fusion / Workday) is a **separate product**, not in this repo.

---

## Why this exists

| | |
|---|---|
| **Problem** | HR answers the same policy and “how do I…?” questions all day |
| **Users** | Employees |
| **Buyer signal** | CHRO / People Ops (ticket deflection, answer consistency) |
| **Why RAG** | Policies change; answers must be source-linked |
| **Hard rule** | **Inform ≠ execute** — no submitting leave/pay/workflows; exceptions → HR ticket |

Full narrative: [`docs/CASE_STUDY.md`](docs/CASE_STUDY.md)

---

## Demo (30 seconds)

```text
You:  How do I request annual leave in SuccessFactors?
Bot:  Open Time Off → Request Time Off → choose Annual Leave → dates → Submit…
      + source citations from the leave how-to + policy pack
```

Other good prompts:

- How many annual leave days do full-time employees get?
- When do I need a medical certificate for sick leave?
- How do I update my home address?
- What is the default hybrid work pattern?
- How do I submit an expense claim?
- When should I contact HR instead of self-serve?

---

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | DeepSeek (`deepseek-chat`) | Strong quality/cost for generation |
| Embeddings | Local `BAAI/bge-small-en-v1.5` | Keeps handbook text on-machine |
| Vector store | Chroma | Simple persistent local index |
| Orchestration | LlamaIndex | Clean ingest/query path |
| UI | Streamlit | Fast portfolio demo with source expanders |

---

## Quickstart

**Requirements:** Python 3.10+, a [DeepSeek API key](https://platform.deepseek.com/)

```bash
git clone https://github.com/hohoho852/hr-agent.git
cd hr-agent

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set DEEPSEEK_API_KEY=...

python -m src.ingest               # build local vector index from data/
python -m src.query --question "How do I request annual leave?"
streamlit run app.py               # open the local URL Streamlit prints
python -m src.eval                 # quality gate
```

First ingest downloads the local embedding model (one-time).

---

## Project layout

```text
hr-agent/
├── app.py                      # Streamlit UI
├── data/                       # synthetic Acme HK policy + how-to pack
├── docs/CASE_STUDY.md          # portfolio narrative
├── eval/
│   ├── golden_questions.json   # regression cases
│   └── last_report.json        # last local eval run (optional to commit)
├── src/
│   ├── config.py
│   ├── ingest.py
│   ├── query.py
│   └── eval.py
├── .env.example
├── LICENSE                     # MIT
├── PUBLISH.md                  # push steps after GitHub account exists
└── README.md
```

---

## Demo corpus

Synthetic **Acme HK** handbook pack (portfolio-safe — **not** a real employer policy):

| File | Content |
|------|---------|
| `01_employee_handbook_overview.md` | Purpose, channels, principles |
| `02_leave_and_time_off_policy.md` | AL/SL rules, carry-over, notice |
| `03_how_to_request_time_off.md` | SuccessFactors Time Off steps |
| `04_personal_data_and_profile_policy.md` | What employees may change |
| `05_how_to_update_personal_info.md` | Address / emergency / bank steps |
| `06_hybrid_work_and_attendance_policy.md` | 3/2 hybrid default |
| `07_how_to_submit_expense_claim.md` | Expense steps + receipt threshold |
| `08_hr_contact_and_escalation.md` | Self-serve vs HR ticket |

---

## Evaluation

```bash
python -m src.eval
```

| Metric | Meaning |
|--------|---------|
| Retrieval hit-rate | Expected source file appears in top sources |
| Keyword coverage | Answer contains domain anchor phrases |
| Latency | End-to-end query time |

Baseline on this pack: **7/7 pass** (local run). Report: `eval/last_report.json`.

---

## Enterprise controls (honest v1)

- Local embeddings; only retrieved snippets + question go to the LLM
- Citations always shown in the UI
- No workflow execution; no invented personal leave balances
- Escalation copy for exceptions, payroll, grievances
- `.env` gitignored — **never commit API keys**

Production follow-ons (not in this demo): SSO, DLP/redaction, private LLM endpoint, deflection analytics.

---

## What this is / isn’t

| This repo | Not this repo |
|-----------|----------------|
| Employee policy + HR how-to RAG | Multi-vendor impl copilot |
| GitHub portfolio proof | Production multi-tenant SaaS |
| Synthetic handbook | Real customer PII / policies |

---

## License

MIT — see [LICENSE](LICENSE).

Demo policy text is synthetic for illustration only and is not legal or HR advice.
