# HR Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Employee-facing assistant for **company policy** and **standard HR how-tos**.

Answers common questions (leave, hybrid work, expenses, profile updates) with **citations** from the handbook pack. Designed so People Ops can deflect repetitive Tier-1 volume without the bot approving leave, changing pay, or handling exceptions.

**Scope:** employee self-serve only.  
Implementation guidance for SuccessFactors / Oracle Fusion / Workday lives in a separate product: [`hcm-impl-copilot`](https://github.com/hohoho852/hcm-impl-copilot) (when published).

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
You:  How do I request annual leave in SuccessFactors?
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

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Generation | DeepSeek (`deepseek-chat`) | Cost-efficient generation on retrieved snippets |
| Embeddings | Local `BAAI/bge-small-en-v1.5` | Handbook text stays on-machine |
| Vector store | Chroma | Persistent local index |
| Orchestration | LlamaIndex | Ingest / retrieve / query path |
| UI | Streamlit | Lightweight operator UI |

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
# set DEEPSEEK_API_KEY=...

python -m src.ingest               # build local vector index from data/
python -m src.query --question "How do I request annual leave?"
streamlit run app.py
python -m src.eval                 # regression suite
```

First ingest downloads the local embedding model (one-time).

---

## Deploy on Streamlit Community Cloud

No Docker required. Point Streamlit at this repo with **Main file:** `app.py`.

**Public demo:** this deployment is open so visitors can try the product from the README. The API key stays in Streamlit Secrets (never in the repo or browser). Protect spend with a **demo-only key**, provider billing alerts, and app session limits (10 questions per browser session, 5s cooldown — override via `DEMO_SESSION_LIMIT`, `DEMO_COOLDOWN_SEC`, or set `DEMO_LIMITS=0` to disable).

**Secrets (TOML):**

```toml
DEEPSEEK_API_KEY = "your_deepseek_key_here"
```

**First boot:** the app downloads the local BGE embedding model and builds the Chroma index from `data/` automatically (several minutes on a cold container). The vector store is not committed — each new container rebuilds on first start.

**Requirements:** Python 3.10+ (set in Streamlit app settings if needed). Dependencies are in `requirements.txt`.

---

## Layout

```text
hr-agent/
├── app.py                 # Streamlit UI
├── data/                  # Acme HK sample policy + how-to pack
├── docs/PRODUCT.md        # product design
├── eval/
│   ├── golden_questions.json
│   └── last_report.json
├── src/
│   ├── config.py
│   ├── ingest.py
│   ├── query.py
│   └── eval.py
├── .env.example
├── LICENSE                # MIT
└── README.md
```

---

## Sample corpus

Bundled **Acme Hong Kong** pack — a **fictional** sample employer for local/demo runs. **Not a real company** and **not** a real employer handbook:

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

Replace `data/` with your own licensed policies for a real deployment.

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

On the sample pack: **7/7** pass. Report: `eval/last_report.json`.

---

## Operating controls

- Local embeddings; only retrieved snippets + question go to the LLM
- Citations always shown in the UI
- No workflow execution; no invented personal leave balances
- Escalation copy for exceptions, payroll, grievances
- Public demo: session limits count **attempted model calls** (default 10/session, 5s cooldown)
- `.env` is gitignored — never commit API keys

For a live tenant deploy, add SSO, DLP/redaction, private model endpoint, and deflection analytics as needed.

---

## Related

| Product | Repo | Audience |
|---------|------|----------|
| **HR Agent** (this repo) | `hr-agent` | Employees — policy + how-to |
| **HCM Implementation Copilot** | `hcm-impl-copilot` | Consultants — multi-vendor impl guidance |

Codebases are separate on purpose.

---

## License

MIT — see [LICENSE](LICENSE).

Sample policy text is for illustration only and is not legal or HR advice.
