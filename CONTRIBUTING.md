# Contributing

This is a **portfolio demo** of an employee HR self-serve RAG assistant.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — set DEEPSEEK_API_KEY
python -m src.ingest
streamlit run app.py
```

## Quality gate

```bash
python -m src.eval
```

All golden cases should pass before opening a PR.

## Rules

- Do **not** commit `.env`, API keys, or real employer handbooks
- Keep the corpus **synthetic** (Acme HK demo pack) unless you have rights to share real policies
- Assistant must **inform**, not execute HR workflows
- This repo is **employee self-serve only** — implementation-consultant multi-SaaS code belongs elsewhere
