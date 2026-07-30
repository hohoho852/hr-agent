# Publish checklist (GitHub)

Local prep is done when `git log` shows the initial commit and `git status` is clean.

## When your new GitHub account exists

1. Create a **public** empty repo named `hr-employee-selfserve` (no README/license — already in this repo).
2. From this folder:

```bash
cd ~/Projects/hr-employee-selfserve
git remote add origin git@github.com:<YOUR_NEW_USERNAME>/hr-employee-selfserve.git
# or HTTPS:
# git remote add origin https://github.com/<YOUR_NEW_USERNAME>/hr-employee-selfserve.git

git branch -M main
git push -u origin main
```

3. GitHub repo settings (recommended for portfolio):
   - Description: `Employee HR self-serve RAG — policy + how-to answers with citations (Tier-1 deflection)`
   - Topics: `rag`, `hr`, `streamlit`, `llamaindex`, `portfolio`, `deepseek`
   - About → link case study path in README

## Never push

- `.env` (gitignored)
- `chroma_db/` (rebuilt by ingest)
- `.venv/`
- Real employer policy PDFs or PII

## After first push

Optional: add screenshots under `docs/screenshots/` and link them from README.
