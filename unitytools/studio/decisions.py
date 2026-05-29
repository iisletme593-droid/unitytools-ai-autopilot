"""Decision-log queries + ratification.

`decisions.jsonl` is append-only: every Decision the Designer / Critic /
Art Director / Worker proposes gets a row. Phase 2 shipped
`studio_list_decisions(limit)` which tails the file. Phase 15 added
filtered queries so the Producer can ask "did anyone propose X
already?" before another role re-files it. Phase 18 adds ratification:
appending a new row with the SAME id but updated status (so the audit
trail stays intact) and a `latest_decisions()` helper so user-facing
reads dedupe by id and show the current state.

Append-only invariant is preserved: ratify never rewrites the file,
it just appends. Readers consult `latest_decisions` to see the
current state per id; `state.load_decisions()` / `iter_decisions()`
still expose the full history for audit.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from .models import Decision, DecisionStatus
from .state import StudioState

logger = logging.getLogger(__name__)


def latest_decisions(state: StudioState) -> list[Decision]:
    """Read the decisions log and return the latest row per id.

    Iterates the full log (audit trail) and keeps the newest entry
    per decision id (by timestamp). This is what user-facing views
    show — `query_decisions`, `decisions_summary`, `studio_list_decisions`,
    and the `studio-decisions` CLI all dedupe through this helper.
    """
    latest: dict[str, Decision] = {}
    for d in state.iter_decisions():
        existing = latest.get(d.id)
        if existing is None or (d.timestamp or 0.0) >= (existing.timestamp or 0.0):
            latest[d.id] = d
    return list(latest.values())


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
    means no cap. Operates on latest-per-id (see `latest_decisions`).
    """
    rows = latest_decisions(state)
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
    """Counts per status (latest-per-id), useful for diagnostics."""
    by_status: dict[str, int] = {}
    total = 0
    for d in latest_decisions(state):
        total += 1
        by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
    return {"total": total, "by_status": by_status}


def ratify_decision(
    state: StudioState,
    decision_id: str,
    new_status: DecisionStatus,
    superseded_by: Optional[str] = None,
) -> Optional[Decision]:
    """Mark an existing decision accepted / rejected / superseded.

    Append-only: a new Decision row is appended with the SAME id but
    the updated status. Subsequent reads via latest_decisions /
    query_decisions / studio_list_decisions see the new status; the
    original proposal stays in the log for audit.

    Returns the new Decision, or None when no matching id exists.
    """
    current = next((d for d in latest_decisions(state) if d.id == decision_id), None)
    if current is None:
        return None
    revised = Decision(
        title=current.title,
        summary=current.summary,
        rationale=current.rationale,
        author_role=current.author_role,
        status=new_status,
        alternatives_considered=list(current.alternatives_considered),
        superseded_by=(superseded_by or current.superseded_by),
    )
    revised.id = current.id  # keep id; new timestamp via default
    state.append_decision(revised)
    return revised


def find_decision(state: StudioState, prefix: str) -> Optional[Decision]:
    """Resolve a decision by exact id or unique id prefix.

    Returns the matching Decision (latest row), None if no match or
    the prefix is ambiguous. Two-or-more matches resolve to None so
    callers do not silently act on the wrong record.
    """
    if not prefix:
        return None
    candidates = [d for d in latest_decisions(state) if d.id == prefix or d.id.startswith(prefix)]
    if len(candidates) != 1:
        return None
    return candidates[0]
