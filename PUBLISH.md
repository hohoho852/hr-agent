# Publish checklist (GitHub)

Local prep is done when `git log` shows the initial commit and `git status` is clean.

## When your new GitHub account exists

1. Repo is published: **https://github.com/hohoho852/hr-agent** (public).
2. Local path matches:

```bash
cd ~/Projects/hr-agent
git remote -v   # origin → https://github.com/hohoho852/hr-agent.git
git push -u origin main
```

3. GitHub repo settings (recommended for portfolio):
   - Description: `HR Agent — employee policy + how-to RAG with citations (Tier-1 deflection)`
   - Topics: `rag`, `hr`, `streamlit`, `llamaindex`, `portfolio`, `deepseek`
   - About → link case study path in README

## Never push

- `.env` (gitignored)
- `chroma_db/` (rebuilt by ingest)
- `.venv/`
- Real employer policy PDFs or PII

## After first push

Optional: add screenshots under `docs/screenshots/` and link them from README.
