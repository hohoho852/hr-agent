# HR Agent — Production deploy guide (Path A & Path B)

Step-by-step packaging for a **private company** deployment.

**Product (same on both paths):** employee policy + HR how-to assistant with citations.  
**Inform ≠ execute** — answers and sources only; no HRIS write-back.

| Audience doc | Purpose |
|--------------|---------|
| This guide | Ordered install / cutover steps for IT + People Ops |
| [`DEPLOY-A-vs-B.md`](DEPLOY-A-vs-B.md) | One-page decision table |
| [`diagrams/production-deploy-architecture.html`](diagrams/production-deploy-architecture.html) | Production architecture diagram |
| [`diagrams/demo-streamlit-architecture.html`](diagrams/demo-streamlit-architecture.html) | Public Streamlit **demo** only |
| [`OPS.md`](OPS.md) | Demo ops (logging, eval, cost env) |

**Not this guide:** running the public Streamlit Community Cloud demo as production.

---

## 0. Choose a path (5 minutes)

```text
M365 + Entra is the default workplace?     → Path B
AWS / GCP / multi-cloud / Google / Okta?   → Path A
Almost no cloud, tiny pilot only?          → short VM pilot, then move to A or B
```

| | **Path A — Cloud-neutral** | **Path B — Microsoft-centric** |
|--|----------------------------|--------------------------------|
| IdP | Any OIDC (Okta, Google, Entra, Auth0…) | **Entra ID** first-class |
| Cloud | Customer choice (AWS / GCP / Azure) | **Azure** |
| App host | Container (ECS/EKS, Cloud Run, Container Apps, …) | Azure App Service or Container Apps |
| Handbook store | Object storage (S3 / GCS / Blob) | Blob and/or **SharePoint** |
| Vectors | Postgres + pgvector (or equiv.) | Same, or **Azure AI Search** |
| Secrets | Cloud secrets manager | **Azure Key Vault** |
| Later front door | Web (bot optional) | Web + optional **Teams** bot |

**Rule:** one product codebase. A/B is glue, not different answer logic.

---

## 1. Preconditions (both paths)

Complete before build day.

### 1.1 Owners

| Role | Owns |
|------|------|
| **IT** | Hosting, network, SSO app, secrets, uptime |
| **People Ops** | Licensed handbook pack, publish approval, golden questions |
| **Security** (if separate) | Data class, retention, DLP review |

### 1.2 Customer supplies

- [ ] Cloud subscription (Path A: any agreed cloud; Path B: Azure)
- [ ] SSO tenant + ability to register an app (OIDC or Entra)
- [ ] Employer-licensed handbook (PDF/DOCX or library) — **not** the public demo sample pack for production answers
- [ ] LLM contract: API key and/or Azure OpenAI (or other OpenAI-compatible) deployment
- [ ] Private DNS / URL plan (no anonymous public marketing URL as production)

### 1.3 Non-negotiable controls (definition of production)

| Control | Requirement |
|---------|-------------|
| Identity | Company SSO; no anonymous production access |
| Corpus | Employer-licensed handbook only |
| Model | Customer-supplied `LLM_API_KEY` + model (+ optional `LLM_API_BASE`) |
| Boundary | Cite sources; escalate exceptions; never submit HR workflows |
| Audit | Log user, time, question, answer, source ids, model |
| Quality | Golden-question eval **before each corpus release** |
| Secrets | Secret store / Key Vault — never in git |

### 1.4 Config surface (app)

| Variable | Purpose |
|----------|---------|
| `LLM_API_KEY` | Customer key (preferred) |
| `LLM_MODEL` | Model or Azure deployment name |
| `LLM_API_BASE` | Optional OpenAI-compatible base URL |
| Cost env (optional) | `LLM_COST_USD_PER_1M_PROMPT` / `…_COMPLETION` for ops estimates — see [`OPS.md`](OPS.md) |

Embeddings can stay **in-VPC** (e.g. local BGE) so full handbook text need not leave the tenant for indexing.

---

## 2. Shared build sequence (both paths)

Do these in order. Path-specific service names appear in §3 and §4.

### Step S1 — Freeze pilot scope

| Item | Pilot default |
|------|----------------|
| Users | 50–100 |
| Corpus | One legal entity / one handbook set |
| Auth | SSO **on** from day one of pilot |
| Success | Tier-1 deflection + citation trust + no policy incidents |
| Duration | ~4–8 weeks |

### Step S2 — Register identity application

1. Create OIDC app (Path A) or Entra app registration (Path B).
2. Set redirect URIs for the private app URL (HTTPS).
3. Restrict to company tenant / assigned groups (pilot security group first).
4. Record client id, issuer, and secret/certificate **into the secret store only**.

### Step S3 — Provision network + private entry

1. Create private app URL (internal DNS or reverse proxy).
2. Prefer private connectivity (VPN, private link, or IP allowlist). No open anonymous internet front door for production.
3. TLS certificate on the edge.

### Step S4 — Provision handbook storage

1. Create bucket/container or SharePoint library (Path B).
2. Permissions: ingest service identity **read**; People Ops **write/approve**.
3. Upload **licensed** pilot corpus only.

### Step S5 — Provision vector index + app data store

1. Managed Postgres + pgvector **or** Azure AI Search (Path B option).
2. One index/collection **per tenant** (no shared demo index).
3. Backup / retention per company policy.

### Step S6 — Provision secrets

Store at minimum:

- `LLM_API_KEY` (+ model / base if needed)
- OIDC/Entra client secret or cert
- DB / search connection strings
- Any storage credentials

Never commit secrets; never put production keys in Streamlit Community Cloud public demo.

### Step S7 — Build and run the app image

1. Build container (or App Service package) from the HR Agent release.
2. Inject config from secret store + environment.
3. Wire SSO middleware / Easy Auth / OIDC proxy in front of or inside the app.
4. Health check: authenticated `/` (or agreed health path) returns 200 only for allowed identities when tested through SSO.

### Step S8 — First ingest + publish

1. People Ops signs off corpus version (date + file list).
2. Run ingest against tenant storage → tenant vector index.
3. Spot-check 5–10 known questions in the UI (citations point at correct files).

### Step S9 — Eval gate (release blocker)

```bash
python -m src.eval
# or CI job equivalent against tenant golden set
```

1. Maintain `eval/golden_questions.json` (or tenant copy) owned by People Ops + IT.
2. **Do not** promote a corpus/app release if pass rate < 1.0 on the agreed set.
3. Keep report artifact (latency + cost fields if enabled) with the release record.

### Step S10 — Audit + ops hooks

1. Confirm each answer path writes audit fields: user id, timestamp, question, answer, source ids, model.
2. Ship logs to the cloud log stack (CloudWatch / Cloud Logging / Azure Monitor).
3. Optional: retain request cost/latency metrics using the same event shape as demo ops (`latency`, tokens, `est_cost_usd`) without storing unnecessary PII beyond policy.

### Step S11 — Pilot launch checklist

- [ ] SSO works for pilot group only  
- [ ] Anonymous access denied  
- [ ] Handbook is customer pack (not public sample)  
- [ ] Eval gate green on pilot golden set  
- [ ] Audit events visible in log store  
- [ ] LLM billing alerts on customer account  
- [ ] Escalation copy visible in UI (exceptions → HR ticket)  
- [ ] Rollback: previous index + previous app image tagged  

### Step S12 — Expand after pilot

1. Widen SSO group / full <1k headcount as agreed.  
2. Add handbook entities only with eval cases per entity.  
3. Path B only: optional Teams bot **after** web SSO path is stable.  

---

## 3. Path A — Cloud-neutral steps (detail)

Use when IT is not standardizing on M365/Azure as the spine.

### A1. Identity

1. Create OIDC application in Okta / Google / Entra / Auth0 (any).
2. Claims: stable user id, email, groups (for pilot ACL).
3. Put client secret in AWS Secrets Manager / GCP Secret Manager / Key Vault (if Azure compute).

### A2. Compute

1. Push image to ECR / Artifact Registry / ACR.  
2. Deploy service: **ECS/Fargate**, **Cloud Run**, **Azure Container Apps**, or EKS equivalent.  
3. Min instances: enough for cold-start tolerance on pilot; scale policy on CPU/RPS.  
4. Attach IAM/service account with least privilege to storage + secrets + DB.

### A3. Handbook storage

| Cloud | Typical choice |
|-------|----------------|
| AWS | S3 bucket, block public access |
| GCP | GCS bucket, uniform access |
| Azure | Blob container |

Version objects (or folder-per-release) so ingest can pin a corpus version.

### A4. Index

1. Managed Postgres with `pgvector` (RDS, Cloud SQL, Azure DB for PostgreSQL).  
2. Or existing vector service if company standard — keep **one** retrieval path in app config.  
3. Network: private subnet / serverless VPC connector.

### A5. Edge

1. HTTPS load balancer or Cloud Run/ACS ingress.  
2. OIDC-aware proxy (e.g. oauth2-proxy) **or** app-native OIDC.  
3. Optional IP allowlist / VPN-only DNS.

### A6. Observability

- Logs + metrics in native cloud stack.  
- Alerts: 5xx rate, auth failures, LLM upstream errors, eval job failure.

### A7. Path A done when

Pilot users sign in via company IdP, ask handbook questions, see citations, and IT can pull an audit row for a sample user session.

---

## 4. Path B — Microsoft-centric steps (detail)

Use when **Entra + M365** is the workplace default.

### B1. Entra application

1. App registration in the company tenant.  
2. Redirect URIs for App Service / Container Apps URL.  
3. Optional: **Easy Auth** (App Service Authentication) with Entra — fastest SSO.  
4. Alternative: MSAL in-app if Easy Auth is not used.  
5. Assign pilot security group; block entire org until pilot exit.

### B2. Azure compute

1. **Azure Container Apps** or **App Service** (Linux container).  
2. System- or user-assigned managed identity.  
3. Grant identity `get/list` on Key Vault secrets; read on handbook storage.

### B3. Handbook storage

**Preferred for People Ops:** SharePoint document library (versioning + familiar permissions).  
**Alternative:** Azure Blob with private endpoint.

Ingest identity needs read; editors need contribute; production app does not need write after publish if ingest is a separate job.

### B4. Index

Pick one:

| Option | When |
|--------|------|
| Azure Database for PostgreSQL + pgvector | Align with Path A shape / portability |
| **Azure AI Search** | Prefer Microsoft search stack / semantic features |

Keep tenant isolation (index or filter per employer entity).

### B5. Model

1. Prefer **Azure OpenAI** deployment in customer subscription.  
2. Set `LLM_API_BASE` / `LLM_MODEL` to the deployment.  
3. Key or Entra auth to AOAI per company standard — store in **Key Vault**.

### B6. Networking

1. Private endpoints for Key Vault, storage, DB/Search when required.  
2. App accessible on corporate network or via Entra-secured public HTTPS (still **authenticated**).  
3. Azure Monitor + Log Analytics workspace for audit trail.

### B7. Optional later (not pilot day-one)

- Teams bot front door calling the **same** answer API.  
- SharePoint change webhook → re-ingest pipeline.  

Do not block pilot on Teams.

### B8. Path B done when

Pilot users open the private URL, authenticate with Entra, receive cited answers from the SharePoint/Blob handbook pack, and Security can query Log Analytics for a sample session.

---

## 5. Cutover & release rhythm (both paths)

| Cadence | Action |
|---------|--------|
| Every corpus change | People Ops approve → ingest → **eval gate** → switch active index |
| Every app release | Deploy new image → smoke SSO + 3 golden questions → keep previous image rollback tag |
| Weekly pilot | Review audit samples, failed retrievals, cost estimates, escalations |
| Pilot exit | Widen SSO group; freeze runbooks; schedule BAU support owner |

### Rollback

1. Point app at previous container image tag.  
2. Point retrieval config at previous index/collection name.  
3. Re-run smoke + eval on previous golden set snapshot.

---

## 6. What you deliberately do **not** do in production

- Use **Streamlit Community Cloud** public demo as the employee system of record  
- Ship **anonymous** access “just for testing” on the production URL  
- Index **unlicensed** or personal documents  
- Let the assistant **submit** leave, pay changes, or approvals  
- Skip eval because “only a small handbook tweak”  
- Store production API keys in git or in the public demo secrets as a shared prod key  

---

## 7. Quick reference — who does what

| Step | IT | People Ops | Security |
|------|----|------------|----------|
| Choose A vs B | Lead | Consult | Consult |
| SSO app | Lead | — | Review |
| Hosting / network | Lead | — | Review |
| Handbook pack | Support ingest IAM | **Lead** | Classify |
| Golden questions | CI hook | **Lead** content | Spot-check |
| LLM key | Wire secrets | — | Approve vendor |
| Pilot comms | — | **Lead** | — |
| Audit retention | Implement | Define need | **Lead** policy |

---

## 8. Related artifacts

| File | Use |
|------|-----|
| [`DEPLOY-A-vs-B.md`](DEPLOY-A-vs-B.md) | Executive / IT one-pager |
| [`diagrams/production-deploy-architecture.html`](diagrams/production-deploy-architecture.html) | Production topology |
| [`diagrams/demo-streamlit-architecture.html`](diagrams/demo-streamlit-architecture.html) | Public demo topology |
| [`OPS.md`](OPS.md) | Demo logging, cost env, eval commands |
| [`PRODUCT.md`](PRODUCT.md) | Product design & boundaries |
| Repo `README.md` | Clone, local run, public demo link |

---

## Commercial one-liner

> **Production HR Agent is private + SSO. Deploy Path A (cloud-neutral) or Path B (Azure/M365). Bring your own model key. Same product either way.**
