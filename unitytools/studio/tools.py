"""Doc-level + visual + activity studio tools — exposed to RoleAgents via the tool registry.

Phase 2 surface: read/write the canonical project documents (GDD, art
bible, sprint), and append to the structured records (backlog, decisions).
Phase 3 surface: capture engine screenshots and compare them to reference
images via a vision model. Engine and vision dependencies are injected
through separate `init_studio_*` calls so tests can swap fakes.
Phase 4 surface: read-only views into recent regressions and recent git
commits so the Producer can reason about what changed since last run.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from ..core.tool_registry import tool
from .models import Decision, DecisionStatus, Milestone, MilestoneStatus, ROLES, Task, TaskStatus
from .state import StudioState
from .vision import VisionClient, guess_mime

_STATE: Optional[StudioState] = None
_UNITY: Any = None  # UnityBridge or any object with .is_connected() and .call()
_VISION: Optional[VisionClient] = None


def init_studio_tools(state: StudioState) -> None:
    """Inject the studio state used by all `studio_*` tools."""
    global _STATE
    _STATE = state


def init_studio_unity(unity_bridge: Any) -> None:
    """Inject the Unity bridge used by `studio_capture_screenshot`."""
    global _UNITY
    _UNITY = unity_bridge


def init_studio_vision(vision_client: VisionClient) -> None:
    """Inject the vision client used by `studio_compare_to_reference`."""
    global _VISION
    _VISION = vision_client


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


@tool(description="List backlog tasks. Optional filters: status (pending/in_progress/blocked/review/done/rejected), role, milestone id, substring search against title + description.")
def studio_list_tasks(status: str = "", role: str = "", milestone: str = "", search: str = "") -> dict:
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
    if milestone:
        tasks = [t for t in tasks if (t.milestone or "") == milestone]
    if search:
        needle = search.strip().lower()
        if needle:
            tasks = [
                t for t in tasks
                if needle in (t.title or "").lower() or needle in (t.description or "").lower()
            ]
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


@tool(description="Compute completion progress for one milestone: how many tasks link to it, status breakdown, completion percent (counts both active backlog and archived done tasks). Returns ok=False with reason when the milestone id is unknown.")
def studio_milestone_progress(milestone_id: str) -> dict:
    state = _require_state()
    from .milestones import milestone_progress

    result = milestone_progress(state, milestone_id)
    if result is None:
        return {"ok": False, "error": f"Milestone {milestone_id!r} not found."}
    return {"ok": True, **result}


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


@tool(description="Query decisions with filters: author_role, status (proposed/accepted/rejected/superseded), substring search (matches title + summary + rationale), and limit. Returns newest-first. Use this before proposing a new decision to check whether the same idea was raised earlier.")
def studio_query_decisions(
    author_role: str = "",
    status: str = "",
    search: str = "",
    limit: int = 30,
) -> dict:
    state = _require_state()
    from .decisions import query_decisions

    status_arg = None
    if status:
        try:
            status_arg = DecisionStatus(status)
        except ValueError:
            return {"ok": False, "error": f"Unknown decision status {status!r}. Use proposed / accepted / rejected / superseded."}
    rows = query_decisions(
        state,
        author_role=author_role or None,
        status=status_arg,
        search=search,
        limit=max(1, int(limit or 30)),
    )
    return {
        "ok": True,
        "count": len(rows),
        "filters": {
            "author_role": author_role or None,
            "status": status_arg.value if status_arg else None,
            "search": search or None,
            "limit": limit,
        },
        "decisions": [
            {
                "id": d.id,
                "title": d.title,
                "summary": d.summary,
                "rationale": d.rationale,
                "status": d.status.value,
                "author_role": d.author_role,
                "timestamp": d.timestamp,
                "alternatives_considered": d.alternatives_considered,
            }
            for d in rows
        ],
    }


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


# ─── References (read-only listing) ────────────────────────────────────

@tool(description="List reference images currently sitting under studio/refs/. Use these as targets for studio_compare_to_reference.")
def studio_list_references() -> dict:
    state = _require_state()
    refs_dir = state.paths.refs
    if not refs_dir.is_dir():
        return {"ok": True, "count": 0, "references": []}
    refs = sorted(p for p in refs_dir.iterdir() if p.is_file() and not p.name.startswith("."))
    return {
        "ok": True,
        "count": len(refs),
        "references": [
            {"name": p.name, "path": str(p), "size_bytes": p.stat().st_size}
            for p in refs
        ],
    }


@tool(description="List screenshots captured into studio/qa/screenshots/, newest first.")
def studio_list_screenshots(limit: int = 20) -> dict:
    state = _require_state()
    shots_dir = state.paths.qa_screenshots
    if not shots_dir.is_dir():
        return {"ok": True, "count": 0, "screenshots": []}
    shots = sorted(
        (p for p in shots_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    shots = shots[: max(1, int(limit or 1))]
    return {
        "ok": True,
        "count": len(shots),
        "screenshots": [
            {"name": p.name, "path": str(p), "size_bytes": p.stat().st_size, "mtime": p.stat().st_mtime}
            for p in shots
        ],
    }


# ─── Engine capture ────────────────────────────────────────────────────

@tool(description="Capture a SceneView screenshot from Unity Editor and copy it under studio/qa/screenshots/. Requires Unity to be open and the bridge connected. Use a short hint name like 'level_1_overview' to label the file.")
def studio_capture_screenshot(name: str = "scene") -> dict:
    state = _require_state()
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected. Run init_studio_unity(bridge) first."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected. Open Unity and start the BridgeServer."}
    try:
        result = _UNITY.call("run_visual_qa", {"capture_screenshot": True}, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Unity RPC failed: {exc}", "error_type": type(exc).__name__}

    raw_path = ""
    if isinstance(result, dict):
        raw_path = result.get("screenshot_path") or result.get("path") or ""
    if not raw_path:
        return {"ok": False, "error": "Unity did not return a screenshot path.", "raw": result}
    src = Path(raw_path)
    if not src.exists():
        return {"ok": False, "error": f"Screenshot file does not exist: {src}"}

    state.paths.qa_screenshots.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "scene")).strip("_") or "scene"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dest = state.paths.qa_screenshots / f"{timestamp}_{safe_name}{src.suffix or '.png'}"
    shutil.copy2(src, dest)
    return {
        "ok": True,
        "path": str(dest),
        "name": dest.name,
        "size_bytes": dest.stat().st_size,
        "source": str(src),
    }


# ─── Vision compare ────────────────────────────────────────────────────

@tool(description="Compare a screenshot against a reference image using Claude vision. Returns a structured diff (missing/extra/misplaced items, palette and composition scores). Both paths must exist; reference is typically under studio/refs/, screenshot under studio/qa/screenshots/.")
def studio_compare_to_reference(reference_path: str, screenshot_path: str, instruction: str = "") -> dict:
    state = _require_state()
    if _VISION is None:
        return {"ok": False, "error": "Vision client not injected. Run init_studio_vision(client) first."}
    ref = Path(reference_path)
    cand = Path(screenshot_path)
    if not ref.exists():
        return {"ok": False, "error": f"Reference not found: {ref}"}
    if not cand.exists():
        return {"ok": False, "error": f"Screenshot not found: {cand}"}
    try:
        diff = _VISION.compare(
            reference_bytes=ref.read_bytes(),
            reference_mime=guess_mime(ref),
            candidate_bytes=cand.read_bytes(),
            candidate_mime=guess_mime(cand),
            instruction=instruction,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Vision compare failed: {exc}", "error_type": type(exc).__name__}

    # Persist a compact log entry into qa/regression.jsonl so the producer loop
    # has a time-series of how close we are to references.
    state.append_regression_entry(
        {
            "ts": time.time(),
            "kind": "vision_compare",
            "reference": str(ref),
            "screenshot": str(cand),
            "composition_match": diff.get("composition_match"),
            "palette_match": diff.get("palette_match"),
            "missing": diff.get("missing"),
            "extra": diff.get("extra"),
        }
    )
    return {"ok": True, "reference": str(ref), "screenshot": str(cand), **diff}


# ─── Visual regression baseline (Phase 10b) ────────────────────────────

@tool(description="Cheap local pixel-diff between two screenshots. Returns a 0-1 similarity score (1.0 = identical), mean absolute pixel difference, and per-channel color drift. Use BEFORE studio_compare_to_reference to skip the LLM vision call when the scene has not changed materially. Requires Pillow (already a hard dep).")
def studio_visual_regression_check(reference_path: str, candidate_path: str) -> dict:
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return {"ok": False, "error": "Pillow not installed. pip install Pillow.", "error_type": "MissingDependency"}

    state = _require_state()
    ref = Path(reference_path)
    cand = Path(candidate_path)
    if not ref.exists():
        return {"ok": False, "error": f"Reference not found: {ref}"}
    if not cand.exists():
        return {"ok": False, "error": f"Candidate not found: {cand}"}

    try:
        ref_img = Image.open(ref).convert("RGB")
        cand_img = Image.open(cand).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Could not open image: {exc}", "error_type": type(exc).__name__}

    ref_size = ref_img.size
    cand_size = cand_img.size
    dimensions_match = ref_size == cand_size
    if not dimensions_match:
        # Resize candidate to reference dims for diff. The mismatch flag
        # warns callers that the result is approximate.
        cand_img = cand_img.resize(ref_size, Image.Resampling.LANCZOS)

    diff = ImageChops.difference(ref_img, cand_img)
    means = ImageStat.Stat(diff).mean  # [r_mean, g_mean, b_mean] each 0-255
    overall_mean_255 = sum(means) / len(means) if means else 0.0
    mad = overall_mean_255 / 255.0  # 0-1
    similarity = max(0.0, min(1.0, 1.0 - mad))

    payload = {
        "ts": time.time(),
        "kind": "pixel_diff",
        "reference": str(ref),
        "candidate": str(cand),
        "similarity": similarity,
        "mean_abs_diff": mad,
        "dimensions_match": dimensions_match,
    }
    state.append_regression_entry(payload)

    return {
        "ok": True,
        "similarity": similarity,
        "mean_abs_diff": mad,
        "per_channel_mean": {
            "r": (means[0] / 255.0) if len(means) > 0 else 0.0,
            "g": (means[1] / 255.0) if len(means) > 1 else 0.0,
            "b": (means[2] / 255.0) if len(means) > 2 else 0.0,
        },
        "ref_size": list(ref_size),
        "cand_size": list(cand_size),
        "dimensions_match": dimensions_match,
    }


# ─── Recent activity (Producer inputs) ─────────────────────────────────

@tool(description="Read recent QA regression entries from qa/regression.jsonl. Filter by hours (default 24) or kind (e.g. 'vision_compare'). Newest first.")
def studio_recent_regressions(hours: float = 24.0, kind: str = "", limit: int = 50) -> dict:
    state = _require_state()
    path = state.paths.qa_regression
    if not path.exists():
        return {"ok": True, "count": 0, "entries": []}
    cutoff = time.time() - max(0.0, float(hours)) * 3600.0
    entries: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                ts = entry.get("ts")
                if isinstance(ts, (int, float)) and ts < cutoff:
                    continue
                if kind and entry.get("kind") != kind:
                    continue
                entries.append(entry)
    except OSError as exc:
        return {"ok": False, "error": f"Could not read regression log: {exc}"}
    entries.reverse()
    entries = entries[: max(1, int(limit or 1))]
    return {"ok": True, "count": len(entries), "entries": entries}


@tool(description="Query archived (done/rejected) tasks from studio/archive/<YYYY>.json. Optional filters: year (0 = all years), role, status (done/rejected), search substring (matches title + description). Returns newest first, capped at limit. Use this when wondering 'did we already do something like this?'.")
def studio_query_archive(
    year: int = 0,
    role: str = "",
    status: str = "",
    search: str = "",
    limit: int = 30,
) -> dict:
    state = _require_state()
    from .archive import query_archive

    year_arg = year if isinstance(year, int) and year > 0 else None
    status_arg = None
    if status:
        try:
            status_arg = TaskStatus(status)
        except ValueError:
            return {"ok": False, "error": f"Unknown status {status!r}. Use one of: done, rejected (or any valid TaskStatus)."}
    tasks = query_archive(
        state,
        year=year_arg,
        role=role or None,
        status=status_arg,
        search=search,
        limit=max(1, int(limit or 30)),
    )
    return {
        "ok": True,
        "count": len(tasks),
        "filters": {
            "year": year_arg,
            "role": role or None,
            "status": status_arg.value if status_arg else None,
            "search": search or None,
            "limit": limit,
        },
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "status": t.status.value,
                "milestone": t.milestone,
                "completed_at": t.updated_at or t.created_at,
            }
            for t in tasks
        ],
    }


@tool(description="List recent git commits from the project root. Returns up to limit commits (newest first). Returns an empty list if the project is not a git repo.")
def studio_recent_commits(limit: int = 20) -> dict:
    state = _require_state()
    project = state.paths.project_root
    limit = max(1, int(limit or 1))
    try:
        proc = subprocess.run(
            ["git", "-C", str(project), "log", f"-n{limit}", "--pretty=format:%H%x09%an%x09%at%x09%s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return {"ok": True, "count": 0, "commits": [], "note": "git executable not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "git log timed out after 10s"}
    if proc.returncode != 0:
        return {"ok": True, "count": 0, "commits": [], "note": f"git log failed: {proc.stderr.strip()[:200]}"}

    commits: list[dict] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        sha, author, ts, subject = parts
        try:
            ts_int = int(ts)
        except ValueError:
            ts_int = 0
        commits.append(
            {
                "sha": sha[:12],
                "author": author,
                "timestamp": ts_int,
                "subject": subject,
            }
        )
    return {"ok": True, "count": len(commits), "commits": commits}


# ─── Convenience: list of all studio tool names (used by RoleConfig) ───

ALL_STUDIO_TOOL_NAMES: tuple[str, ...] = (
    # docs
    "studio_read_gdd",
    "studio_write_gdd",
    "studio_read_art_bible",
    "studio_write_art_bible",
    "studio_read_sprint",
    "studio_write_sprint",
    # backlog
    "studio_add_task",
    "studio_list_tasks",
    "studio_update_task_status",
    # decisions / milestones
    "studio_propose_decision",
    "studio_list_decisions",
    "studio_query_decisions",
    "studio_add_milestone",
    "studio_list_milestones",
    "studio_milestone_progress",
    # status
    "studio_get_summary",
    # references + screenshots
    "studio_list_references",
    "studio_list_screenshots",
    "studio_capture_screenshot",
    "studio_compare_to_reference",
    "studio_visual_regression_check",
    # recent activity
    "studio_recent_regressions",
    "studio_recent_commits",
    "studio_query_archive",
)
