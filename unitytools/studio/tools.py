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
_BLENDER: Any = None  # BlenderBridge or any object with .generate_prop()


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


def init_studio_blender(blender_bridge: Any) -> None:
    """Inject the Blender bridge used by `studio_generate_prop_asset`."""
    global _BLENDER
    _BLENDER = blender_bridge


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


@tool(description="Read the current Audio Brief (mood, palette, reference tracks, implementation rules).")
def studio_read_audio_brief() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.audio_brief)}


@tool(description="Replace the Audio Brief with new markdown. Owned by the Audio Director.")
def studio_write_audio_brief(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.audio_brief, content)
    return {"ok": True, "path": str(state.paths.audio_brief)}


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

@tool(description="Add a task to the backlog. role must be one of: producer, designer, art_director, level_designer, tech_artist, qa, critic. If milestone is set it must be the id of an existing milestone (use studio_list_milestones to find ids); use empty string to skip linking.")
def studio_add_task(title: str, role: str, description: str = "", milestone: str = "") -> dict:
    state = _require_state()
    if role not in ROLES:
        return {"ok": False, "error": f"Unknown role {role!r}. Allowed: {list(ROLES)}"}
    if milestone:
        valid_ids = {m.id for m in state.load_milestones()}
        if milestone not in valid_ids:
            return {
                "ok": False,
                "error": (
                    f"Unknown milestone id {milestone!r}. Either pass an id from "
                    f"studio_list_milestones, or leave milestone empty to skip linking. "
                    f"Do not invent milestone names -- the field is an id reference."
                ),
            }
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


@tool(description="List recent decisions (current state, deduped by id). Returns up to limit entries, newest first.")
def studio_list_decisions(limit: int = 50) -> dict:
    state = _require_state()
    from .decisions import latest_decisions

    rows = latest_decisions(state)
    rows.sort(key=lambda d: d.timestamp or 0.0, reverse=True)
    rows = rows[: max(1, int(limit or 50))]
    return {
        "ok": True,
        "count": len(rows),
        "decisions": [
            {
                "id": d.id,
                "title": d.title,
                "summary": d.summary,
                "status": d.status.value,
                "author_role": d.author_role,
                "timestamp": d.timestamp,
            }
            for d in rows
        ],
    }


@tool(description="Mark a decision accepted / rejected / superseded. Appends a new revision row with the same id; the original proposal stays in the log for audit. status must be one of: accepted, rejected, superseded. When status='superseded', pass superseded_by with the id of the replacement decision.")
def studio_ratify_decision(decision_id: str, status: str, superseded_by: str = "") -> dict:
    state = _require_state()
    from .decisions import find_decision, ratify_decision

    try:
        new_status = DecisionStatus(status)
    except ValueError:
        return {"ok": False, "error": f"Unknown status {status!r}. Use one of: accepted, rejected, superseded."}
    if new_status is DecisionStatus.PROPOSED:
        return {"ok": False, "error": "Cannot ratify back to 'proposed'; ratify to accepted, rejected, or superseded."}
    if new_status is DecisionStatus.SUPERSEDED and not superseded_by:
        return {"ok": False, "error": "status='superseded' requires superseded_by (id of replacement decision)."}

    target = find_decision(state, decision_id)
    if target is None:
        return {"ok": False, "error": f"Decision {decision_id!r} not found (or prefix is ambiguous)."}
    revised = ratify_decision(
        state,
        target.id,
        new_status,
        superseded_by=(superseded_by or None),
    )
    if revised is None:
        return {"ok": False, "error": f"Could not ratify {decision_id!r}."}
    return {
        "ok": True,
        "decision_id": revised.id,
        "new_status": revised.status.value,
        "superseded_by": revised.superseded_by,
        "previous_status": target.status.value,
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


# ─── Asset generation via Blender (Phase 25) ───────────────────────────

@tool(description="Generate a procedural prop (rock / crate / pillar / column) via Blender and save the FBX under studio/assets/generated/. Deterministic per seed: same prop_type+seed produces the same mesh, so re-runs converge. Optionally imports into Unity if import_into_unity=True and a Unity bridge is wired. Returns the FBX path so the Worker can chain unity_import_asset afterwards.")
def studio_generate_prop_asset(
    prop_type: str,
    name: str = "",
    seed: int = 0,
    scale: float = 1.0,
    import_into_unity: bool = False,
    unity_destination: str = "Assets/Studio/Generated",
) -> dict:
    state = _require_state()
    if _BLENDER is None:
        return {"ok": False, "error": "Blender bridge not injected. Run init_studio_blender(bridge) first."}
    if not _BLENDER.is_available():
        return {"ok": False, "error": "Blender executable not found; set BLENDER_EXECUTABLE in .env."}
    if not prop_type or prop_type not in ("rock", "crate", "pillar", "column"):
        return {"ok": False, "error": f"prop_type must be one of rock / crate / pillar / column; got {prop_type!r}."}

    # Name + output path
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or f"{prop_type}_{seed}")).strip("_")
    if not safe_name:
        safe_name = f"{prop_type}_{seed}"
    assets_dir = state.paths.root / "assets" / "generated"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_path = assets_dir / f"{safe_name}.fbx"

    result = _BLENDER.generate_prop(
        prop_type=prop_type,
        output_path=str(output_path),
        seed=seed,
        scale=scale,
    )
    if not result.success:
        return {
            "ok": False,
            "error": f"Blender generation failed (rc={result.return_code}): {result.stderr.strip()[:400]}",
            "stdout_tail": result.stdout.strip().splitlines()[-5:] if result.stdout else [],
        }
    if not output_path.exists():
        return {
            "ok": False,
            "error": f"Blender reported success but FBX not at {output_path}",
            "stdout_tail": result.stdout.strip().splitlines()[-5:] if result.stdout else [],
        }

    # Log to regression so the time series shows asset generation
    state.append_regression_entry(
        {
            "ts": time.time(),
            "kind": "asset_generated",
            "prop_type": prop_type,
            "name": safe_name,
            "seed": int(seed),
            "size_bytes": output_path.stat().st_size,
            "path": str(output_path),
        }
    )

    payload: dict = {
        "ok": True,
        "prop_type": prop_type,
        "name": safe_name,
        "seed": int(seed),
        "fbx_path": str(output_path),
        "size_bytes": output_path.stat().st_size,
    }

    # Optional Unity import as a convenience chain
    if import_into_unity:
        if _UNITY is None:
            payload["unity_import"] = {"ok": False, "error": "Unity bridge not injected."}
        elif hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
            payload["unity_import"] = {"ok": False, "error": "Unity Editor is not connected."}
        else:
            try:
                imp = _UNITY.call(
                    "import_asset",
                    {
                        "source_path": str(output_path),
                        "destination": unity_destination.rstrip("/"),
                        "replace_existing": True,
                    },
                    timeout=120,
                )
                payload["unity_import"] = imp if isinstance(imp, dict) else {"ok": True, "result": imp}
            except Exception as exc:  # noqa: BLE001
                payload["unity_import"] = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
    return payload


# ─── Physics QA / perf budget (Phase 24) ───────────────────────────────

@tool(description="Profile the active Unity scene and check it against per-metric budgets (triangles, renderers, shadow casters, unique materials, shadow-casting lights). Returns the raw profile, the budget verdict per metric, and a list of violations. Records a perf_budget row in qa/regression.jsonl for the time series. Pass 0 for any budget to disable that check.")
def studio_perf_budget_check(
    triangle_budget: int = 0,
    renderer_budget: int = 0,
    shadow_caster_budget: int = 0,
    unique_material_budget: int = 0,
    shadow_light_budget: int = 0,
    max_objects: int = 10000,
) -> dict:
    state = _require_state()
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}

    # Resolve "0 means defaults from StudioThresholds" so the role can call
    # without arguments and still get an opinionated budget.
    th = state.thresholds
    triangle_budget = triangle_budget or th.perf_triangle_budget
    renderer_budget = renderer_budget or th.perf_renderer_budget
    shadow_caster_budget = shadow_caster_budget or th.perf_shadow_caster_budget
    unique_material_budget = unique_material_budget or th.perf_unique_material_budget
    shadow_light_budget = shadow_light_budget or th.perf_shadow_light_budget

    try:
        raw = _UNITY.call(
            "profile_scene_performance",
            {"max_objects": int(max_objects)},
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"profile_scene_performance failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(raw, dict):
        return {"ok": False, "error": "Unexpected response shape from profile_scene_performance."}

    # Extract metrics defensively (Unity-side may evolve fields).
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    triangles = _to_int(raw.get("triangles"))
    renderers = _to_int(raw.get("renderers"))
    shadow_casters = _to_int(raw.get("shadow_casters"))
    unique_materials = _to_int(raw.get("unique_materials"))
    # shadow_light_budget compares against count of lights whose .shadows != None;
    # the Unity profiler exposes this as nested data, but a useful proxy is the
    # total `lights` count when the profile doesn't break it out. The C# handler
    # already filters internally for the "shadow-casting lights" suggestion;
    # we approximate by reading `lights`.
    shadow_lights = _to_int(raw.get("shadow_lights", raw.get("lights")))

    checks = [
        ("triangles", triangles, triangle_budget),
        ("renderers", renderers, renderer_budget),
        ("shadow_casters", shadow_casters, shadow_caster_budget),
        ("unique_materials", unique_materials, unique_material_budget),
        ("shadow_lights", shadow_lights, shadow_light_budget),
    ]
    violations: list[dict] = []
    breakdown: list[dict] = []
    for name, actual, budget in checks:
        over = actual > budget
        entry = {
            "metric": name,
            "actual": actual,
            "budget": budget,
            "over_budget": over,
            "over_by": max(0, actual - budget),
        }
        breakdown.append(entry)
        if over:
            violations.append(entry)

    state.append_regression_entry(
        {
            "ts": time.time(),
            "kind": "perf_budget",
            "ok": not violations,
            "violations": [v["metric"] for v in violations],
            "triangles": triangles,
            "renderers": renderers,
            "unique_materials": unique_materials,
        }
    )

    return {
        "ok": not violations,
        "violation_count": len(violations),
        "violations": violations,
        "breakdown": breakdown,
        "suggestions": raw.get("suggestions", []),
        "raw": {
            "sampled_objects": raw.get("sampled_objects"),
            "total_scene_objects": raw.get("total_scene_objects"),
            "renderers": renderers,
            "triangles": triangles,
            "shadow_casters": shadow_casters,
            "unique_materials": unique_materials,
            "lights": _to_int(raw.get("lights")),
        },
    }


# ─── Playtest (Phase 23) ───────────────────────────────────────────────

@tool(description="Run a smoke playtest: enter Unity play mode, wait `duration_seconds` (capped 0.5..30), check that each name in expected_object_names still exists in the scene, capture a play-mode screenshot, then exit play mode. Returns a structured report. Records a playtest_smoke row in qa/regression.jsonl for the time series.")
def studio_playtest_smoke(
    duration_seconds: float = 3.0,
    expected_object_names: Optional[list[str]] = None,
    capture_name: str = "playtest",
) -> dict:
    state = _require_state()
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}

    # Cap duration so a confused agent can't lock Unity for an hour.
    duration = max(0.5, min(30.0, float(duration_seconds)))
    expected = list(expected_object_names or [])
    started_at = time.time()
    entered = False
    errors: list[str] = []

    # 1. Enter play mode
    try:
        enter_result = _UNITY.call("play_mode", {"play": True}, timeout=15)
        entered = True
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"Could not enter play mode: {exc}",
            "error_type": type(exc).__name__,
        }

    presence: dict[str, bool] = {}
    screenshot_path: Optional[str] = None
    try:
        # 2. Hold the smoke for the requested window
        time.sleep(duration)

        # 3. Verify each expected object survived play-mode entry
        for name in expected:
            try:
                find_result = _UNITY.call(
                    "find_scene_objects",
                    {"name_contains": name, "max_count": 1},
                    timeout=10,
                )
                objs = find_result.get("objects", []) if isinstance(find_result, dict) else []
                presence[name] = len(objs) > 0
            except Exception as exc:  # noqa: BLE001
                presence[name] = False
                errors.append(f"verify {name}: {exc}")

        # 4. Capture a screenshot for the QA log (best-effort)
        try:
            qa = _UNITY.call("run_visual_qa", {"capture_screenshot": True}, timeout=30)
            raw_path = (qa or {}).get("screenshot_path") if isinstance(qa, dict) else None
            if raw_path:
                src = Path(raw_path)
                if src.exists():
                    state.paths.qa_screenshots.mkdir(parents=True, exist_ok=True)
                    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (capture_name or "playtest"))
                    dest = state.paths.qa_screenshots / f"{time.strftime('%Y%m%d_%H%M%S')}_{safe}{src.suffix or '.png'}"
                    shutil.copy2(src, dest)
                    screenshot_path = str(dest)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"capture: {exc}")
    finally:
        # 5. ALWAYS exit play mode, even if a verification step raised.
        if entered:
            try:
                _UNITY.call("play_mode", {"play": False}, timeout=15)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"exit play mode: {exc}")

    finished_at = time.time()
    missing = [n for n, present in presence.items() if not present]
    ok = (not errors) and (not missing)

    payload = {
        "ok": ok,
        "duration_seconds": duration,
        "elapsed_seconds": finished_at - started_at,
        "expected_count": len(expected),
        "missing": missing,
        "presence": presence,
        "screenshot": screenshot_path,
        "errors": errors,
    }
    # Append to the regression time series so studio_recent_regressions
    # surfaces playtest results alongside vision / pixel diffs.
    state.append_regression_entry(
        {
            "ts": finished_at,
            "kind": "playtest_smoke",
            "ok": ok,
            "missing_count": len(missing),
            "errors_count": len(errors),
            "duration": duration,
        }
    )
    return payload


# ─── Blockout helpers (Phase 22) ───────────────────────────────────────

@tool(description="Create a group of primitives in a layout pattern (line/grid/circle/cluster) at one origin. Saves the Worker from making N separate unity_create_primitive + unity_set_position calls. Returns the list of created object names. layout: 'line' (along x-axis), 'grid' (NxN on xz-plane), 'circle' (ring on xz-plane around origin), 'cluster' (random scatter within a radius).")
def studio_create_blockout_group(
    name_prefix: str,
    primitive_type: str = "Cube",
    count: int = 4,
    layout: str = "line",
    spacing: float = 2.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    origin_z: float = 0.0,
    color_r: float = 0.7,
    color_g: float = 0.7,
    color_b: float = 0.7,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    if count < 1:
        return {"ok": False, "error": "count must be >= 1."}
    if count > 50:
        return {"ok": False, "error": "count is capped at 50 for blockouts; use a procedural tool for larger sets."}
    if layout not in ("line", "grid", "circle", "cluster"):
        return {"ok": False, "error": f"Unknown layout {layout!r}. Use line / grid / circle / cluster."}
    if primitive_type not in ("Cube", "Sphere", "Cylinder", "Capsule", "Plane", "Quad"):
        return {"ok": False, "error": f"Unknown primitive_type {primitive_type!r}."}

    # Compute positions per layout
    positions: list[tuple[float, float, float]] = []
    if layout == "line":
        # Centered along x-axis
        for i in range(count):
            x = origin_x + (i - (count - 1) / 2.0) * spacing
            positions.append((x, origin_y, origin_z))
    elif layout == "grid":
        # NxN grid; round-up the side length
        side = int(count ** 0.5)
        if side * side < count:
            side += 1
        for i in range(count):
            row, col = divmod(i, side)
            x = origin_x + (col - (side - 1) / 2.0) * spacing
            z = origin_z + (row - (side - 1) / 2.0) * spacing
            positions.append((x, origin_y, z))
    elif layout == "circle":
        import math
        for i in range(count):
            angle = 2 * math.pi * i / count
            x = origin_x + spacing * math.cos(angle)
            z = origin_z + spacing * math.sin(angle)
            positions.append((x, origin_y, z))
    elif layout == "cluster":
        # Deterministic pseudo-random scatter (seeded with name_prefix hash)
        import random
        rng = random.Random(hash(name_prefix) & 0xFFFFFFFF)
        for _ in range(count):
            x = origin_x + (rng.random() - 0.5) * 2 * spacing
            z = origin_z + (rng.random() - 0.5) * 2 * spacing
            positions.append((x, origin_y, z))

    created: list[dict] = []
    errors: list[str] = []
    for i, (x, y, z) in enumerate(positions):
        name = f"{name_prefix}_{i:02d}"
        try:
            _UNITY.call(
                "create_primitive",
                {"type": primitive_type, "name": name, "position": {"x": x, "y": y, "z": z}},
            )
            # Apply color
            try:
                _UNITY.call(
                    "set_material_color",
                    {"name": name, "color": {"r": color_r, "g": color_g, "b": color_b, "a": 1.0}},
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"color {name}: {exc}")
            created.append({"name": name, "position": {"x": x, "y": y, "z": z}})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"create {name}: {exc}")
    return {
        "ok": bool(created),
        "count": len(created),
        "layout": layout,
        "primitive_type": primitive_type,
        "objects": created,
        "errors": errors,
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
    "studio_read_audio_brief",
    "studio_write_audio_brief",
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
    "studio_ratify_decision",
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
    "studio_create_blockout_group",
    "studio_playtest_smoke",
    "studio_perf_budget_check",
    "studio_generate_prop_asset",
    # recent activity
    "studio_recent_regressions",
    "studio_recent_commits",
    "studio_query_archive",
)
