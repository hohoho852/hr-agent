"""Print a short summary of recent query events from runs/query_events.jsonl."""

from __future__ import annotations

import argparse
import sys

from src.config import project_root
from src.query_log import read_recent_events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize recent HR Agent query events (runs/query_events.jsonl)"
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=50,
        help="Number of most recent events to include (default: 50)",
    )
    args = parser.parse_args(argv)

    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)

    events = read_recent_events(limit=max(1, args.limit))
    if not events:
        print("No query events found (runs/query_events.jsonl is empty or missing).")
        return 0

    count = len(events)
    errors = sum(1 for e in events if not e.get("ok", True))
    latencies = [float(e.get("latency_ms", 0)) for e in events]
    costs = [float(e.get("est_cost_usd", 0)) for e in events]
    avg_latency_ms = sum(latencies) / count
    total_cost = sum(costs)

    print(f"Events (last {count}):")
    print(f"  error_rate: {errors / count:.1%} ({errors}/{count})")
    print(f"  avg_latency_ms: {avg_latency_ms:.1f}")
    print(f"  sum_est_cost_usd: ${total_cost:.6f}")
    provider = sum(1 for e in events if e.get("usage_source") == "provider")
    estimate = sum(1 for e in events if e.get("usage_source") == "estimate")
    print(f"  usage_source: provider={provider} estimate={estimate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
