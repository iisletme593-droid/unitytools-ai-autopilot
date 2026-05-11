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


# ─── Audio engine integration (Phase 27) ───────────────────────────────

@tool(description="Import an audio file (wav/mp3/ogg) into Unity at the given destination folder. The file is copied through Unity's import pipeline so it becomes a real AudioClip asset. Returns the imported asset path. Best paired with studio_unity_attach_audio_source afterwards.")
def studio_unity_import_audio(source_path: str, unity_destination: str = "Assets/Studio/Audio") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    src = Path(source_path)
    if not src.exists():
        return {"ok": False, "error": f"Audio source not found: {src}"}
    suffix = src.suffix.lower()
    if suffix not in (".wav", ".mp3", ".ogg", ".aiff", ".flac"):
        return {"ok": False, "error": f"Unsupported audio extension {suffix!r}; use wav/mp3/ogg/aiff/flac."}
    destination = unity_destination.rstrip("/")
    try:
        result = _UNITY.call(
            "import_asset",
            {
                "source_path": str(src),
                "destination": destination,
                "replace_existing": True,
            },
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Unity import_asset failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(result, dict) or not result.get("ok", True):
        return {"ok": False, "error": "Unity reported import_asset failure.", "raw": result}
    imported_paths = result.get("imported_object_paths") or []
    return {
        "ok": True,
        "source": str(src),
        "destination": destination,
        "imported_paths": imported_paths,
        "raw": result,
    }


@tool(description="Attach (or update) an AudioSource component on a named scene object. Sets clip (Unity asset path), loop, play_on_awake, volume (0..1), pitch, spatial_blend (0=2D, 1=3D), min/max distance. Any property left as default is not modified. Object must exist; clip_path must point to an imported AudioClip asset.")
def studio_unity_attach_audio_source(
    target_name: str,
    clip_path: str = "",
    loop: bool = False,
    play_on_awake: bool = True,
    volume: float = 1.0,
    pitch: float = 1.0,
    spatial_blend: float = 0.0,
    min_distance: float = 1.0,
    max_distance: float = 500.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    if not target_name:
        return {"ok": False, "error": "target_name is required."}
    if not 0.0 <= volume <= 1.0:
        return {"ok": False, "error": "volume must be in 0..1."}
    if not 0.0 <= spatial_blend <= 1.0:
        return {"ok": False, "error": "spatial_blend must be in 0..1 (0=2D, 1=3D)."}
    params: dict[str, Any] = {
        "name": target_name,
        "loop": bool(loop),
        "play_on_awake": bool(play_on_awake),
        "volume": float(volume),
        "pitch": float(pitch),
        "spatial_blend": float(spatial_blend),
        "min_distance": float(min_distance),
        "max_distance": float(max_distance),
    }
    if clip_path:
        params["clip_path"] = clip_path
    try:
        result = _UNITY.call("set_audio_source", params, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"set_audio_source failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(result, dict) or not result.get("ok", True):
        return {"ok": False, "error": "Unity reported set_audio_source failure.", "raw": result}
    return {"ok": True, "target": target_name, **{k: v for k, v in result.items() if k != "ok"}}


# ─── Cost observability (Phase 33) ─────────────────────────────────────

@tool(description="Summarise the studio's LLM cost log (studio/qa/cost_log.jsonl). days=1 by default (last 24h); days=0 means 'all time'. Returns total tokens + cost USD plus breakdowns by role, model, and day. Free for local Ollama models; priced for Anthropic Claude.")
def studio_cost_summary(days: int = 1) -> dict:
    state = _require_state()
    from .cost import summarise
    return summarise(state, days=days)


# ─── Build preflight (Phase 32) ────────────────────────────────────────

@tool(description="Preflight a build: verify the project has at least one scene in EditorBuildSettings, the GDD is non-empty (or the user explicitly waived it), and the last perf budget check (if any) didn't fail catastrophically. Returns verdict + violations. No mutations — call this before unity_build_player.")
def studio_build_check(require_gdd: bool = True, require_art_bible: bool = False) -> dict:
    state = _require_state()
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}

    violations: list[str] = []
    recommendations: list[str] = []

    # Scenes
    try:
        scenes_info = _UNITY.call("list_build_scenes", {}, timeout=15)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"list_build_scenes failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(scenes_info, dict):
        return {"ok": False, "error": "Unity returned non-dict from list_build_scenes.", "raw": scenes_info}
    enabled = int(scenes_info.get("enabled_count", 0))
    if enabled == 0:
        violations.append("no_enabled_scenes")
        recommendations.append(
            "EditorBuildSettings has zero enabled scenes; add one via "
            "unity_add_scene_to_build(scene_path='Assets/Scenes/Main.unity')."
        )

    # GDD presence + non-empty
    if require_gdd:
        gdd_path = state.paths.gdd
        if not gdd_path.exists() or not gdd_path.read_text(encoding="utf-8").strip():
            violations.append("gdd_empty_or_missing")
            recommendations.append(
                "GDD is empty or missing; open a designer task to draft it before shipping."
            )
    if require_art_bible:
        ab_path = state.paths.art_bible
        if not ab_path.exists() or not ab_path.read_text(encoding="utf-8").strip():
            violations.append("art_bible_empty_or_missing")
            recommendations.append(
                "Art Bible is empty or missing; open an art_director task to draft it."
            )

    verdict = "pass" if not violations else "fail"
    return {
        "ok": True,
        "verdict": verdict,
        "enabled_scenes": enabled,
        "total_scenes": int(scenes_info.get("count", 0)),
        "active_target": scenes_info.get("active_target"),
        "violations": violations,
        "recommendations": recommendations,
    }


# ─── VFX audit (Phase 30) ──────────────────────────────────────────────

@tool(description="Audit the scene's particle systems against soft budgets: at most max_systems active particle systems, total emission_rate under max_total_emission, total max_particles under max_total_particles. Returns verdict + violations + recommendations. No mutations.")
def studio_vfx_audit(
    max_systems: int = 12,
    max_total_emission: float = 400.0,
    max_total_particles: int = 8000,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    try:
        result = _UNITY.call("list_particle_systems", {}, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"list_particle_systems failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(result, dict):
        return {"ok": False, "error": "Unity returned non-dict from list_particle_systems.", "raw": result}

    systems = result.get("systems", []) or []
    count = int(result.get("count", len(systems)))
    total_emission = float(result.get("total_emission_rate", 0.0))
    total_max = int(result.get("total_max_particles", 0))

    violations: list[str] = []
    recommendations: list[str] = []
    if count > max_systems:
        violations.append(f"too_many_systems:{count}>{max_systems}")
        recommendations.append(
            f"{count} active particle systems exceed budget {max_systems}; "
            "merge ambient systems or disable distant ones to drop the count."
        )
    if total_emission > max_total_emission:
        violations.append(f"emission_over_budget:{total_emission:.1f}>{max_total_emission}")
        # Find the loudest 1-2 systems and name them.
        loud = sorted(systems, key=lambda s: float(s.get("emission_rate", 0.0)), reverse=True)[:2]
        names = ", ".join(s.get("name", "?") for s in loud) or "—"
        recommendations.append(
            f"Scene emission rate {total_emission:.1f}/s over budget {max_total_emission}/s; "
            f"halve emission_rate on the top offenders ({names}) via unity_set_particle_properties."
        )
    if total_max > max_total_particles:
        violations.append(f"max_particles_over_budget:{total_max}>{max_total_particles}")
        recommendations.append(
            f"Total max_particles {total_max} exceeds budget {max_total_particles}; "
            "reduce max_particles on the largest systems via unity_set_particle_properties."
        )

    verdict = "pass" if not violations else "fail"
    return {
        "ok": True,
        "verdict": verdict,
        "count": count,
        "total_emission_rate": total_emission,
        "total_max_particles": total_max,
        "violations": violations,
        "recommendations": recommendations,
        "systems": systems,
    }


# ─── Camera framing audit (Phase 29) ───────────────────────────────────

@tool(description="Frame the named target object with the main (or named) camera, capture a screenshot, and optionally compare against a reference image. Returns the screenshot path, the camera placement, and (if reference_path given) the composition_match score. The Camera Director uses this to verify a frame before saving.")
def studio_camera_frame_check(
    target_name: str,
    label: str = "frame",
    camera_name: str = "",
    distance: float = 0.0,
    yaw_degrees: float = -30.0,
    pitch_degrees: float = 20.0,
    reference_path: str = "",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    if not target_name:
        return {"ok": False, "error": "target_name is required."}
    state = _require_state()

    # 1. Frame the target.
    frame_params: dict[str, Any] = {
        "target_name": target_name,
        "camera_name": camera_name,
        "yaw_degrees": yaw_degrees,
        "pitch_degrees": pitch_degrees,
    }
    if distance > 0:
        frame_params["distance"] = distance
    try:
        frame_result = _UNITY.call("frame_object", frame_params, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"frame_object failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(frame_result, dict) or not frame_result.get("ok", True):
        return {"ok": False, "error": "Unity reported frame_object failure.", "raw": frame_result}

    # 2. Capture from that frame (same path studio_capture_screenshot uses).
    try:
        capture_result = _UNITY.call("run_visual_qa", {"capture_screenshot": True}, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"run_visual_qa failed: {exc}",
            "error_type": type(exc).__name__,
            "frame": frame_result,
        }
    raw_path = ""
    if isinstance(capture_result, dict):
        raw_path = capture_result.get("screenshot_path") or capture_result.get("path") or ""
    if not raw_path:
        return {
            "ok": False,
            "error": "Unity did not return a screenshot path.",
            "frame": frame_result,
            "raw": capture_result,
        }
    src = Path(raw_path)
    if not src.exists():
        return {
            "ok": False,
            "error": f"Screenshot file does not exist: {src}",
            "frame": frame_result,
        }

    # Copy the captured shot under studio/qa/screenshots/ with the chosen label.
    state.paths.qa_screenshots.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label).strip("_") or "frame"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = state.paths.qa_screenshots / f"{timestamp}_{safe_label}_{target_name}{src.suffix or '.png'}"
    try:
        shutil.copy2(src, screenshot_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"failed to copy screenshot to studio/qa/screenshots/: {exc}",
            "frame": frame_result,
        }

    out: dict[str, Any] = {
        "ok": True,
        "target": target_name,
        "screenshot": str(screenshot_path),
        "frame": frame_result,
    }

    # 3. Optional reference comparison.
    if reference_path:
        if _VISION is None:
            out["compare"] = {"ok": False, "error": "Vision client not injected."}
        else:
            ref = Path(reference_path)
            if not ref.exists():
                out["compare"] = {"ok": False, "error": f"reference not found: {ref}"}
            else:
                try:
                    diff = _VISION.compare(
                        reference_bytes=ref.read_bytes(),
                        reference_mime=guess_mime(ref),
                        candidate_bytes=screenshot_path.read_bytes(),
                        candidate_mime=guess_mime(screenshot_path),
                        instruction=f"Camera frame check for target '{target_name}'.",
                    )
                    out["compare"] = {"ok": True, **(diff if isinstance(diff, dict) else {})}
                except Exception as exc:  # noqa: BLE001
                    out["compare"] = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}

    return out


# ─── Lighting audit (Phase 28) ─────────────────────────────────────────

@tool(description="Audit the scene's lighting setup. Calls list_lights on the Unity bridge, then verdicts against soft budgets: at least 1 directional light, no more than 8 shadow-casting lights, total intensity below 50. Returns a 'verdict' string + 'recommendations' list the Lighting Director can act on. No mutations.")
def studio_lighting_audit(
    max_shadow_casters: int = 8,
    max_total_intensity: float = 50.0,
    require_directional: bool = True,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    try:
        result = _UNITY.call("list_lights", {}, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"list_lights failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(result, dict):
        return {"ok": False, "error": "Unity returned non-dict from list_lights.", "raw": result}
    lights = result.get("lights", []) or []
    count = int(result.get("count", len(lights)))
    total_intensity = float(result.get("total_intensity", 0.0))
    shadow_count = int(result.get("shadow_casting_count", 0))
    has_directional = any(
        str(l.get("light_type", "")).lower() == "directional"
        for l in lights
    )

    violations: list[str] = []
    recommendations: list[str] = []
    if require_directional and not has_directional:
        violations.append("no_directional_light")
        recommendations.append(
            "Add a Directional light: unity_create_light(name='SunLight', "
            "light_type='Directional', intensity=1.0). Most outdoor scenes need one."
        )
    if shadow_count > max_shadow_casters:
        violations.append(f"shadow_casters_over_budget:{shadow_count}>{max_shadow_casters}")
        recommendations.append(
            f"{shadow_count} lights cast shadows (budget {max_shadow_casters}); "
            "disable shadows on the smallest / most distant lights via "
            "unity_set_light_properties(name=..., shadows_enabled=0)."
        )
    if total_intensity > max_total_intensity:
        violations.append(f"total_intensity_over_budget:{total_intensity:.1f}>{max_total_intensity}")
        recommendations.append(
            f"Scene total intensity is {total_intensity:.1f} (budget {max_total_intensity}); "
            "halve the intensity on the brightest lights before adding more."
        )
    if count == 0:
        violations.append("scene_has_no_lights")
        recommendations.append(
            "Scene has zero Light components. Add at least one directional light "
            "plus ambient via unity_set_ambient_light(r=0.3, g=0.3, b=0.35, intensity=1.0)."
        )

    verdict = "pass" if not violations else "fail"
    return {
        "ok": True,
        "verdict": verdict,
        "count": count,
        "total_intensity": total_intensity,
        "shadow_casting_count": shadow_count,
        "has_directional": has_directional,
        "ambient_intensity": result.get("ambient_intensity"),
        "ambient_mode": result.get("ambient_mode"),
        "violations": violations,
        "recommendations": recommendations,
        "lights": lights,
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
    # audio engine (Phase 27)
    "studio_unity_import_audio",
    "studio_unity_attach_audio_source",
    # lighting (Phase 28)
    "studio_lighting_audit",
    # camera framing (Phase 29)
    "studio_camera_frame_check",
    # vfx (Phase 30)
    "studio_vfx_audit",
    # build pipeline (Phase 32)
    "studio_build_check",
    # cost observability (Phase 33)
    "studio_cost_summary",
    # recent activity
    "studio_recent_regressions",
    "studio_recent_commits",
    "studio_query_archive",
)
