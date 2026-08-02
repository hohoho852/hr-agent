# Release checklist

Use when cutting a public release of this repo.

## Remote

```bash
cd ~/Projects/hr-agent
git remote -v   # origin → https://github.com/hohoho852/hr-agent.git
git status
git push origin main
```

## Repo settings

- Description: `Employee policy + HR how-to assistant with citations`
- Topics: `rag`, `hr`, `streamlit`, `llamaindex`, `deepseek`
- About → points at README

## Never push

- `.env`
- `chroma_db/` (rebuild with ingest)
- `.venv/`
- Real employer policies or PII without rights

## Optional

Screenshots under `docs/screenshots/` linked from the README.
