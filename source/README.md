# Source documents — sample client pack

This folder holds **client-style inputs**: the kind of PDF/Word handbooks and how-tos People Ops already has before an HR Agent project starts.

| Document | Typical owner |
|----------|----------------|
| Employee handbook overview | People Ops |
| Leave and time-off policy | People Ops / Legal |
| Time Off employee guide | HRIS |
| Personal data & profile policy | People Ops / Privacy |
| Hybrid work policy | People Ops |
| Expense claim guide | Finance + People Ops |
| HR contact & escalation | People Ops / HRBP |

**Demo note:** files are labeled **Demo Hong Kong Limited** — a **fictional** sample employer. Not a real company. Not legal or HR advice. How-tos refer to a generic company HR system / People Portal (not a named vendor product).

## How this relates to `data/`

| Folder | Audience | Format | Used by |
|--------|----------|--------|---------|
| **`source/`** | Humans evaluating the product | PDF (client look-and-feel) | README / demos — “what you provide” |
| **`data/`** | The running agent | Markdown (same policies) | `python -m src.ingest` / Streamlit index |

For a real tenant:

1. Collect licensed PDFs/DOCX from the client into `source/` (or your secure doc store).  
2. Place extractable text (PDF/DOCX/MD/TXT) into `data/` (or point ingest at that store).  
3. Run `python -m src.ingest` and re-run `python -m src.eval`.

Ingest already accepts `.pdf`, `.docx`, `.txt`, and `.md` under `data/`.
