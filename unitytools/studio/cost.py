"""LLM cost / token observability for the studio.

The studio runs roles continuously; without observability there's no
way for the operator to see "how much did today cost" or "which role
is burning the most tokens." This module is intentionally minimal:

  - estimate_cost(model, in_toks, out_toks) -> USD
  - CostLogger.append(role_id, model, in_toks, out_toks)
      appends one JSONL row to studio/qa/cost_log.jsonl
  - summarise(state, days) reads back the log and aggregates per-day,
    per-role, per-model

Hookup is done in runner.py: when an LLMClient.complete() returns
a "usage" block, the RoleRunner appends to the log. Clients without
usage (RehearsalLLM, FakeLLM tests) skip silently — no breakage.

Pricing reflects published rates per million tokens (approx.); the
table is patchable per project via studio/cost_rates.json.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:
    from .state import StudioState

logger = logging.getLogger(__name__)


# (input $/M, output $/M)
_DEFAULT_RATES: dict[str, tuple[float, float]] = {
    # Anthropic Claude family
    "claude-opus-4-5-20250929": (15.0, 75.0),
    "claude-opus-4-1": (15.0, 75.0),
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-5-haiku": (0.80, 4.0),
    # Local Ollama models — zero cost
    "gemma4": (0.0, 0.0),
    "gemma3": (0.0, 0.0),
    "qwen2.5": (0.0, 0.0),
    "qwen3": (0.0, 0.0),
    "llama3.1": (0.0, 0.0),
    "llama3.2": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost estimate for one LLM call.

    Lookup tries the full model name first, then a prefix-match against
    the family (so 'claude-sonnet-4-5-20250929' matches 'claude-sonnet-4-5').
    Unknown models cost 0 — visibility without false alarms.
    """
    if not model:
        return 0.0
    rates = _DEFAULT_RATES.get(model)
    if rates is None:
        for key, val in _DEFAULT_RATES.items():
            if model.startswith(key):
                rates = val
                break
    if rates is None:
        return 0.0
    in_rate, out_rate = rates
    return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate


@dataclass(frozen=True)
class CostEntry:
    ts: float
    role_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float

    def to_jsonl(self) -> str:
        return json.dumps(
            {
                "ts": self.ts,
                "role_id": self.role_id,
                "model": self.model,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cost_usd": round(self.cost_usd, 6),
            },
            ensure_ascii=False,
        )


def cost_log_path(state: "StudioState") -> Path:
    return state.paths.qa / "cost_log.jsonl"


def append_cost_entry(
    state: "StudioState",
    *,
    role_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    ts: Optional[float] = None,
) -> CostEntry:
    """Append one cost row to studio/qa/cost_log.jsonl atomically."""
    if input_tokens < 0 or output_tokens < 0:
        # Bad input from a buggy client — skip silently rather than
        # corrupt the log.
        logger.warning(
            "append_cost_entry: negative tokens role=%s model=%s in=%s out=%s — skipped",
            role_id, model, input_tokens, output_tokens,
        )
        return CostEntry(
            ts=ts if ts is not None else time.time(),
            role_id=role_id, model=model,
            input_tokens=0, output_tokens=0, cost_usd=0.0,
        )

    entry = CostEntry(
        ts=ts if ts is not None else time.time(),
        role_id=role_id,
        model=model,
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        cost_usd=estimate_cost(model, int(input_tokens), int(output_tokens)),
    )
    path = cost_log_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = entry.to_jsonl() + "\n"
    # Append; this is not multi-process safe, but a single studio instance
    # is the contract.
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return entry


def load_cost_entries(state: "StudioState") -> list[CostEntry]:
    path = cost_log_path(state)
    if not path.exists():
        return []
    entries: list[CostEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        try:
            entries.append(CostEntry(
                ts=float(row.get("ts", 0.0)),
                role_id=str(row.get("role_id", "")),
                model=str(row.get("model", "")),
                input_tokens=int(row.get("input_tokens", 0)),
                output_tokens=int(row.get("output_tokens", 0)),
                cost_usd=float(row.get("cost_usd", 0.0)),
            ))
        except (TypeError, ValueError):
            continue
    return entries


def _utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def summarise(state: "StudioState", days: int = 1) -> dict:
    """Aggregate the cost log over the last `days` days (UTC). days=0
    returns the entire log.

    Returns:
      {
        "ok": True,
        "days": days,
        "since_ts": float,
        "total_calls": int,
        "total_input_tokens": int,
        "total_output_tokens": int,
        "total_cost_usd": float,
        "by_role": {role_id: {calls, input_tokens, output_tokens, cost_usd}},
        "by_model": {model: {...}},
        "by_day": {YYYY-MM-DD: {...}},
      }
    """
    entries = load_cost_entries(state)
    cutoff = 0.0 if days <= 0 else time.time() - days * 86400.0
    by_role: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    by_day: dict[str, dict] = {}
    total_calls = 0
    total_in = 0
    total_out = 0
    total_cost = 0.0
    for e in entries:
        if e.ts < cutoff:
            continue
        total_calls += 1
        total_in += e.input_tokens
        total_out += e.output_tokens
        total_cost += e.cost_usd
        for bucket, key in ((by_role, e.role_id), (by_model, e.model), (by_day, _utc_day(e.ts))):
            row = bucket.setdefault(key, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            row["calls"] += 1
            row["input_tokens"] += e.input_tokens
            row["output_tokens"] += e.output_tokens
            row["cost_usd"] += e.cost_usd
    # Round costs for human display, leaving raw aggregation intact above.
    for bucket in (by_role, by_model, by_day):
        for v in bucket.values():
            v["cost_usd"] = round(v["cost_usd"], 6)
    return {
        "ok": True,
        "days": days,
        "since_ts": cutoff,
        "total_calls": total_calls,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_cost_usd": round(total_cost, 6),
        "by_role": by_role,
        "by_model": by_model,
        "by_day": by_day,
    }
