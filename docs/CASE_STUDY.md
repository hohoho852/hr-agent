# Case Study — HR Agent

Portfolio product · Enterprise AI deployment track  
**Publish target:** public GitHub (job-hunting portfolio)

> This case study covers **only** HR Agent (employee policy + how-to assistant).  
> Multi-SaaS implementation copilot is a **separate product/repo** (`hcm-impl-copilot`).

---

## 1. Situation

People Ops burns capacity on repetitive Tier-1 questions: leave policy, how to request time off, how to update an address, expense rules. Employees wait; HR handles the same answers instead of exceptions and people cases.

## 2. Problem

Build a production-style assistant that:

1. Answers **company policy** from a handbook pack  
2. Teaches **how to complete standard HR actions** in the HRIS  
3. Routes **exceptions** to HR tickets (does not fake approvals)  
4. Always returns **citations**  
5. Can be **evaluated** (not vibe-only demos)

Out of scope: submitting workflows, payroll fixes, grievances, customer PII, implementation-consultant config guidance.

## 3. Users & JTBD

| Persona | Job | Success |
|---------|-----|---------|
| Employee | Policy + how-to | Completes action or understands rule without a ticket |
| People Ops | Deflect Tier-1 | Lower volume on standard Qs; consistent answers |
| HRBP | Protect exceptions | Hard cases still reach humans |

## 4. Architecture

```text
data/*.md (policy + how-to)
  → chunk 800 / overlap 120
  → local BGE → Chroma
  → top_k=4 → DeepSeek compact answer + citations
  → Streamlit UI + golden-set eval
```

| Choice | Why |
|--------|-----|
| RAG over fine-tune-first | Policies change; need source linkage |
| Local embeddings | Keep full handbook text on-machine |
| Inform ≠ execute | Liability / authZ boundary |
| Synthetic corpus | Portfolio-safe; no employer PII |

## 5. Evaluation

Harness: `python -m src.eval`  
Metrics: retrieval hit-rate, keyword coverage, latency.

## 6. Enterprise controls (honest v1)

Citations + HITL copy; no workflow execution; escalate exceptions/pay/grievances.  
Next in a real deploy: SSO, DLP, deflection analytics, private LLM endpoint.

## 7. Hiring signal

- Domain framing (CHRO / ticket deflection), not generic PDF chat  
- Systems path: ingest → retrieve → generate → cite → eval  
- Clear product boundary vs implementation copilot  

## 8. Publish goal

Public **GitHub** repo for portfolio. Separate from any production multi-vendor impl product.
