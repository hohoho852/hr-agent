# HR Agent — Path A vs Path B (one-pager for IT)

**Product (same on both paths):** employee policy + HR how-to assistant with citations.  
**Inform ≠ execute.** SSO, private app, tenant handbook, audit log, eval gate.

**Audience:** companies under ~1,000 headcount choosing a production deploy shape.  
**Not this page:** public Streamlit demo (sales only).

---

## Decision in one glance

| | **Path A — Cloud-neutral** | **Path B — Microsoft-centric** |
|--|----------------------------|--------------------------------|
| **Choose when** | AWS/GCP/multi-cloud, Google Workspace, Okta, “ship a container” | M365 + Entra is the spine; SharePoint handbooks; want Teams later |
| **Default IdP** | Any OIDC (Okta, Google, Entra, Auth0…) | **Entra ID** first-class |
| **Primary cloud** | Customer choice (AWS / GCP / Azure) | **Azure** |
| **App host** | Container (ECS/EKS, Cloud Run, Container Apps, etc.) | Azure App Service or Container Apps |
| **Source files** | Object storage (S3/GCS/Blob) | Blob and/or **SharePoint** library |
| **Vector index** | Postgres + pgvector (or equiv.) | Same, or **Azure AI Search** if preferred |
| **LLM** | **Customer’s model + key** (OpenAI-compatible endpoint) | Same — often Azure OpenAI |
| **Front door later** | Web only (bot optional later) | Web + optional **Teams** bot |
| **Best for** | Flexibility, non-Microsoft estates | Lowest friction in Microsoft houses |

**Rule:** one product codebase; A/B is packaging + cloud glue, not different answer behavior.

```text
M365 + Entra as default workplace?  → Path B
Anything else / multi-cloud         → Path A
Tiny pilot, almost no cloud yet     → short Path C (VM) then move to A or B
```

---

## Same on both paths (non-negotiable)

| Control | Requirement |
|---------|-------------|
| Identity | Company SSO; no anonymous production access |
| Corpus | Employer-licensed handbook only (not public demo pack) |
| Model | Customer-supplied **LLM_API_KEY** + model id (+ optional API base) |
| Boundary | Cite sources; escalate exceptions; never submit HR workflows |
| Audit | Log user, time, question, answer, source ids, model |
| Quality | Golden-question eval before each corpus release |
| Secrets | Cloud secret store / Key Vault — never in git |

---

## What differs (services sketch)

| Concern | Path A (example) | Path B (example) |
|---------|------------------|------------------|
| Compute | Container service on chosen cloud | Azure Container Apps / App Service |
| Auth | OIDC proxy or app-native OIDC | Entra app registration + Easy Auth or MSAL |
| Handbook store | S3 / GCS / Blob | SharePoint site or Blob |
| DB / vectors | Managed Postgres + pgvector | Azure Database for PostgreSQL or AI Search |
| Secrets | AWS SM / GCP SM / Key Vault | Azure Key Vault |
| Observability | Cloud logs + metrics | Azure Monitor |
| Network | Private URL, VPN, or IP allowlist | Same + Private Link common |

---

## LLM flexibility (both paths)

Generation is **not** locked to one vendor.

| Setting | Purpose |
|---------|---------|
| `LLM_API_KEY` | Customer key (preferred) |
| `LLM_MODEL` | Model or deployment name |
| `LLM_API_BASE` | Optional OpenAI-compatible base URL |

Examples customers run: OpenAI, Azure OpenAI, DeepSeek, corporate LLM gateway, self-hosted vLLM.  
Embeddings can stay local-in-VPC (e.g. BGE) so handbook text need not leave the tenant for indexing.

---

## What the customer supplies

| Item | Path A | Path B |
|------|--------|--------|
| Cloud subscription | Yes (their account or agreed managed) | Azure subscription |
| SSO tenant | OIDC client + claims | Entra tenant + app consent |
| Handbook PDFs/DOCX | Licensed pack + owner | Same (± SharePoint library) |
| LLM key / endpoint | Their contract | Often Azure OpenAI deployment |
| People Ops owner | Corpus approve/publish | Same |
| IT owner | Network, secrets, uptime | Same (+ Entra admin) |

---

## What you deliver

- Same HR Agent app image / release  
- Deploy templates for **A** and **B**  
- Ingest + publish runbook, eval suite, audit field list  
- Pilot → company rollout support  

---

## Pilot shape (either path)

| | Pilot |
|--|--------|
| Users | 50–100 |
| Corpus | One entity handbook set |
| Auth | SSO on |
| Success | Deflection on Tier-1 Qs + citation trust + no policy incidents |
| Duration | ~4–8 weeks |

Then open to full <1k headcount.

---

## Commercial one-liner

> **Production HR Agent is private + SSO. Deploy Path A (cloud-neutral) or Path B (Azure/M365). Bring your own model key. Same product either way.**

---

## Out of scope on this page

- Public Streamlit Community Cloud as production  
- Multi-region active-active  
- Fine-tuned custom LLM requirement  
- Workflow execution inside HRIS  

See also: `docs/PRODUCT.md` (product design), repo README (demo quickstart).
