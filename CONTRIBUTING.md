# Contributing

HR Agent — employee policy + how-to assistant.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# set DEEPSEEK_API_KEY
python -m src.ingest
streamlit run app.py
```

## Quality gate

```bash
python -m src.eval
```

All cases in `eval/golden_questions.json` should pass before opening a PR.

## Rules

- Do **not** commit `.env`, API keys, or real employer handbooks without rights  
- Keep the default corpus as the sample Acme HK pack unless you own the content  
- Assistant must **inform**, not execute HR workflows  
- This repo is **employee self-serve only** — multi-vendor implementation code belongs in `hcm-impl-copilot`
