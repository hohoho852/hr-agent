"""Token usage helpers and USD cost estimates for LLM calls."""

from __future__ import annotations

import os
from typing import Any, Literal

UsageSource = Literal["provider", "estimate"]

# DeepSeek-ish defaults (override via env; see docs/OPS.md).
_DEFAULT_USD_PER_1M_PROMPT = 0.14
_DEFAULT_USD_PER_1M_COMPLETION = 0.28

_CHARS_PER_TOKEN_ESTIMATE = 4


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def usd_per_1m_prompt_tokens(model: str | None = None) -> float:
    """USD per 1M prompt tokens (env: LLM_COST_USD_PER_1M_PROMPT)."""
    _ = model
    return _env_float("LLM_COST_USD_PER_1M_PROMPT", _DEFAULT_USD_PER_1M_PROMPT)


def usd_per_1m_completion_tokens(model: str | None = None) -> float:
    """USD per 1M completion tokens (env: LLM_COST_USD_PER_1M_COMPLETION)."""
    _ = model
    return _env_float("LLM_COST_USD_PER_1M_COMPLETION", _DEFAULT_USD_PER_1M_COMPLETION)


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str | None = None,
) -> float:
    """Estimated USD for a single LLM call (label as estimate in logs/reports)."""
    prompt_rate = usd_per_1m_prompt_tokens(model)
    completion_rate = usd_per_1m_completion_tokens(model)
    cost = (prompt_tokens / 1_000_000) * prompt_rate + (
        completion_tokens / 1_000_000
    ) * completion_rate
    return round(cost, 8)


def estimate_tokens_from_text(text: str) -> int:
    """Heuristic token count when the provider omits usage metadata."""
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN_ESTIMATE)


def usage_from_object(obj: Any) -> tuple[int, int] | None:
    """Read prompt/completion token counts from a provider or LlamaIndex response."""
    if obj is None:
        return None

    candidates: list[Any] = [obj]
    for attr in ("additional_kwargs", "raw", "usage", "metadata"):
        if hasattr(obj, attr):
            candidates.append(getattr(obj, attr))

    if isinstance(obj, dict):
        candidates.extend([obj.get("usage"), obj.get("additional_kwargs")])

    for candidate in candidates:
        parsed = _parse_usage_dict(candidate)
        if parsed is not None:
            return parsed

    raw = getattr(obj, "raw", None)
    if raw is not None and raw is not obj:
        nested = usage_from_object(raw)
        if nested is not None:
            return nested

    return None


def _parse_usage_dict(data: Any) -> tuple[int, int] | None:
    if data is None:
        return None

    usage = data
    if hasattr(data, "usage"):
        usage = data.usage
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif hasattr(usage, "dict"):
        usage = usage.dict()
    if not isinstance(usage, dict):
        return None

    prompt_keys = ("prompt_tokens", "input_tokens", "prompt_token_count")
    completion_keys = (
        "completion_tokens",
        "output_tokens",
        "candidates_token_count",
    )

    prompt_tokens = _first_int(usage, prompt_keys)
    completion_tokens = _first_int(usage, completion_keys)
    if prompt_tokens == 0 and completion_tokens == 0:
        return None
    return prompt_tokens, completion_tokens


def _first_int(data: dict, keys: tuple[str, ...]) -> int:
    for key in keys:
        if key in data and data[key] is not None:
            try:
                return int(data[key])
            except (TypeError, ValueError):
                continue
    return 0


def resolve_token_usage(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    usage_source: UsageSource,
    question: str = "",
    answer: str = "",
) -> tuple[int, int, UsageSource]:
    """Return final token counts, applying heuristics only when needed."""
    if prompt_tokens > 0 or completion_tokens > 0:
        return prompt_tokens, completion_tokens, usage_source

    est_prompt = estimate_tokens_from_text(question)
    est_completion = estimate_tokens_from_text(answer)
    return est_prompt, est_completion, "estimate"
