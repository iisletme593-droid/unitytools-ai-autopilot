"""Doc-level studio tools — exposed to RoleAgents via the tool registry.

Phase 2 surface: read/write the canonical project documents (GDD, art
bible, sprint), and append to the structured records (backlog, decisions).
No engine calls. Roles operate on text + JSON only.

The state object is injected once via `init_studio_tools(state)` so the
@tool functions stay zero-arg-friendly for the LLM.
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.tool_registry import tool
from .models import Decision, DecisionStatus, Milestone, MilestoneStatus, ROLES, Task, TaskStatus
from .state import StudioState

_STATE: Optional[StudioState] = None


def init_studio_tools(state: StudioState) -> None:
    """Inject the studio state used by all `studio_*` tools."""
    global _STATE
    _STATE = state


def _require_state() -> StudioState:
    if _STATE is None:
        raise RuntimeError(
            "Studio tools were called without state. Run `init_studio_tools(state)` first."
        )
    return _STATE


# ─── Documents ─────────────────────────────────────────────────────────

@tool(description="Read the current Game Design Document (returns full markdown).")
def studio_read_gdd() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.gdd)}


@tool(description="Replace the entire Game Design Document with new markdown. Use after consolidating discussion into a coherent doc.")
def studio_write_gdd(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.gdd, content)
    return {"ok": True, "path": str(state.paths.gdd), "bytes": len(content.encode("utf-8"))}


@tool(description="Read the current Art Bible (style, palette, references).")
def studio_read_art_bible() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.art_bible)}


@tool(description="Replace the Art Bible with new markdown.")
def studio_write_art_bible(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.art_bible, content)
    return {"ok": True, "path": str(state.paths.art_bible)}


@tool(description="Read the current sprint plan markdown.")
def studio_read_sprint() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.sprint_current)}


@tool(description="Replace the current sprint plan markdown.")
def studio_write_sprint(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.sprint_current, content)
    return {"ok": True, "path": str(state.paths.sprint_current)}


# ─── Backlog ───────────────────────────────────────────────────────────

@tool(description="Add a task to the backlog. role must be one of: producer, designer, art_director, level_designer, tech_artist, qa, critic.")
def studio_add_task(title: str, role: str, description: str = "", milestone: str = "") -> dict:
    state = _require_state()
    if role not in ROLES:
        return {"ok": False, "error": f"Unknown role {role!r}. Allowed: {list(ROLES)}"}
    task = Task(
        title=title,
        role=role,
        description=description,
        milestone=milestone or None,
    )
    state.add_task(task)
    return {"ok": True, "task_id": task.id, "title": task.title, "role": task.role, "status": task.status.value}


@tool(description="List backlog tasks. Optional status filter: pending, in_progress, blocked, review, done, rejected. Optional role filter.")
def studio_list_tasks(status: str = "", role: str = "") -> dict:
    state = _require_state()
    tasks = state.load_tasks()
    if status:
        try:
            wanted = TaskStatus(status)
        except ValueError:
            return {"ok": False, "error": f"Unknown status {status!r}."}
        tasks = [t for t in tasks if t.status is wanted]
    if role:
        tasks = [t for t in tasks if t.role == role]
    return {
        "ok": True,
        "count": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "status": t.status.value,
                "milestone": t.milestone,
                "blockers": t.blockers,
            }
            for t in tasks
        ],
    }


@tool(description="Change a task's status. Valid statuses: pending, in_progress, blocked, review, done, rejected.")
def studio_update_task_status(task_id: str, status: str) -> dict:
    state = _require_state()
    try:
        new_status = TaskStatus(status)
    except ValueError:
        return {"ok": False, "error": f"Unknown status {status!r}."}
    tasks = state.load_tasks()
    for t in tasks:
        if t.id == task_id:
            t.status = new_status
            state.update_task(t)
            return {"ok": True, "task_id": t.id, "status": t.status.value}
    return {"ok": False, "error": f"Task {task_id!r} not found."}


# ─── Decisions ─────────────────────────────────────────────────────────

@tool(description="Propose a design decision. Append-only. Default status is 'proposed'; use studio_accept_decision to ratify.")
def studio_propose_decision(title: str, summary: str, rationale: str = "", alternatives: Optional[list[str]] = None) -> dict:
    state = _require_state()
    decision = Decision(
        title=title,
        summary=summary,
        rationale=rationale,
        alternatives_considered=list(alternatives or []),
    )
    state.append_decision(decision)
    return {"ok": True, "decision_id": decision.id, "status": decision.status.value}


@tool(description="List recent decisions. Returns up to limit entries, newest last.")
def studio_list_decisions(limit: int = 50) -> dict:
    state = _require_state()
    decisions = state.load_decisions()[-max(1, limit):]
    return {
        "ok": True,
        "count": len(decisions),
        "decisions": [
            {
                "id": d.id,
                "title": d.title,
                "summary": d.summary,
                "status": d.status.value,
                "author_role": d.author_role,
                "timestamp": d.timestamp,
            }
            for d in decisions
        ],
    }


# ─── Milestones ────────────────────────────────────────────────────────

@tool(description="Add a milestone with success criteria.")
def studio_add_milestone(name: str, description: str = "", success_criteria: Optional[list[str]] = None, target_date: str = "") -> dict:
    state = _require_state()
    milestone = Milestone(
        name=name,
        description=description,
        success_criteria=list(success_criteria or []),
        target_date=target_date or None,
    )
    state.add_milestone(milestone)
    return {"ok": True, "milestone_id": milestone.id, "name": milestone.name}


@tool(description="List milestones with status counts.")
def studio_list_milestones() -> dict:
    state = _require_state()
    milestones = state.load_milestones()
    return {
        "ok": True,
        "count": len(milestones),
        "milestones": [
            {
                "id": m.id,
                "name": m.name,
                "status": m.status.value,
                "target_date": m.target_date,
                "criteria_count": len(m.success_criteria),
            }
            for m in milestones
        ],
    }


# ─── Project summary ───────────────────────────────────────────────────

@tool(description="Snapshot of project state: counts, doc presence. Use as the first call to orient yourself.")
def studio_get_summary() -> dict:
    state = _require_state()
    return {"ok": True, **state.summary()}


# ─── Convenience: list of all studio tool names (used by RoleConfig) ───

ALL_STUDIO_TOOL_NAMES: tuple[str, ...] = (
    "studio_read_gdd",
    "studio_write_gdd",
    "studio_read_art_bible",
    "studio_write_art_bible",
    "studio_read_sprint",
    "studio_write_sprint",
    "studio_add_task",
    "studio_list_tasks",
    "studio_update_task_status",
    "studio_propose_decision",
    "studio_list_decisions",
    "studio_add_milestone",
    "studio_list_milestones",
    "studio_get_summary",
)
