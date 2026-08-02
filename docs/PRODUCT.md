# Product design — HR Agent

Employee policy + standard HR how-to assistant.

Implementation-consultant multi-SaaS guidance is a **separate product** (`hcm-impl-copilot`).

---

## 1. Situation

People Ops spends capacity on repetitive Tier-1 questions: leave rules, how to request time off, how to update an address, expense steps. Employees wait; HR repeats the same answers instead of handling exceptions.

## 2. Product job

Ship an assistant that:

1. Answers **company policy** from a handbook pack  
2. Explains **how to complete standard HR actions** in the HRIS  
3. Routes **exceptions** to HR (does not fake approvals)  
4. Returns **citations** on every answer  
5. Can be **regression-tested** with a fixed question set  

Out of scope: submitting workflows, payroll fixes, grievances, customer PII, implementation config guidance.

## 3. Users

| Persona | Job | Success |
|---------|-----|---------|
| Employee | Policy + how-to | Completes the action or understands the rule without a ticket |
| People Ops | Deflect Tier-1 | Lower volume on standard questions; consistent answers |
| HRBP | Protect exceptions | Hard cases still reach humans |

## 4. Architecture

```text
data/*.md (policy + how-to)
  → chunk 800 / overlap 120
  → local BGE → Chroma
  → top_k=4 → DeepSeek answer + citations
  → Streamlit UI
  → eval suite (golden questions)
```

| Choice | Why |
|--------|-----|
| RAG first | Policies change; answers must stay source-linked |
| Local embeddings | Keep full handbook text on-machine |
| Inform ≠ execute | Clear authZ / liability boundary |
| Sample corpus in repo | Safe default; swap in licensed policies for production |

## 5. Evaluation

```bash
python -m src.eval
```

Metrics: retrieval hit-rate, keyword coverage, latency.  
Baseline on the Acme HK sample pack: 7/7 pass.

## 6. Controls

- Citations + human-in-the-loop copy in the UI  
- No workflow execution  
- Escalate exceptions, pay, and grievances  
- Secrets only via `.env` (never committed)

Production add-ons when you wire a real tenant: SSO, DLP, private LLM endpoint, deflection analytics.

## 7. Boundary vs HCM Implementation Copilot

| | HR Agent | HCM Implementation Copilot |
|--|----------|----------------------------|
| Audience | Employees | Impl consultants / HRIS / SI |
| Content | Policy + HRIS how-tos | Vendor config / prep guidance |
| Risk focus | Wrong employee advice; over-automation | Cross-vendor bleed; bad tenant changes |
