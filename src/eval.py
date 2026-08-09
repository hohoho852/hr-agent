"""Lightweight evaluation harness for HR Agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config import llm_model_name, project_root
from src.query import get_query_engine
from src.query_log import record_query_call


def _load_golden(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list) or not data:
        raise ValueError(f"Golden set must be a non-empty list: {path}")
    return data


def _keyword_hit(answer: str, must_include_any: list[str]) -> bool:
    text = (answer or "").lower()
    return any(token.lower() in text for token in must_include_any)


def _retrieval_hit(source_nodes, expected_file_substr: str) -> bool:
    needle = (expected_file_substr or "").lower()
    if not needle:
        return True
    for node in source_nodes or []:
        meta = getattr(node, "metadata", {}) or {}
        name = str(
            meta.get("file_name")
            or meta.get("filename")
            or meta.get("file_path")
            or ""
        ).lower()
        if needle in name:
            return True
    return False


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def evaluate(golden_path: Path | None = None) -> dict:
    root = project_root()
    path = golden_path or (root / "eval" / "golden_questions.json")
    cases = _load_golden(path)
    engine = get_query_engine()
    model = llm_model_name()
    rows = []
    for case in cases:
        q = case["question"]
        response, metrics = record_query_call(
            lambda q=q: engine.query(q),
            question=q,
            model=model,
            return_metrics=True,
        )
        latency = metrics["latency_s"]
        answer = getattr(response, "response", str(response))
        sources = getattr(response, "source_nodes", []) or []
        kw_ok = _keyword_hit(answer, case.get("must_include_any") or [])
        ret_ok = _retrieval_hit(sources, case.get("expected_file_substr") or "")
        top_files = []
        for node in sources[:4]:
            meta = getattr(node, "metadata", {}) or {}
            top_files.append(
                meta.get("file_name")
                or meta.get("filename")
                or meta.get("file_path")
                or "Unknown"
            )
        rows.append(
            {
                "id": case.get("id"),
                "question": q,
                "latency_s": latency,
                "prompt_tokens": metrics["prompt_tokens"],
                "completion_tokens": metrics["completion_tokens"],
                "est_cost_usd": metrics["est_cost_usd"],
                "usage_source": metrics["usage_source"],
                "keyword_hit": kw_ok,
                "retrieval_hit": ret_ok,
                "pass": bool(kw_ok and ret_ok),
                "answer_preview": (answer or "")[:280],
                "top_files": top_files,
            }
        )
        status = "PASS" if rows[-1]["pass"] else "FAIL"
        print(
            f"[{status}] {case.get('id')} kw={kw_ok} retrieval={ret_ok} "
            f"latency={latency:.2f}s cost=${metrics['est_cost_usd']:.6f}"
        )

    n = len(rows) or 1
    latencies = [r["latency_s"] for r in rows]
    costs = [r["est_cost_usd"] for r in rows]
    total_cost = sum(costs)
    return {
        "product": "hr-agent",
        "model": model,
        "cases": len(rows),
        "pass_rate": round(sum(1 for r in rows if r["pass"]) / n, 3),
        "keyword_hit_rate": round(sum(1 for r in rows if r["keyword_hit"]) / n, 3),
        "retrieval_hit_rate": round(sum(1 for r in rows if r["retrieval_hit"]) / n, 3),
        "avg_latency_s": round(sum(latencies) / n, 3),
        "p95_latency_s": round(_p95(latencies), 3),
        "total_est_cost_usd": round(total_cost, 6),
        "avg_est_cost_usd": round(total_cost / n, 6),
        "results": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate HR Agent RAG")
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)

    summary = evaluate(args.golden)
    print("\n=== EVAL SUMMARY ===")
    print(
        json.dumps(
            {
                "product": summary["product"],
                "cases": summary["cases"],
                "pass_rate": summary["pass_rate"],
                "keyword_hit_rate": summary["keyword_hit_rate"],
                "retrieval_hit_rate": summary["retrieval_hit_rate"],
                "avg_latency_s": summary["avg_latency_s"],
                "p95_latency_s": summary["p95_latency_s"],
                "total_est_cost_usd": summary["total_est_cost_usd"],
                "avg_est_cost_usd": summary["avg_est_cost_usd"],
            },
            indent=2,
        )
    )
    out = args.out or (project_root() / "eval" / "last_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(f"Wrote report: {out}")
    return 0 if summary["pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
