"""Decision-log queries.

`decisions.jsonl` is append-only: every Decision the Designer / Critic /
Art Director / Worker proposes gets a row. Phase 2 shipped
`studio_list_decisions(limit)` which tails the file. Phase 15 adds
filtered queries so the Producer can ask "did anyone propose X
already?" before another role re-files it.

This module mirrors `archive.py:query_archive`: pure read, no writes,
crash-proof against malformed jsonl rows (skip + log).
"""
from __future__ import annotations

import logging
from typing import Optional

from .models import Decision, DecisionStatus
from .state import StudioState

logger = logging.getLogger(__name__)


def query_decisions(
    state: StudioState,
    author_role: Optional[str] = None,
    status: Optional[DecisionStatus] = None,
    since: Optional[float] = None,
    until: Optional[float] = None,
    search: str = "",
    limit: int = 50,
) -> list[Decision]:
    """Filter decisions by author_role / status / time window / substring.

    Returns newest-first (by timestamp), capped at `limit`. `search`
    matches title + summary + rationale, case-insensitive. `limit=0`
    means no cap.
    """
    rows = list(state.iter_decisions())
    needle = (search or "").strip().lower()
    role_filter = (author_role or "").strip()
    out: list[Decision] = []
    for d in rows:
        if role_filter and d.author_role != role_filter:
            continue
        if status is not None and d.status is not status:
            continue
        ts = d.timestamp or 0.0
        if since is not None and ts < since:
            continue
        if until is not None and ts > until:
            continue
        if needle:
            haystack = " ".join(
                (d.title or "", d.summary or "", d.rationale or "")
            ).lower()
            if needle not in haystack:
                continue
        out.append(d)
    out.sort(key=lambda x: x.timestamp or 0.0, reverse=True)
    if limit and limit > 0:
        out = out[:limit]
    return out


def decisions_summary(state: StudioState) -> dict:
    """Counts per status, useful for diagnostics / dashboards."""
    by_status: dict[str, int] = {}
    total = 0
    for d in state.iter_decisions():
        total += 1
        by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
    return {"total": total, "by_status": by_status}
