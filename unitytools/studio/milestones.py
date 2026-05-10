"""Milestone progress computation.

`milestones.json` stores the goals; `backlog.json` and the archive
together hold the tasks. This module joins them: for each milestone,
how many tasks link to it, what's their status mix, and what percent
done are we.

Done tasks live in TWO places after Phase 12 (auto-archive): in
backlog.json until they age out, then in archive/<YYYY>.json. The
progress calculation always reads BOTH so old finished work still
counts toward the milestone, and a freshly archived task does not
suddenly disappear from the percentage.
"""
from __future__ import annotations

from typing import Optional

from .archive import load_archived_tasks
from .models import Milestone, Task, TaskStatus
from .state import StudioState


def _aggregate_tasks(state: StudioState) -> list[Task]:
    """Active backlog plus the full archive, deduped by id (active wins)."""
    active = state.load_tasks()
    archived = load_archived_tasks(state)
    seen = {t.id for t in active}
    merged = list(active)
    for t in archived:
        if t.id not in seen:
            merged.append(t)
            seen.add(t.id)
    return merged


def _tasks_for_milestone(tasks: list[Task], milestone_id: str) -> list[Task]:
    return [t for t in tasks if (t.milestone or "") == milestone_id]


def _progress_dict(milestone: Milestone, related: list[Task]) -> dict:
    by_status: dict[str, int] = {}
    for t in related:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
    done = by_status.get(TaskStatus.DONE.value, 0)
    total = len(related)
    pct = (done / total) if total > 0 else 0.0
    return {
        "milestone_id": milestone.id,
        "name": milestone.name,
        "description": milestone.description,
        "status": milestone.status.value,
        "target_date": milestone.target_date,
        "success_criteria_count": len(milestone.success_criteria),
        "task_count": total,
        "by_status": by_status,
        "done_count": done,
        "completion_pct": pct,
    }


def milestone_progress(state: StudioState, milestone_id: str) -> Optional[dict]:
    """Compute progress for one milestone, or None if it doesn't exist."""
    milestones = state.load_milestones()
    target = next((m for m in milestones if m.id == milestone_id), None)
    if target is None:
        return None
    tasks = _aggregate_tasks(state)
    return _progress_dict(target, _tasks_for_milestone(tasks, milestone_id))


def all_milestones_with_progress(state: StudioState) -> list[dict]:
    """Progress for every milestone, ordered by `created_at`."""
    milestones = sorted(state.load_milestones(), key=lambda m: m.created_at)
    tasks = _aggregate_tasks(state)
    return [_progress_dict(m, _tasks_for_milestone(tasks, m.id)) for m in milestones]
