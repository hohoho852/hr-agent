"""Append-only JSONL logging for query/chat LLM calls (fail-open)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from llama_index.core import Settings
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.core.callbacks.token_counting import (
    TokenCountingHandler,
    get_tokens_from_response,
)

from src.config import configure_settings, llm_model_name, project_root
from src.cost import UsageSource, estimate_cost, resolve_token_usage

QUERY_EVENTS_PATH = project_root() / "runs" / "query_events.jsonl"


class _QueryUsageTracker(TokenCountingHandler):
    """Accumulates per-query LLM token usage via LlamaIndex callbacks."""

    def __init__(self) -> None:
        super().__init__()
        self._provider_llm_calls = 0
        self._total_llm_calls = 0

    def reset_counts(self) -> None:
        super().reset_counts()
        self._provider_llm_calls = 0
        self._total_llm_calls = 0

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        if (
            event_type == CBEventType.LLM
            and event_type not in self.event_ends_to_ignore
            and payload is not None
        ):
            self._total_llm_calls += 1
            response = payload.get(EventPayload.RESPONSE)
            if response is not None:
                prompt_tokens, completion_tokens = get_tokens_from_response(response)
                if prompt_tokens > 0 or completion_tokens > 0:
                    self._provider_llm_calls += 1
        super().on_event_end(
            event_type, payload=payload, event_id=event_id, **kwargs
        )

    @property
    def usage_source(self) -> UsageSource:
        if self._total_llm_calls > 0 and self._provider_llm_calls == self._total_llm_calls:
            return "provider"
        if self._provider_llm_calls > 0:
            return "provider"
        if self.prompt_llm_token_count > 0 or self.completion_llm_token_count > 0:
            return "estimate"
        return "estimate"


_tracker: _QueryUsageTracker | None = None


def query_events_path() -> Path:
    return QUERY_EVENTS_PATH


def _ensure_tracker() -> _QueryUsageTracker:
    global _tracker
    configure_settings()
    llm = Settings.llm
    if _tracker is None:
        _tracker = _QueryUsageTracker()
    if _tracker not in llm.callback_manager.handlers:
        llm.callback_manager.add_handler(_tracker)
    return _tracker


def count_sources(response: Any) -> int:
    if response is None:
        return 0
    nodes = getattr(response, "source_nodes", None)
    if nodes is not None:
        return len(nodes)
    sources = getattr(response, "sources", None)
    if sources is not None:
        return len(sources)
    return 0


def append_query_event(event: dict[str, Any]) -> None:
    """Append one JSON line; never raises to callers."""
    try:
        path = query_events_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_query_event(
    *,
    latency_ms: float,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    usage_source: UsageSource,
    ok: bool,
    n_sources: int,
    error_type: str | None = None,
    question_len: int | None = None,
) -> None:
    est_cost_usd = estimate_cost(prompt_tokens, completion_tokens, model)
    event: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "latency_ms": round(latency_ms, 2),
        "model": model,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "est_cost_usd": est_cost_usd,
        "usage_source": usage_source,
        "ok": ok,
        "n_sources": int(n_sources),
    }
    if error_type:
        event["error_type"] = error_type
    if question_len is not None:
        event["question_len"] = int(question_len)
    append_query_event(event)


def record_query_call(
    call: Callable[[], Any],
    *,
    model: str | None = None,
    question: str = "",
    question_len: int | None = None,
    n_sources_fn: Callable[[Any], int] | None = None,
    return_metrics: bool = False,
) -> Any:
    """Run a query/chat call, track usage, append JSONL (success or failure)."""
    tracker = _ensure_tracker()
    tracker.reset_counts()
    model_name = model or llm_model_name()
    q_len = question_len if question_len is not None else len(question or "")
    source_counter = n_sources_fn or count_sources

    t0 = time.perf_counter()
    ok = True
    error_type: str | None = None
    result: Any = None
    metrics: dict[str, Any] = {}
    try:
        result = call()
        return (result, metrics) if return_metrics else result
    except Exception as exc:
        ok = False
        error_type = type(exc).__name__
        raise
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        prompt_tokens = tracker.prompt_llm_token_count
        completion_tokens = tracker.completion_llm_token_count
        usage_source = tracker.usage_source
        answer = ""
        if ok and result is not None:
            answer = str(getattr(result, "response", result) or "")
        prompt_tokens, completion_tokens, usage_source = resolve_token_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usage_source=usage_source,
            question=question,
            answer=answer,
        )
        n_sources = source_counter(result) if ok else 0
        est_cost_usd = estimate_cost(prompt_tokens, completion_tokens, model_name)
        metrics.update(
            {
                "latency_ms": round(latency_ms, 2),
                "latency_s": round(latency_ms / 1000.0, 3),
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "est_cost_usd": est_cost_usd,
                "usage_source": usage_source,
            }
        )
        log_query_event(
            latency_ms=latency_ms,
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usage_source=usage_source,
            ok=ok,
            n_sources=n_sources,
            error_type=error_type,
            question_len=q_len,
        )


def read_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    path = query_events_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
