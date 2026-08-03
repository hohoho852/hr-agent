# Product design — HR Agent

Employee policy + standard HR how-to assistant.

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

Out of scope: submitting workflows, payroll fixes, grievances, customer PII, or implementation/configuration consulting.

## 3. Users

| Persona | Job | Success |
|---------|-----|---------|
| Employee | Policy + how-to | Completes the action or understands the rule without a ticket |
| People Ops | Deflect Tier-1 | Lower volume on standard questions; consistent answers |
| HRBP | Protect exceptions | Hard cases still reach humans |
| Buyer / executive (demo) | Evaluate fit | Clean main experience; clear source story |

## 4. Architecture

```text
Client docs (PDF/DOCX)  →  source/ (sample pack for audience)
                            data/  (runtime corpus; md or extracted text)
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
| `source/` PDFs | Show what client input looks like before indexing |

## 5. Evaluation

```bash
python -m src.eval
```

Metrics: retrieval hit-rate, keyword coverage, latency.  
Baseline on the Demo Hong Kong Limited sample pack: 7/7 pass.

## 6. Controls

- Citations + human-in-the-loop copy in the UI  
- No workflow execution  
- Escalate exceptions, pay, and grievances  
- Secrets only via `.env` / platform secrets (never committed)

Production add-ons when you wire a real tenant: SSO, DLP, private LLM endpoint, deflection analytics.
