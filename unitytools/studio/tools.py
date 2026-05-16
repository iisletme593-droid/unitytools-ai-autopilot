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
import re
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


@tool(description="Read the press kit markdown (title, tagline, description, features, hero shots, credits, links, build targets). Empty string if absent.")
def studio_read_press_kit() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.press_kit)}


@tool(description="Replace the press kit markdown. Owned by the Marketing Director. Must include at minimum: Game Title, Tagline, Description, and hero shot references.")
def studio_write_press_kit(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.press_kit, content)
    return {"ok": True, "path": str(state.paths.press_kit)}


@tool(description="Read the tutorial / onboarding markdown — player goal, controls, the 3-5 beat first-60-seconds flow, UI surface, skip path. Empty string if absent.")
def studio_read_tutorial() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.tutorial)}


@tool(description="Replace the tutorial / onboarding markdown. Owned by the Tutorial Designer. Must include at minimum: Player Goal, Controls, and 3+ beats describing the first 60 seconds of play.")
def studio_write_tutorial(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.tutorial, content)
    return {"ok": True, "path": str(state.paths.tutorial)}


@tool(description="Read the scene catalog markdown — the scene-graph of the game (Title / Game / Win / GameOver / Credits / ...), the allowed transitions between them, the build-settings checklist, and any persistent state. Empty string if absent.")
def studio_read_scene_catalog() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.scene_catalog)}


@tool(description="Replace the scene catalog markdown. Owned by the Scene Director. Must include at minimum: a Scenes table (path + role + loaded-by), a Transitions list, and a Build Settings checklist that the Build Engineer can act on.")
def studio_write_scene_catalog(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.scene_catalog, content)
    return {"ok": True, "path": str(state.paths.scene_catalog)}


@tool(description="Read the achievements markdown — the roster of unlocks (key + trigger kind + threshold + display message). Empty string if absent.")
def studio_read_achievements() -> dict:
    state = _require_state()
    return {"ok": True, "content": state.read_doc(state.paths.achievements)}


@tool(description="Replace the achievements markdown. Owned by the Achievement Designer. Each entry must list: achievementKey (PlayerPrefs slug), trigger kind from {ScoreAtLeast, LivesRemainingAtMost, GameOver}, threshold (int; ignored for GameOver), and a one-line unlock message.")
def studio_write_achievements(content: str) -> dict:
    state = _require_state()
    state.write_doc(state.paths.achievements, content)
    return {"ok": True, "path": str(state.paths.achievements)}


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


@tool(description="Phase 70: Explain a task's full status — current state, blockers list, and dependency readiness (which deps are done vs. still pending). Used by /why <task-id> for the 'why can't I work on this' diagnostic. Pass the full task id (use studio_list_tasks to find one).")
def studio_explain_task(task_id: str) -> dict:
    state = _require_state()
    all_tasks = state.load_tasks()
    target = next((t for t in all_tasks if t.id == task_id), None)
    if target is None:
        return {"ok": False, "error": f"Task {task_id!r} not found."}

    # Walk deps and tell the operator which are done vs. still open.
    by_id = {t.id: t for t in all_tasks}
    dep_status: list[dict] = []
    for dep_id in (target.depends_on or []):
        dep_task = by_id.get(dep_id)
        if dep_task is None:
            dep_status.append({
                "id": dep_id,
                "title": "(unknown — task not in backlog)",
                "status": "missing",
                "satisfied": False,
            })
        else:
            satisfied = dep_task.status is TaskStatus.DONE
            dep_status.append({
                "id": dep_task.id,
                "title": dep_task.title,
                "status": dep_task.status.value,
                "satisfied": satisfied,
            })

    unsatisfied = [d for d in dep_status if not d["satisfied"]]
    return {
        "ok": True,
        "task_id": target.id,
        "title": target.title,
        "role": target.role,
        "status": target.status.value,
        "description": target.description,
        "milestone": target.milestone,
        "blockers": list(target.blockers or []),
        "depends_on": dep_status,
        "unsatisfied_dep_count": len(unsatisfied),
        "ready_to_start": (
            target.status is TaskStatus.PENDING and not unsatisfied
            and not (target.blockers or [])
        ),
    }


@tool(description="Phase 70: Append a free-text blocker note to a task and flip its status to 'blocked'. The reason is stored in the task's blockers list. Idempotent: if status is already blocked the reason is just appended.")
def studio_block_task(task_id: str, reason: str = "") -> dict:
    state = _require_state()
    tasks = state.load_tasks()
    for t in tasks:
        if t.id == task_id:
            if reason and reason.strip():
                t.blockers = list(t.blockers or []) + [reason.strip()]
            t.status = TaskStatus.BLOCKED
            state.update_task(t)
            return {
                "ok": True,
                "task_id": t.id,
                "status": t.status.value,
                "blockers": list(t.blockers or []),
            }
    return {"ok": False, "error": f"Task {task_id!r} not found."}


@tool(description="Phase 79: Stage every change and create a git commit at the studio root. Runs `git add -A` then `git commit -m <message>`. Returns the new commit's short sha + summary, or ok=False with the git error output. The studio must be inside a git repo; not-a-repo and nothing-to-commit cases return clean errors. Refuses empty messages.")
def studio_commit(message: str) -> dict:
    import subprocess
    state = _require_state()
    msg = (message or "").strip()
    if not msg:
        return {"ok": False, "error": "commit message is empty"}

    cwd = state.paths.root.parent  # studio sits at <project>/studio
    # Sanity: is this a git repo?
    check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    if check.returncode != 0:
        return {
            "ok": False,
            "error": (
                "not inside a git repo. Run `git init` at the project root "
                "before /commit."
            ),
        }

    # Stage everything (matches our README/CONTRIBUTING pattern: studios
    # are small enough that -A is the right default).
    add = subprocess.run(
        ["git", "add", "-A"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    if add.returncode != 0:
        return {
            "ok": False,
            "error": f"git add failed: {add.stderr.strip() or add.stdout.strip()}",
        }

    # Commit. Will fail with returncode=1 if nothing's staged.
    commit = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    if commit.returncode != 0:
        # Distinguish "nothing to commit" from real failures
        combined = (commit.stdout + commit.stderr).lower()
        if "nothing to commit" in combined or "no changes added" in combined:
            return {
                "ok": False,
                "error": "nothing to commit — working tree clean",
                "git_output": commit.stdout.strip(),
            }
        return {
            "ok": False,
            "error": f"git commit failed: {commit.stderr.strip() or commit.stdout.strip()}",
        }

    # Grab the new commit's short sha
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    short_sha = sha.stdout.strip() if sha.returncode == 0 else "?"

    return {
        "ok": True,
        "sha": short_sha,
        "message": msg,
        "git_output": commit.stdout.strip(),
    }


@tool(description="Phase 76: Per-milestone burndown — % complete and a 20-char ASCII bar chart for each milestone. Optional milestone_id narrows to one. Always also returns a project-wide rollup (all tasks across the backlog, including those not linked to any milestone) so the operator can sanity-check the milestone numbers against total backlog state.")
def studio_burndown(milestone_id: str = "") -> dict:
    state = _require_state()
    from .milestones import milestone_progress

    def _bar(pct: float, width: int = 20) -> str:
        pct = max(0.0, min(1.0, pct))
        filled = int(round(pct * width))
        return "[" + ("#" * filled) + ("-" * (width - filled)) + f"] {int(pct * 100)}%"

    # Project-wide rollup — every task in the backlog
    all_tasks = state.load_tasks()
    total = len(all_tasks)
    from collections import Counter
    proj_counts = Counter(t.status.value for t in all_tasks)
    proj_done = proj_counts.get("done", 0)
    proj_pct = (proj_done / total) if total else 0.0
    project = {
        "task_count": total,
        "done_count": proj_done,
        "in_progress_count": proj_counts.get("in_progress", 0),
        "blocked_count": proj_counts.get("blocked", 0),
        "pending_count": proj_counts.get("pending", 0),
        "review_count": proj_counts.get("review", 0),
        "completion_pct": round(proj_pct, 4),
        "bar": _bar(proj_pct),
    }

    # Per-milestone breakdown
    milestones = state.load_milestones()
    if milestone_id:
        # Filter to one
        milestones = [m for m in milestones if m.id == milestone_id]
        if not milestones:
            return {
                "ok": False,
                "error": f"Milestone {milestone_id!r} not found.",
            }

    milestone_rows: list[dict] = []
    for m in milestones:
        progress = milestone_progress(state, m.id)
        if progress is None:
            continue
        pct = float(progress.get("completion_pct", 0.0))
        milestone_rows.append({
            **progress,
            "bar": _bar(pct),
        })

    # Sort by ascending completion so the operator sees what's farthest
    # from shipping first (most useful for a producer scan).
    milestone_rows.sort(key=lambda r: r.get("completion_pct", 0.0))

    return {
        "ok": True,
        "milestone_id": milestone_id or None,
        "project": project,
        "milestones": milestone_rows,
        "milestone_count": len(milestone_rows),
    }


@tool(description="Phase 75: Search across every text surface of the studio — tasks (title + description), decisions (title + summary + rationale), milestones, GDD, Art Bible, Audio Brief, Tutorial, Scene Catalog, Press Kit, Achievements, current sprint plan, and journal entries. Substring match, case-insensitive. Returns hits grouped by source plus a flat 'all_hits' list ranked by source priority (tasks first, then decisions, then docs, then journal). Optional max_per_source caps each bucket so large studios don't blow past payload limits.")
def studio_find(needle: str, max_per_source: int = 10) -> dict:
    state = _require_state()
    n = (needle or "").strip().lower()
    if not n:
        return {"ok": False, "error": "needle is empty"}
    if max_per_source <= 0:
        return {"ok": False, "error": "max_per_source must be positive"}

    def _excerpt(text: str, max_len: int = 120) -> str:
        """Show a snippet centred on the first occurrence of the needle,
        so the operator sees context rather than the head of the file."""
        if not text:
            return ""
        idx = text.lower().find(n)
        if idx < 0:
            return text[:max_len]
        start = max(0, idx - 30)
        end = min(len(text), idx + len(n) + 60)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{text[start:end].strip()}{suffix}"

    # ── Tasks
    task_hits: list[dict] = []
    for t in state.load_tasks():
        hay = f"{t.title}\n{t.description or ''}".lower()
        if n in hay:
            task_hits.append({
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "status": t.status.value,
                "milestone": t.milestone,
                "excerpt": _excerpt(t.description or t.title),
            })
        if len(task_hits) >= max_per_source:
            break

    # ── Decisions
    decision_hits: list[dict] = []
    for d in state.load_decisions():
        hay = f"{d.title}\n{d.summary}\n{d.rationale or ''}".lower()
        if n in hay:
            decision_hits.append({
                "id": d.id,
                "title": d.title,
                "status": d.status.value,
                "author_role": d.author_role,
                "excerpt": _excerpt(f"{d.summary} {d.rationale}".strip()),
            })
        if len(decision_hits) >= max_per_source:
            break

    # ── Milestones
    milestone_hits: list[dict] = []
    for m in state.load_milestones():
        hay = f"{m.name}\n{m.description or ''}".lower()
        if n in hay:
            milestone_hits.append({
                "id": m.id,
                "name": m.name,
                "excerpt": _excerpt(m.description or m.name),
            })
        if len(milestone_hits) >= max_per_source:
            break

    # ── Docs (GDD / Art Bible / Audio Brief / ...)
    doc_paths = [
        ("gdd", state.paths.gdd),
        ("art_bible", state.paths.art_bible),
        ("audio_brief", state.paths.audio_brief),
        ("press_kit", state.paths.press_kit),
        ("tutorial", state.paths.tutorial),
        ("scene_catalog", state.paths.scene_catalog),
        ("achievements", state.paths.achievements),
        ("sprint_current", state.paths.sprint_current),
    ]
    doc_hits: list[dict] = []
    for label, path in doc_paths:
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if n in content.lower():
            doc_hits.append({
                "doc": label,
                "path": str(path),
                "excerpt": _excerpt(content),
            })
        if len(doc_hits) >= max_per_source:
            break

    # ── Journal entries (last 30 days)
    import time
    journal_hits: list[dict] = []
    today_ts = time.time()
    if state.paths.journal.is_dir():
        for offset in range(30):
            day_ts = today_ts - offset * 86400
            date_iso = time.strftime("%Y-%m-%d", time.localtime(day_ts))
            jpath = state.paths.journal_for_date(date_iso)
            if not jpath.is_file():
                continue
            try:
                content = jpath.read_text(encoding="utf-8")
            except Exception:
                continue
            if n in content.lower():
                journal_hits.append({
                    "date": date_iso,
                    "path": str(jpath),
                    "excerpt": _excerpt(content),
                })
            if len(journal_hits) >= max_per_source:
                break

    # Flat ranked stream — tasks first (most actionable), then decisions,
    # docs, milestones, journal.
    all_hits: list[dict] = []
    for src_label, bucket in (
        ("task", task_hits),
        ("decision", decision_hits),
        ("doc", doc_hits),
        ("milestone", milestone_hits),
        ("journal", journal_hits),
    ):
        for hit in bucket:
            all_hits.append({"source": src_label, **hit})

    return {
        "ok": True,
        "needle": n,
        "tasks": task_hits,
        "decisions": decision_hits,
        "milestones": milestone_hits,
        "docs": doc_hits,
        "journal": journal_hits,
        "all_hits": all_hits,
        "total_hits": len(all_hits),
    }


@tool(description="Phase 72: Append a free-text journal entry to today's studio/memory/journal/<YYYY-MM-DD>.md file. Each entry is timestamped (HH:MM:SS) so the daily log builds a chronological record. Used by the /log slash command for the operator's personal notes — kept separate from tasks, decisions, and reviews.")
def studio_journal_append(message: str) -> dict:
    import time
    state = _require_state()
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "message is empty"}
    today = time.strftime("%Y-%m-%d", time.localtime())
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    path = state.paths.journal_for_date(today)
    path.parent.mkdir(parents=True, exist_ok=True)
    # New file gets a date header so a quick `cat` is readable.
    if not path.exists():
        header = f"# Journal — {today}\n\n"
    else:
        header = ""
    line = f"- **{timestamp}**  {message}\n"
    with path.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(line)
    return {
        "ok": True,
        "date": today,
        "timestamp": timestamp,
        "path": str(path),
        "message": message,
    }


@tool(description="Phase 72: Read the last N days of journal entries from studio/memory/journal/. days defaults to 1 (today only). Returns each day's entries plus a flat 'recent' list so chat panels can render either a calendar view or a single stream. Days with no entries are skipped — the result never crashes when the journal directory is empty or missing.")
def studio_journal_read(days: int = 1) -> dict:
    import time
    state = _require_state()
    if days <= 0:
        return {"ok": False, "error": "days must be positive"}

    journal_dir = state.paths.journal
    if not journal_dir.is_dir():
        return {"ok": True, "days": days, "entries_by_date": {}, "recent": [], "total_days": 0}

    today_ts = time.time()
    entries_by_date: dict[str, str] = {}
    recent: list[dict] = []
    for offset in range(days):
        day_ts = today_ts - offset * 86400
        date_iso = time.strftime("%Y-%m-%d", time.localtime(day_ts))
        path = state.paths.journal_for_date(date_iso)
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        entries_by_date[date_iso] = content
        recent.append({"date": date_iso, "content": content})

    return {
        "ok": True,
        "days": days,
        "entries_by_date": entries_by_date,
        "recent": recent,
        "total_days": len(entries_by_date),
    }


@tool(description="Phase 71: Morning standup digest. Aggregates: tasks closed within the window, tasks currently in_progress, blocked tasks, pending backlog count, and a per-role breakdown of activity. window_hours defaults to 24 (since yesterday). The shape is consistent regardless of activity level so chat panels can render it without conditional logic.")
def studio_standup(window_hours: float = 24.0) -> dict:
    import time
    state = _require_state()
    now = time.time()
    cutoff = now - (window_hours * 3600)

    all_tasks = state.load_tasks()

    closed_recent = [
        t for t in all_tasks
        if t.status is TaskStatus.DONE
        and (getattr(t, "updated_at", 0) or 0) >= cutoff
    ]
    in_flight = [t for t in all_tasks if t.status is TaskStatus.IN_PROGRESS]
    blocked = [t for t in all_tasks if t.status is TaskStatus.BLOCKED]
    pending = [t for t in all_tasks if t.status is TaskStatus.PENDING]
    review = [t for t in all_tasks if t.status is TaskStatus.REVIEW]

    # Per-role activity in the window: closed counts by discipline so
    # the producer can see whether one role is starved.
    from collections import Counter
    by_role_closed = Counter(t.role for t in closed_recent)
    by_role_inflight = Counter(t.role for t in in_flight)
    by_role_blocked = Counter(t.role for t in blocked)

    def _summarise(tasks: list[Task], limit: int = 5) -> list[dict]:
        return [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "milestone": t.milestone,
                "blockers": list(t.blockers or [])[:3],
            }
            for t in tasks[:limit]
        ]

    return {
        "ok": True,
        "window_hours": window_hours,
        "now": now,
        "cutoff": cutoff,
        # Highlights
        "closed_recent": _summarise(closed_recent),
        "closed_recent_count": len(closed_recent),
        "in_flight": _summarise(in_flight),
        "in_flight_count": len(in_flight),
        "blocked": _summarise(blocked, limit=10),
        "blocked_count": len(blocked),
        "review_count": len(review),
        "pending_count": len(pending),
        "total_tasks": len(all_tasks),
        # Per-role rollups
        "closed_by_role": dict(by_role_closed),
        "in_flight_by_role": dict(by_role_inflight),
        "blocked_by_role": dict(by_role_blocked),
    }


@tool(description="Phase 85: End-of-day wrap-up — what landed today, what's carrying over to tomorrow, what's still blocked, plus today's commits + journal entries + the next-pending task suggestion. Pairs with the morning /standup: standup is forward-looking ('what's open'), wrap-up is close-out + handoff ('what landed, what to pick up tomorrow'). The window is bounded by local-day midnight, not a 24-hour sliding scope.")
def studio_wrap_up() -> dict:
    import time
    state = _require_state()

    now = time.time()
    # Local midnight today — wrap-up scopes to the calendar day
    local_today = time.localtime(now)
    midnight_struct = time.struct_time((
        local_today.tm_year, local_today.tm_mon, local_today.tm_mday,
        0, 0, 0, local_today.tm_wday, local_today.tm_yday, local_today.tm_isdst,
    ))
    cutoff = time.mktime(midnight_struct)
    today_iso = time.strftime("%Y-%m-%d", local_today)

    all_tasks = state.load_tasks()

    closed_today = [
        t for t in all_tasks
        if t.status is TaskStatus.DONE
        and (getattr(t, "updated_at", 0) or 0) >= cutoff
    ]
    in_flight = [t for t in all_tasks if t.status is TaskStatus.IN_PROGRESS]
    blocked = [t for t in all_tasks if t.status is TaskStatus.BLOCKED]

    def _shape(tasks: list[Task]) -> list[dict]:
        return [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "milestone": t.milestone,
                "blockers": list(t.blockers or [])[:3],
            }
            for t in tasks
        ]

    # Journal entries written today (line-count, parsed from the daily file)
    journal_entries_today = 0
    journal_path = state.paths.journal_for_date(today_iso)
    if journal_path.is_file():
        try:
            content = journal_path.read_text(encoding="utf-8")
            import re
            journal_entries_today = len(re.findall(
                r"^\s*-\s+\*\*\d{2}:\d{2}:\d{2}\*\*", content, re.MULTILINE,
            ))
        except Exception:
            journal_entries_today = 0

    # Commits today via studio_recent_commits (resolved at call time)
    commits_today: list[dict] = []
    try:
        commits_result = studio_recent_commits(limit=50)
        if commits_result.get("ok"):
            for c in commits_result.get("commits", []):
                ts = c.get("timestamp", 0) or 0
                if ts >= cutoff:
                    commits_today.append({
                        "sha": c.get("sha"),
                        "subject": c.get("subject"),
                        "author": c.get("author"),
                    })
    except Exception:  # noqa: BLE001
        commits_today = []

    # Tomorrow's pick — first ready pending task
    next_pick = None
    try:
        nxt_result = studio_next_task()
        if nxt_result.get("ok") and nxt_result.get("task"):
            t = nxt_result["task"]
            next_pick = {
                "id": t["id"],
                "title": t["title"],
                "role": t["role"],
                "milestone": t.get("milestone"),
            }
    except Exception:  # noqa: BLE001
        next_pick = None

    return {
        "ok": True,
        "date": today_iso,
        "cutoff": cutoff,
        "closed_today": _shape(closed_today),
        "closed_today_count": len(closed_today),
        "in_flight": _shape(in_flight),
        "in_flight_count": len(in_flight),
        "blocked": _shape(blocked),
        "blocked_count": len(blocked),
        "commits_today": commits_today,
        "commits_today_count": len(commits_today),
        "journal_entries_today": journal_entries_today,
        "next_pick": next_pick,
    }


@tool(description="Phase 84: Mark a task as REJECTED — the 'won't do' close-out for stale or no-longer-relevant pending work. Optional reason is appended to the blockers list so the rejection rationale stays with the task. Use this for backlog hygiene; for blockers that are still worth tracking use studio_block_task instead.")
def studio_reject_task(task_id: str, reason: str = "") -> dict:
    state = _require_state()
    tasks = state.load_tasks()
    for t in tasks:
        if t.id == task_id:
            if reason and reason.strip():
                t.blockers = list(t.blockers or []) + [f"rejected: {reason.strip()}"]
            t.status = TaskStatus.REJECTED
            state.update_task(t)
            return {
                "ok": True,
                "task_id": t.id,
                "status": t.status.value,
                "blockers": list(t.blockers or []),
            }
    return {"ok": False, "error": f"Task {task_id!r} not found."}


@tool(description="Phase 83: Every blocked task across the studio, with full blocker reasons. The 'why am I blocked' producer scan — complements /standup's blocked count by surfacing each task's actual blocker text. Grouped by role so the producer sees concentration.")
def studio_blocked_tasks() -> dict:
    state = _require_state()
    blocked = [t for t in state.load_tasks() if t.status is TaskStatus.BLOCKED]

    from collections import Counter
    by_role = Counter(t.role for t in blocked)

    return {
        "ok": True,
        "count": len(blocked),
        "by_role": dict(by_role),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "milestone": t.milestone,
                "blockers": list(t.blockers or []),
                "updated_at": getattr(t, "updated_at", 0),
            }
            for t in blocked
        ],
    }


@tool(description="Phase 83: Every in_progress task across the studio with its owner. The 'what's everyone working on right now' producer scan. Sorted oldest-first by updated_at so anything that's been in flight for a long time bubbles up — those are the candidates for /why or /block triage.")
def studio_inflight_tasks() -> dict:
    state = _require_state()
    inflight = [t for t in state.load_tasks() if t.status is TaskStatus.IN_PROGRESS]
    # Oldest-updated first: long-running in-flight tasks are stickiness signals
    inflight.sort(key=lambda t: getattr(t, "updated_at", 0) or 0)

    from collections import Counter
    by_role = Counter(t.role for t in inflight)

    return {
        "ok": True,
        "count": len(inflight),
        "by_role": dict(by_role),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "milestone": t.milestone,
                "updated_at": getattr(t, "updated_at", 0),
            }
            for t in inflight
        ],
    }


@tool(description="Phase 82: Full status drill-down for one role — every task that role owns, grouped by status (in_progress, pending, blocked, review, done_recent), with per-bucket counts. The done_recent bucket is capped to tasks closed within the last 7 days so the response stays scannable on long-running studios. Use this when /standup's per-role counts say a role has 12 tasks and you want to actually see them.")
def studio_role_status(role: str, recent_days: float = 7.0) -> dict:
    import time
    state = _require_state()
    if role not in ROLES:
        return {
            "ok": False,
            "error": f"Unknown role {role!r}. Allowed: {sorted(ROLES)}",
        }
    if recent_days <= 0:
        return {"ok": False, "error": "recent_days must be positive"}

    now = time.time()
    cutoff = now - (recent_days * 86400)
    role_tasks = [t for t in state.load_tasks() if t.role == role]

    def _shape(tasks: list[Task]) -> list[dict]:
        return [
            {
                "id": t.id,
                "title": t.title,
                "milestone": t.milestone,
                "blockers": list(t.blockers or [])[:3],
                "updated_at": getattr(t, "updated_at", 0),
            }
            for t in tasks
        ]

    in_progress = [t for t in role_tasks if t.status is TaskStatus.IN_PROGRESS]
    pending = [t for t in role_tasks if t.status is TaskStatus.PENDING]
    blocked = [t for t in role_tasks if t.status is TaskStatus.BLOCKED]
    review = [t for t in role_tasks if t.status is TaskStatus.REVIEW]
    done_all = [t for t in role_tasks if t.status is TaskStatus.DONE]
    done_recent = [
        t for t in done_all
        if (getattr(t, "updated_at", 0) or 0) >= cutoff
    ]
    # Sort pending by created_at so the next-up task surfaces at the top
    pending.sort(key=lambda t: getattr(t, "created_at", 0) or 0)
    # Sort recent-done newest-first
    done_recent.sort(
        key=lambda t: getattr(t, "updated_at", 0) or 0, reverse=True,
    )

    return {
        "ok": True,
        "role": role,
        "recent_days": recent_days,
        "total": len(role_tasks),
        "in_progress": _shape(in_progress),
        "in_progress_count": len(in_progress),
        "pending": _shape(pending),
        "pending_count": len(pending),
        "blocked": _shape(blocked),
        "blocked_count": len(blocked),
        "review": _shape(review),
        "review_count": len(review),
        "done_recent": _shape(done_recent),
        "done_recent_count": len(done_recent),
        "done_total": len(done_all),
    }


@tool(description="Phase 81: Combined activity timeline across the studio — recent git commits, tasks closed, decisions made, and journal entries — in one DESC-by-timestamp stream. days defaults to 7. Each event carries: timestamp (unix), source ('commit'/'task'/'decision'/'journal'), title, and source-specific extras. Useful for the 'what happened recently' daily catch-up.")
def studio_recent_activity(days: float = 7.0) -> dict:
    import time
    state = _require_state()
    if days <= 0:
        return {"ok": False, "error": "days must be positive"}

    now = time.time()
    cutoff = now - (days * 86400)
    events: list[dict] = []

    # ── Closed tasks within window
    for t in state.load_tasks():
        if t.status is not TaskStatus.DONE:
            continue
        ts = getattr(t, "updated_at", 0) or 0
        if ts >= cutoff:
            events.append({
                "timestamp": ts,
                "source": "task",
                "title": t.title,
                "role": t.role,
                "id": t.id,
                "milestone": t.milestone,
            })

    # ── Decisions in window
    for d in state.load_decisions():
        ts = getattr(d, "timestamp", 0) or 0
        if ts >= cutoff:
            events.append({
                "timestamp": ts,
                "source": "decision",
                "title": d.title,
                "status": d.status.value,
                "id": d.id,
                "summary": d.summary,
            })

    # ── Journal entries — each individual entry line in last N days
    if state.paths.journal.is_dir():
        for offset in range(int(days) + 1):
            day_ts = now - offset * 86400
            date_iso = time.strftime("%Y-%m-%d", time.localtime(day_ts))
            jpath = state.paths.journal_for_date(date_iso)
            if not jpath.is_file():
                continue
            try:
                content = jpath.read_text(encoding="utf-8")
            except Exception:
                continue
            # Parse each `- **HH:MM:SS**  <text>` line into an event
            import re
            for m in re.finditer(
                r"-\s+\*\*(\d{2}):(\d{2}):(\d{2})\*\*\s+(.+?)$",
                content, re.MULTILINE,
            ):
                hh, mm, ss, text = m.group(1), m.group(2), m.group(3), m.group(4)
                try:
                    entry_ts = time.mktime(time.strptime(
                        f"{date_iso} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S",
                    ))
                except Exception:
                    entry_ts = day_ts
                if entry_ts < cutoff:
                    continue
                events.append({
                    "timestamp": entry_ts,
                    "source": "journal",
                    "title": text.strip()[:120],
                    "date": date_iso,
                })

    # ── Git commits via the existing studio_recent_commits tool
    # (defined later in this module — resolved at call time).
    commits_result = studio_recent_commits(limit=50)
    if commits_result.get("ok"):
        for c in commits_result.get("commits", []):
            ts = c.get("timestamp", 0) or 0
            if ts >= cutoff:
                events.append({
                    "timestamp": ts,
                    "source": "commit",
                    "title": c.get("subject", ""),
                    "sha": c.get("sha"),
                    "author": c.get("author"),
                })

    # Sort newest-first
    events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)

    # Per-source counters
    from collections import Counter
    by_source = Counter(e["source"] for e in events)

    return {
        "ok": True,
        "days": days,
        "now": now,
        "cutoff": cutoff,
        "events": events,
        "event_count": len(events),
        "by_source": dict(by_source),
    }


@tool(description="Phase 80: Append a free-text note to a task's description. The new note is separated from existing content by a blank line and timestamped (YYYY-MM-DD HH:MM) so the description grows into a chronological record of the task's evolution. Never overwrites — pure append.")
def studio_append_task_note(task_id: str, note: str) -> dict:
    import time
    state = _require_state()
    note = (note or "").strip()
    if not note:
        return {"ok": False, "error": "note is empty"}
    tasks = state.load_tasks()
    for t in tasks:
        if t.id == task_id:
            stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime())
            entry = f"[{stamp}] {note}"
            existing = (t.description or "").strip()
            t.description = f"{existing}\n\n{entry}" if existing else entry
            state.update_task(t)
            return {
                "ok": True,
                "task_id": t.id,
                "appended": entry,
                "description": t.description,
            }
    return {"ok": False, "error": f"Task {task_id!r} not found."}


@tool(description="Phase 80: Wire a dependency between two tasks — `task_id` is the task that needs `dep_id` to be DONE before it's pickable. Both must already exist in the backlog. Self-references and duplicate deps are rejected. The /next slash command honours these dependencies and will skip tasks whose deps aren't satisfied.")
def studio_add_task_dependency(task_id: str, dep_id: str) -> dict:
    state = _require_state()
    if task_id == dep_id:
        return {"ok": False, "error": "task cannot depend on itself"}
    tasks = state.load_tasks()
    by_id = {t.id: t for t in tasks}
    if task_id not in by_id:
        return {"ok": False, "error": f"Task {task_id!r} not found."}
    if dep_id not in by_id:
        return {"ok": False, "error": f"Dependency {dep_id!r} not found in backlog."}

    t = by_id[task_id]
    current_deps = list(t.depends_on or [])
    if dep_id in current_deps:
        return {
            "ok": False,
            "error": f"{task_id[:8]} already depends on {dep_id[:8]}",
            "depends_on": current_deps,
        }
    t.depends_on = current_deps + [dep_id]
    state.update_task(t)
    return {
        "ok": True,
        "task_id": t.id,
        "depends_on": list(t.depends_on),
        "dep_added": dep_id,
    }


@tool(description="Phase 70: Find tasks whose id starts with the given prefix. Used by chat slash commands so the operator can type the short form (first 8 chars) that /next surfaces, instead of the full UUID. Returns all matches — caller decides whether ambiguity is fatal.")
def studio_find_task(partial_id: str) -> dict:
    state = _require_state()
    needle = (partial_id or "").strip().lower()
    if not needle:
        return {"ok": False, "error": "partial_id is empty"}
    matches = [t for t in state.load_tasks() if t.id.lower().startswith(needle)]
    return {
        "ok": True,
        "needle": needle,
        "matches": [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "status": t.status.value,
            }
            for t in matches
        ],
        "count": len(matches),
    }


@tool(description="Phase 69: Find the next pending task that's ready to be picked up. Skips tasks whose 'depends_on' includes anything not yet done. Optional role filter narrows to a single discipline (producer/designer/art_director/...). Returns the oldest ready task — FIFO by created_at — so the backlog moves in roughly the order it was planned.")
def studio_next_task(role: str = "") -> dict:
    """Return the single next ready-to-pick task (PENDING, dependencies
    satisfied, oldest-first). Used by the /next slash command for the
    daily 'what should I work on now' producer flow.

    Optional `role` narrows to one discipline so a designer can ask
    'next designer task' without seeing engineer work.
    """
    state = _require_state()
    if role and role not in ROLES:
        return {
            "ok": False,
            "error": f"Unknown role {role!r}. Allowed: {sorted(ROLES)}",
        }

    all_tasks = state.load_tasks()
    done_ids = {t.id for t in all_tasks if t.status is TaskStatus.DONE}

    pending: list[Task] = [t for t in all_tasks if t.status is TaskStatus.PENDING]
    if role:
        pending = [t for t in pending if t.role == role]

    # Skip tasks that still wait on undone deps; tasks with empty
    # depends_on are always considered ready.
    ready = [
        t for t in pending
        if all(dep in done_ids for dep in (t.depends_on or []))
    ]

    if not ready:
        # Why is nothing ready? Surface diagnostics so the producer can
        # see whether the backlog is empty vs. blocked.
        blocked_by_deps = [
            t for t in pending
            if any(dep not in done_ids for dep in (t.depends_on or []))
        ]
        return {
            "ok": True,
            "task": None,
            "pending_count": len(pending),
            "blocked_by_deps": len(blocked_by_deps),
            "reason": (
                "no pending tasks" if not pending
                else "all pending tasks are blocked by unfinished dependencies"
            ),
        }

    # Oldest-first; treats absent created_at defensively at 0
    ready.sort(key=lambda t: getattr(t, "created_at", 0) or 0)
    nxt = ready[0]
    return {
        "ok": True,
        "task": {
            "id": nxt.id,
            "title": nxt.title,
            "role": nxt.role,
            "description": nxt.description,
            "milestone": nxt.milestone,
            "depends_on": list(nxt.depends_on or []),
            "blockers": list(nxt.blockers or []),
            "created_at": getattr(nxt, "created_at", None),
        },
        "pending_count": len(pending),
        "ready_count": len(ready),
    }


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


# ─── Studio sync — migrate older studios to current schema (Phase 63) ─

@tool(description="Bring the active studio up to the current UnityTools schema. As phases ship, new starter docs (tutorial.md / scene_catalog.md / achievements.md / ...) and new directories (studio/dialogs/ / studio/strings/) are added. An older scaffolded studio misses these. studio_sync compares the studio against templates.starter_files() + paths.all_dirs(), reports what's missing, and optionally creates it. check_only=True is a read-only diff for CI. Never overwrites existing files.")
def studio_sync(check_only: bool = False) -> dict:
    from .templates import starter_files
    state = _require_state()
    paths = state.paths

    # 1. Directory check
    expected_dirs = paths.all_dirs()
    missing_dirs: list[str] = []
    for d in expected_dirs:
        if not d.is_dir():
            missing_dirs.append(str(d.relative_to(paths.root.parent))
                                if d.is_relative_to(paths.root.parent)
                                else str(d))

    # 2. Starter doc check
    expected_files = starter_files()
    missing_files: list[str] = []
    for rel_path in expected_files.keys():
        target = paths.root / rel_path
        if not target.exists():
            missing_files.append(rel_path)

    # 3. Schema version markers — surface info even when nothing to do
    behaviours_supported = 0
    try:
        from ..tools.unity_tools import _BEHAVIOUR_LIBRARY
        behaviours_supported = len(_BEHAVIOUR_LIBRARY)
    except ImportError:
        pass
    role_count = 0
    try:
        from .roles import all_roles
        role_count = len(all_roles())
    except ImportError:
        pass

    drift_count = len(missing_dirs) + len(missing_files)
    actions: list[str] = []

    if not check_only and drift_count > 0:
        # Apply migrations
        for d in expected_dirs:
            if not d.is_dir():
                d.mkdir(parents=True, exist_ok=True)
                rel = str(d.relative_to(paths.root.parent)) if d.is_relative_to(paths.root.parent) else str(d)
                actions.append(f"created dir: {rel}")
        for rel_path, content in expected_files.items():
            target = paths.root / rel_path
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                actions.append(f"created file: {rel_path}")

    return {
        "ok": True,
        "in_sync": drift_count == 0,
        "check_only": check_only,
        "drift_count": drift_count,
        "missing_dirs": missing_dirs,
        "missing_files": missing_files,
        "actions_applied": actions,
        "schema_info": {
            "expected_doc_count": len(expected_files),
            "expected_dir_count": len(expected_dirs),
            "behaviour_library_size": behaviours_supported,
            "role_count": role_count,
        },
        "recommendation": (
            "Studio is in sync with the current UnityTools schema."
            if drift_count == 0
            else (
                f"{drift_count} drift item(s); run studio_sync(check_only=False) "
                "to apply migrations. Existing files are never overwritten."
                if check_only
                else f"Applied {len(actions)} migration step(s)."
            )
        ),
    }


# ─── Studio Dashboard (Phase 58) ───────────────────────────────────────

@tool(description="Operator's morning glance. Aggregates every signal across the studio into ONE structured report: task / milestone / decision counts, ship readiness verdict, internal consistency drift, cost summary, balance audit, recent regressions, in-progress milestones with %. Use this as the first call of a producer standup. Optionally writes the report as markdown to studio/reviews/dashboard_<date>.md so the human sees the same view next morning. Engine-gated audits (lighting/atmosphere/vfx) are run only when a Unity bridge is connected; offline runs skip them cleanly.")
def studio_dashboard(days: int = 7, save_report: bool = False) -> dict:
    state = _require_state()
    if days < 1 or days > 90:
        return {"ok": False, "error": "days must be in 1..90."}

    bridge_connected = (
        _UNITY is not None
        and (not hasattr(_UNITY, "is_connected") or _UNITY.is_connected())
    )

    sections: dict[str, dict] = {}

    # 1) Counts — what's on the board right now
    try:
        sections["counts"] = studio_get_summary()
    except Exception as exc:  # noqa: BLE001
        sections["counts"] = {"ok": False, "error": str(exc)}

    # 2) Ship readiness — go / no-go verdict
    try:
        sections["ship_readiness"] = studio_ship_readiness_check(recent_days=days)
    except Exception as exc:  # noqa: BLE001
        sections["ship_readiness"] = {"ok": False, "error": str(exc)}

    # 3) Internal consistency — meta drift
    try:
        sections["internal_consistency"] = studio_internal_consistency_check()
    except Exception as exc:  # noqa: BLE001
        sections["internal_consistency"] = {"ok": False, "error": str(exc)}

    # 4) Cost — last N days
    try:
        sections["cost"] = studio_cost_summary(days=days)
    except Exception as exc:  # noqa: BLE001
        sections["cost"] = {"ok": False, "error": str(exc)}

    # 5) Balance — playtest + perf signals
    try:
        sections["balance"] = studio_balance_audit(days=days)
    except Exception as exc:  # noqa: BLE001
        sections["balance"] = {"ok": False, "error": str(exc)}

    # 6) Recent regressions — last 5 entries, any kind
    try:
        sections["recent_regressions"] = studio_recent_regressions(
            hours=days * 24, limit=5
        )
    except Exception as exc:  # noqa: BLE001
        sections["recent_regressions"] = {"ok": False, "error": str(exc)}

    # 7) Milestones with progress — only the in_progress ones
    try:
        from .milestones import all_milestones_with_progress
        rows = all_milestones_with_progress(state)
        in_progress = [
            r for r in rows
            if str(r.get("status", "")).lower() in ("in_progress", "planning")
        ]
        sections["milestones_in_flight"] = {
            "ok": True,
            "count": len(in_progress),
            "rows": in_progress,
        }
    except Exception as exc:  # noqa: BLE001
        sections["milestones_in_flight"] = {"ok": False, "error": str(exc)}

    # ── Headline verdict
    blockers: list[str] = []
    ship_v = sections["ship_readiness"].get("verdict", "fail")
    consist_v = sections["internal_consistency"].get("verdict", "fail")
    balance_failure_rate = sections["balance"].get("playtest_failure_rate", 0.0) or 0.0
    if ship_v != "pass":
        blockers.append("ship_readiness_fail")
    if consist_v != "pass":
        blockers.append("internal_consistency_drift")
    if balance_failure_rate > 0.5:
        blockers.append(f"playtest_failure_rate_high:{balance_failure_rate:.2f}")
    headline = "green" if not blockers else "blockers"

    # ── Markdown summary (always built; optionally written to disk)
    md = _format_dashboard_markdown(sections, days, headline, blockers)
    saved_path: Optional[str] = None
    if save_report:
        state.paths.reviews.mkdir(parents=True, exist_ok=True)
        dt = time.strftime("%Y-%m-%d")
        path = state.paths.reviews / f"dashboard_{dt}.md"
        path.write_text(md, encoding="utf-8")
        saved_path = str(path)

    return {
        "ok": True,
        "days": days,
        "bridge_connected": bridge_connected,
        "headline": headline,
        "blockers": blockers,
        "sections": sections,
        "markdown": md,
        "saved_path": saved_path,
    }


def _format_dashboard_markdown(sections: dict, days: int, headline: str, blockers: list[str]) -> str:
    """Build a one-page markdown report from the dashboard sections."""
    out: list[str] = []
    today = time.strftime("%Y-%m-%d %H:%M")
    out.append(f"# Studio Dashboard — {today}")
    out.append(f"")
    out.append(f"**Window:** last {days} day(s)   **Headline:** **{headline.upper()}**")
    if blockers:
        out.append(f"**Blockers:** " + ", ".join(f"`{b}`" for b in blockers))
    out.append("")

    # Counts
    c = sections.get("counts", {})
    if c.get("ok") is not False:
        out.append("## Counts")
        out.append(
            f"- Tasks: **{c.get('task_count', 0)}** "
            f"(by status: {c.get('tasks_by_status', {}) or '—'})"
        )
        out.append(f"- Milestones: **{c.get('milestone_count', 0)}**")
        out.append(f"- Decisions: **{c.get('decision_count', 0)}**")
        out.append("")

    # Ship readiness
    sr = sections.get("ship_readiness", {})
    out.append("## Ship Readiness")
    out.append(f"Verdict: **{sr.get('verdict', '?')}** "
                f"({sr.get('blocker_count', 0)} blockers)")
    if sr.get("blockers"):
        for b in sr["blockers"][:8]:
            out.append(f"- `{b}`")
    out.append("")

    # Internal consistency
    ic = sections.get("internal_consistency", {})
    out.append("## Internal Consistency")
    out.append(f"Verdict: **{ic.get('verdict', '?')}** "
                f"({ic.get('drift_count', 0)} drifts)")
    if ic.get("drifts"):
        for d in ic["drifts"][:6]:
            out.append(f"- `{d}`")
    out.append("")

    # Cost
    cs = sections.get("cost", {})
    out.append(f"## Cost (last {days}d)")
    out.append(f"- Total calls: **{cs.get('total_calls', 0)}**, "
                f"USD: **${cs.get('total_cost_usd', 0.0):.4f}**")
    top_role = sorted(
        (cs.get("by_role") or {}).items(),
        key=lambda kv: kv[1].get("cost_usd", 0.0),
        reverse=True,
    )[:3]
    for role, row in top_role:
        out.append(f"  - {role}: {row.get('calls', 0)} calls / ${row.get('cost_usd', 0.0):.4f}")
    out.append("")

    # Balance
    ba = sections.get("balance", {})
    out.append(f"## Balance (last {days}d)")
    out.append(f"- Playtests: **{ba.get('playtest_smokes', 0)}**, "
                f"failures: **{ba.get('playtest_failures', 0)}** "
                f"(rate {ba.get('playtest_failure_rate', 0.0):.2f})")
    if ba.get("top_missing_objects"):
        out.append("- Top missing objects:")
        for row in ba["top_missing_objects"][:3]:
            out.append(f"  - {row.get('name', '?')}: {row.get('missing_count', 0)}x")
    if ba.get("perf_violations"):
        out.append(f"- Perf violations: {ba['perf_violations']}")
    out.append("")

    # Milestones in flight
    ms = sections.get("milestones_in_flight", {})
    if ms.get("count"):
        out.append("## Milestones In Flight")
        for r in ms.get("rows", [])[:6]:
            pct = r.get("percent_done", 0)
            out.append(f"- {r.get('name', r.get('title', '?'))} — **{pct}%** "
                        f"({r.get('done_count', 0)}/{r.get('total_count', 0)})")
        out.append("")

    # Recent regressions
    rr = sections.get("recent_regressions", {})
    if rr.get("count"):
        out.append("## Recent Regressions (last 5)")
        for entry in rr.get("entries", [])[:5]:
            kind = entry.get("kind", "?")
            out.append(f"- `{kind}` — {entry.get('ts', '?')}")
        out.append("")

    return "\n".join(out) + "\n"


# ─── Internal consistency audit (Phase 49) ─────────────────────────────

@tool(description="Audit the studio's own moving parts for internal consistency drift. Cross-checks: DISPATCH_MAP keys vs the ROLES validation tuple, DISPATCH_MAP targets vs registered RoleConfigs, each role's allowlist vs the actual registered tool set, behaviour-library Python tuple vs the C# library list vs the .cs files on disk, the studio/strings/ tables for malformed JSON. Returns verdict='pass'/'fail' + per-section status + named drifts. This is meta-tooling: as the studio grows phases, things go out of sync; the Producer / Critic runs this to catch drift early.")
def studio_internal_consistency_check() -> dict:
    from . import dispatch as _dispatch
    from . import roles as _roles
    from .models import ROLES as _ROLES_TUPLE
    from ..core.tool_registry import _REGISTRY
    # Eagerly trigger @tool registration for the engine + asset modules
    # so the consistency check sees the full vocabulary. Each module
    # registers its tools as a side effect of import.
    try:
        import unitytools.tools  # noqa: F401
    except ImportError:
        pass
    try:
        import unitytools.tools.unity_tools  # noqa: F401
    except ImportError:
        pass
    try:
        import unitytools.tools.asset_tools  # noqa: F401
    except ImportError:
        pass
    try:
        import unitytools.tools.snapshot_tools  # noqa: F401
    except ImportError:
        pass
    try:
        import unitytools.tools.scene_intelligence_tools  # noqa: F401
    except ImportError:
        pass
    try:
        import unitytools.tools.autopilot_quality_tools  # noqa: F401
    except ImportError:
        pass
    try:
        import unitytools.tools.procedural_tools  # noqa: F401
    except ImportError:
        pass

    sections: dict[str, dict] = {}
    drifts: list[str] = []

    # 1. DISPATCH_MAP keys vs ROLES validation tuple
    dispatch_keys = set(_dispatch.DISPATCH_MAP.keys())
    roles_tuple = set(_ROLES_TUPLE)
    missing_from_roles = dispatch_keys - roles_tuple
    missing_from_dispatch = roles_tuple - dispatch_keys
    sections["dispatch_vs_roles_tuple"] = {
        "ok": not missing_from_roles,
        "dispatch_map_keys": len(dispatch_keys),
        "roles_tuple_size": len(roles_tuple),
        "in_dispatch_but_not_in_roles": sorted(missing_from_roles),
        "in_roles_but_not_in_dispatch": sorted(missing_from_dispatch),
    }
    for k in missing_from_roles:
        drifts.append(f"role_in_dispatch_missing_from_validation_tuple:{k}")

    # 2. DISPATCH_MAP targets must resolve to registered RoleConfigs.
    role_ids_registered = {r.id for r in _roles.all_roles()}
    unresolved_targets: list[str] = []
    for src, target in _dispatch.DISPATCH_MAP.items():
        if target is None:
            continue
        if target not in role_ids_registered:
            unresolved_targets.append(f"{src}->{target}")
            drifts.append(f"unresolved_dispatch_target:{src}->{target}")
    sections["dispatch_targets_resolve"] = {
        "ok": not unresolved_targets,
        "registered_role_count": len(role_ids_registered),
        "unresolved": unresolved_targets,
    }

    # 3. Each role's allowlist must reference real registered tools.
    role_tool_drifts: dict[str, list[str]] = {}
    for role in _roles.all_roles():
        bad = [t for t in role.allowed_tools if t not in _REGISTRY]
        if bad:
            role_tool_drifts[role.id] = bad
            for t in bad:
                drifts.append(f"unregistered_tool_in_role_allowlist:{role.id}:{t}")
    sections["role_allowlists_registered"] = {
        "ok": not role_tool_drifts,
        "roles_with_drift": role_tool_drifts,
    }

    # 4. Behaviour library: Python tuple vs the .cs files on disk.
    #    (The C# library list lives in CommandHandlers.cs; we cross-check
    #    by globbing the Behaviours/ folder rather than parsing C#.)
    behaviours_dir = (Path(__file__).resolve().parents[2]
                       / "unity_plugin" / "Scripts" / "Behaviours")
    try:
        from ..tools.unity_tools import _BEHAVIOUR_LIBRARY  # noqa: F401
        py_set = set(_BEHAVIOUR_LIBRARY)
    except ImportError:
        py_set = set()
        drifts.append("unity_tools_module_unimportable")
    if behaviours_dir.exists():
        cs_files = {p.stem for p in behaviours_dir.glob("*.cs")}
    else:
        cs_files = set()
        drifts.append("behaviours_dir_missing")
    missing_files = py_set - cs_files
    extra_files = cs_files - py_set
    sections["behaviour_library"] = {
        "ok": not missing_files,
        "python_count": len(py_set),
        "cs_file_count": len(cs_files),
        "in_python_but_no_cs_file": sorted(missing_files),
        "in_cs_files_but_not_in_python": sorted(extra_files),
    }
    for name in missing_files:
        drifts.append(f"behaviour_in_python_library_without_cs_file:{name}")
    # Note: extra .cs files (existence in folder but not registered) is a
    # warning, not a hard drift — a developer may be drafting a new script.

    # 5. studio/strings/*.json files must parse as JSON objects.
    state = _STATE
    if state is not None and state.paths.strings.exists():
        malformed: list[str] = []
        for p in state.paths.strings.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    malformed.append(f"{p.stem}:not_object")
                    drifts.append(f"strings_not_object:{p.stem}")
            except json.JSONDecodeError:
                malformed.append(f"{p.stem}:malformed_json")
                drifts.append(f"strings_malformed:{p.stem}")
        sections["strings_files"] = {
            "ok": not malformed,
            "checked_count": len(list(state.paths.strings.glob("*.json"))),
            "malformed": malformed,
        }
    else:
        sections["strings_files"] = {
            "ok": True,
            "skipped": True,
            "reason": "no studio state or strings/ dir missing",
        }

    # 6. Final verdict
    verdict = "pass" if not drifts else "fail"
    return {
        "ok": True,
        "verdict": verdict,
        "drift_count": len(drifts),
        "drifts": drifts,
        "sections": sections,
        "recommendation": (
            "No drift. The studio's moving parts are aligned."
            if verdict == "pass"
            else (
                "Drift detected — each named entry tells you what to do. "
                "Common fixes: add a missing role id to models.py ROLES, "
                "remove a stray tool name from a role's allowlist, ship "
                "the missing .cs file for a registered behaviour name."
            )
        ),
    }


# ─── Ship readiness (Phase 45) ─────────────────────────────────────────

@tool(description="Aggregate every ship-blocking audit + doc state into a single go/no-go verdict. Runs studio_build_check (scenes + GDD), studio_localization_audit per locale, studio_atmosphere_audit + studio_lighting_audit + studio_vfx_audit when the Unity bridge is connected (skipped gracefully when offline). Also checks: art bible non-empty, audio brief non-empty, press kit non-empty, at least one screenshot present, recent playtest in last `recent_days` days, at least one milestone in 'in_progress'. Returns verdict='pass'/'fail' + per-section status + named blockers. The Marketing + Build Engineer roles call this before ship; Producer cites the result in retros.")
def studio_ship_readiness_check(
    target_locales: list[str] | None = None,
    recent_days: int = 7,
) -> dict:
    state = _require_state()
    if target_locales is None:
        target_locales = ["en"]
    if not isinstance(target_locales, list) or not target_locales:
        return {"ok": False, "error": "target_locales must be a non-empty list of locale codes."}

    sections: dict[str, dict] = {}
    blockers: list[str] = []
    bridge_connected = (
        _UNITY is not None
        and (not hasattr(_UNITY, "is_connected") or _UNITY.is_connected())
    )

    # 1) Docs — non-empty checks (file-system only, no bridge)
    def _doc_status(doc_path: Path, label: str, required: bool) -> dict:
        exists = doc_path.exists()
        content = doc_path.read_text(encoding="utf-8").strip() if exists else ""
        status = {
            "ok": bool(content),
            "exists": exists,
            "non_empty": bool(content),
            "byte_count": len(content.encode("utf-8")) if content else 0,
        }
        if required and not content:
            blockers.append(f"{label}_empty_or_missing")
        return status

    sections["gdd"] = _doc_status(state.paths.gdd, "gdd", required=True)
    sections["art_bible"] = _doc_status(state.paths.art_bible, "art_bible", required=True)
    sections["audio_brief"] = _doc_status(state.paths.audio_brief, "audio_brief", required=False)
    sections["press_kit"] = _doc_status(state.paths.press_kit, "press_kit", required=True)

    # 2) Milestones — need at least one in_progress
    try:
        all_ms = state.load_milestones()
        in_progress = [m for m in all_ms if m.status == MilestoneStatus.IN_PROGRESS]
        sections["milestones"] = {
            "ok": len(in_progress) >= 1,
            "total": len(all_ms),
            "in_progress": len(in_progress),
        }
        if not in_progress:
            blockers.append("no_in_progress_milestone")
    except Exception as exc:  # noqa: BLE001
        sections["milestones"] = {"ok": False, "error": str(exc)}
        blockers.append("milestones_unreadable")

    # 3) Screenshots — at least one captured
    shots = list(state.paths.qa_screenshots.glob("*.png")) if state.paths.qa_screenshots.exists() else []
    sections["screenshots"] = {
        "ok": len(shots) >= 1,
        "count": len(shots),
    }
    if not shots:
        blockers.append("no_screenshots_captured")

    # 4) Recent playtest — should have at least one playtest_smoke entry
    #    inside the recent_days window
    playtest_recent = False
    if state.paths.qa_regression.exists():
        cutoff = time.time() - max(0, int(recent_days)) * 86400.0
        try:
            with state.paths.qa_regression.open("r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("kind") != "playtest_smoke":
                        continue
                    ts = entry.get("ts")
                    if isinstance(ts, (int, float)) and ts >= cutoff:
                        playtest_recent = True
                        break
        except OSError:
            pass
    sections["recent_playtest"] = {
        "ok": playtest_recent,
        "window_days": recent_days,
    }
    if not playtest_recent:
        blockers.append(f"no_playtest_in_last_{recent_days}d")

    # 5) Localization — every target locale must have a non-empty table
    loc_results: list[dict] = []
    for loc in target_locales:
        try:
            r = studio_read_strings(loc)
            count = r.get("key_count", len(r.get("strings", {})))
            row = {"locale": loc, "ok": bool(count and count > 0), "key_count": count}
            loc_results.append(row)
            if not row["ok"]:
                blockers.append(f"locale_empty:{loc}")
        except Exception as exc:  # noqa: BLE001
            loc_results.append({"locale": loc, "ok": False, "error": str(exc)})
            blockers.append(f"locale_unreadable:{loc}")
    sections["localization"] = {
        "ok": all(r["ok"] for r in loc_results) if loc_results else False,
        "target_locales": target_locales,
        "results": loc_results,
    }

    # 6) Engine-gated audits — skip cleanly when offline
    if not bridge_connected:
        sections["engine_audits"] = {
            "ok": False,
            "skipped": True,
            "reason": "Unity bridge not connected; engine-gated audits skipped. Re-run with the bridge online for a complete verdict.",
        }
    else:
        engine_sections: dict[str, dict] = {}
        for name, fn in (
            ("build_check", studio_build_check),
            ("lighting_audit", studio_lighting_audit),
            ("atmosphere_audit", studio_atmosphere_audit),
            ("vfx_audit", studio_vfx_audit),
        ):
            try:
                result = fn()
                verdict = result.get("verdict", "fail" if not result.get("ok") else "pass")
                engine_sections[name] = {
                    "ok": result.get("ok", False),
                    "verdict": verdict,
                    "violations": result.get("violations", []),
                }
                if verdict != "pass":
                    blockers.append(f"{name}_verdict_{verdict}")
            except Exception as exc:  # noqa: BLE001
                engine_sections[name] = {"ok": False, "error": str(exc)}
                blockers.append(f"{name}_errored")
        all_pass = all(
            s.get("ok") and s.get("verdict") == "pass"
            for s in engine_sections.values()
        )
        sections["engine_audits"] = {"ok": all_pass, **engine_sections}

    # 7) Final verdict
    verdict = "pass" if not blockers else "fail"
    return {
        "ok": True,
        "verdict": verdict,
        "bridge_connected": bridge_connected,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "sections": sections,
        "recommendation": (
            "Ship: every gate is green. Run build_engineer next."
            if verdict == "pass"
            else "Hold ship: address the listed blockers, then re-run studio_ship_readiness_check."
        ),
    }


# ─── Game template scaffolder (Phase 42) ───────────────────────────────

@tool(description="Scaffold a complete collectathon mini-game: drafts a milestone + a structured task batch covering Designer, Worker, UI Builder, Camera, Lighting, Atmosphere, Material, Audio Director + Engineer, Localization, Marketing, Build Engineer. Each task has concrete instructions referring to the Behaviour Library (GameSession / Collectible / ScoreHUD / KeyboardMover / PauseMenu). One Producer call -> a full backlog ready to dispatch. Returns the milestone id + list of opened task ids.")
def studio_scaffold_collectathon_game(
    game_name: str = "Coin Hunter",
    coin_count: int = 10,
    play_area_radius: float = 8.0,
    win_scene_name: str = "WinScene",
) -> dict:
    state = _require_state()
    if coin_count < 1 or coin_count > 100:
        return {"ok": False, "error": "coin_count must be in 1..100."}
    if play_area_radius <= 0 or play_area_radius > 50:
        return {"ok": False, "error": "play_area_radius must be in (0, 50]."}

    # 1) Create a milestone so all tasks link to one tracking row.
    milestone_name = f"Ship MVP: {game_name}"
    milestone = Milestone(
        name=milestone_name,
        description=(
            f"End-to-end collectathon MVP. Player walks with KeyboardMover, "
            f"collects {coin_count} coins (Collectible -> GameSession), HUD "
            f"shows progress (ScoreHUD), win condition loads {win_scene_name!r}, "
            f"Escape pauses (PauseMenu), settings persist (SettingsStore)."
        ),
    )
    state.add_milestone(milestone)
    milestone_id = milestone.id

    # 2) Define the task batch. Each is intentionally concrete enough that a
    #    Worker / specialist can execute without follow-up questions.
    tasks_spec: list[tuple[str, str, str]] = [
        (
            "designer",
            f"Draft GDD for {game_name}",
            f"Write a one-page GDD for a collectathon MVP. Pitch: 'Walk + collect "
            f"{coin_count} coins to win.' Pillars: discoverable, no fail state, "
            f"under 5-minute runs. Win scene: {win_scene_name!r}. Update GDD via "
            "studio_write_gdd; propose any non-trivial decisions."
        ),
        (
            "art_director",
            "Draft Art Bible — palette + style",
            "Pick a 4-colour palette + style sentence + lighting recipe + 'do not' "
            "list. Save via studio_write_art_bible. Propose a decision for the "
            "dominant palette so downstream Lighting + Atmosphere + Material "
            "Artist roles align."
        ),
        (
            "worker",
            f"Place player + {coin_count} coins + GameSession",
            f"Step-by-step:\n"
            f"1. unity_create_scene_snapshot(label='{{task_id}}_before')\n"
            f"2. unity_create_primitive(primitive_type='Capsule', name='Player')\n"
            f"   then unity_set_position(name='Player', y=1.0)\n"
            f"3. unity_attach_behaviour(target_name='Player', behaviour_name='KeyboardMover',\n"
            f"   params={{'speed': 5.0, 'applyGravity': true}})\n"
            f"4. Create an empty GameObject 'GameSession' (unity_create_empty),\n"
            f"   attach GameSession with winScore={coin_count}, winSceneName='{win_scene_name}'.\n"
            f"5. Place {coin_count} coins on a circle of radius {play_area_radius} around (0,0,0):\n"
            f"   for i in 0..{coin_count-1}: unity_create_primitive('Sphere', name='Coin_{{i}}'),\n"
            f"   set_position to (cos(angle)*r, 1, sin(angle)*r), set_scale to 0.4,\n"
            f"   add SphereCollider with isTrigger=true (via unity_add_component),\n"
            f"   unity_attach_behaviour(behaviour_name='Collectible',\n"
            f"      params={{'scoreValue': 1, 'playerFilter': 'Player'}}),\n"
            f"   unity_attach_behaviour(behaviour_name='Rotator',\n"
            f"      params={{'speedDegPerSec': 90}}).\n"
            f"6. unity_save_scene()\n"
            f"7. studio_update_task_status('{{task_id}}', 'done')"
        ),
        (
            "ui_builder",
            "Build HUD + Pause Canvas",
            f"Step-by-step:\n"
            f"1. unity_create_ui_canvas(name='HUDCanvas')\n"
            f"2. unity_create_ui_text(canvas_name='HUDCanvas', name='ScoreText',\n"
            f"   text='Coins: 0/{coin_count}', position_x=0, position_y=320, font_size=42)\n"
            f"3. unity_attach_behaviour(target_name='ScoreText',\n"
            f"   behaviour_name='ScoreHUD', params={{'format': 'Coins: {{score}}/{{win}}'}})\n"
            f"4. unity_create_ui_canvas(name='PauseCanvas')\n"
            f"5. unity_create_ui_text(canvas_name='PauseCanvas', name='PausedLabel',\n"
            f"   text='Paused', position_y=80, font_size=64)\n"
            f"6. unity_create_ui_button(canvas_name='PauseCanvas', name='ResumeButton',\n"
            f"   label='Resume', position_y=-80, width=240, height=72)\n"
            f"7. unity_attach_behaviour(target_name='PauseCanvas',\n"
            f"   behaviour_name='PauseMenu', params={{'toggleKey': 'Escape'}})\n"
            f"8. unity_attach_behaviour(target_name='HUDCanvas',\n"
            f"   behaviour_name='SettingsStore')\n"
            f"9. unity_save_scene(); studio_update_task_status('{{task_id}}', 'done')"
        ),
        (
            "lighting_director",
            "Light the playfield",
            "Audit lighting (studio_lighting_audit). If no directional light, add "
            "one tinted toward the Art Bible palette. Land verdict=pass."
        ),
        (
            "atmosphere_director",
            "Set sky + fog matching palette",
            "Read Art Bible. Configure procedural skybox + fog mode that fits the "
            "dominant palette. Run studio_atmosphere_audit until verdict=pass."
        ),
        (
            "camera_director",
            "Frame the play area",
            f"Frame the play area at center=(0,0,0) radius={play_area_radius}. Use "
            f"studio_camera_frame_check(target_name='GameSession', "
            f"distance={play_area_radius * 1.8:.1f}, yaw_degrees=-30, "
            f"pitch_degrees=55) for an overhead hero shot."
        ),
        (
            "material_artist",
            "Make coins read as gold",
            "For each Coin_N, set_material_pbr(metallic=1.0, smoothness=0.85). "
            "Skip if Worker already left a non-default PBR."
        ),
        (
            "audio_director",
            "Draft Audio Brief",
            "Write a one-page brief: upbeat / playful mood, 44.1kHz / 16-bit, "
            "1 ambient music loop + 1 pickup SFX. Save via studio_write_audio_brief."
        ),
        (
            "localization_lead",
            "Seed en + tr string tables",
            f"studio_write_strings('en', strings={{"
            f"'title.main': '{game_name}', 'btn.start': 'Start', 'btn.resume': 'Resume', "
            f"'hud.coins': 'Coins: ', 'screen.win': 'You Win!', 'screen.pause': 'Paused'"
            f"}}). Then translate the same keys into 'tr'. Run "
            f"studio_localization_audit until verdict=pass."
        ),
        (
            "marketing_director",
            "Finalize PlayerSettings + press kit",
            f"unity_set_player_settings(product_name='{game_name}', "
            f"company_name='UnityTools Studio', version='0.1.0', "
            f"bundle_id='com.unitytools.{game_name.lower().replace(' ', '')}'). "
            "Capture a hero shot. Write press_kit citing real screenshot paths."
        ),
        (
            "playtester",
            "Smoke-test the build",
            "Run studio_playtest_smoke(expected_object_names=['Player', 'GameSession', "
            "'HUDCanvas']). Mark blocked if any go missing."
        ),
        (
            "build_engineer",
            "Ship Windows build",
            "Run studio_build_check; if pass, unity_build_player(target='windows', "
            f"output_path='studio/builds/<date>/windows/{game_name.replace(' ', '')}.exe'). "
            "Report warnings."
        ),
    ]

    opened: list[dict] = []
    for role, title, description in tasks_spec:
        if role not in ROLES:
            # Skip a role that isn't registered (e.g. older ROLES tuple). Log
            # silently rather than failing the whole scaffold.
            continue
        task = Task(
            title=title,
            role=role,
            description=description,
            milestone=milestone_id,
        )
        state.add_task(task)
        opened.append({"task_id": task.id, "role": task.role, "title": task.title})

    return {
        "ok": True,
        "game_name": game_name,
        "coin_count": coin_count,
        "milestone_id": milestone_id,
        "milestone_name": milestone_name,
        "task_count": len(opened),
        "tasks": opened,
    }


@tool(description="Scaffold a complete top-down shooter / wave-survival mini-game: drafts a milestone + a structured task batch using the combat Behaviour Library (Projectile / Shooter / Spawner / Enemy). target_kills sets the win condition; spawn_interval + max_alive control wave pacing. One Producer call -> a full action-genre backlog. Returns the milestone id + list of opened task ids.")
def studio_scaffold_top_down_shooter_game(
    game_name: str = "Wave Hunter",
    target_kills: int = 30,
    spawn_interval: float = 2.0,
    max_alive: int = 5,
    play_area_radius: float = 12.0,
    win_scene_name: str = "WinScene",
) -> dict:
    state = _require_state()
    if target_kills < 1 or target_kills > 500:
        return {"ok": False, "error": "target_kills must be in 1..500."}
    if spawn_interval <= 0 or spawn_interval > 30:
        return {"ok": False, "error": "spawn_interval must be in (0, 30] seconds."}
    if max_alive < 1 or max_alive > 50:
        return {"ok": False, "error": "max_alive must be in 1..50."}
    if play_area_radius <= 0 or play_area_radius > 50:
        return {"ok": False, "error": "play_area_radius must be in (0, 50]."}

    milestone_name = f"Ship MVP: {game_name}"
    milestone = Milestone(
        name=milestone_name,
        description=(
            f"End-to-end top-down shooter MVP. Player walks with KeyboardMover, "
            f"clicks to fire (Shooter -> Projectile), enemies spawn on a "
            f"{spawn_interval}s interval (Spawner, cap {max_alive}) and chase "
            f"the player (Enemy + FollowTarget). Win after {target_kills} kills "
            f"loads {win_scene_name!r}; lose-on-contact via Enemy.contactDamage."
        ),
    )
    state.add_milestone(milestone)
    milestone_id = milestone.id

    tasks_spec: list[tuple[str, str, str]] = [
        (
            "designer",
            f"Draft GDD for {game_name}",
            f"Write a one-page GDD for a top-down wave-survival MVP. Pitch: "
            f"'Click to shoot, survive {target_kills} enemy kills.' Pillars: "
            f"tight loop, 3 minutes to complete a run, fail state matters. "
            f"Win scene: {win_scene_name!r}. Update GDD via studio_write_gdd."
        ),
        (
            "art_director",
            "Draft Art Bible — combat palette",
            "Pick a 4-colour palette where ENEMY and PROJECTILE colours read "
            "against the background (the player needs to see incoming threats "
            "fast). Save via studio_write_art_bible."
        ),
        (
            "worker",
            f"Place player + templates + GameSession + Spawner",
            f"Step-by-step:\n"
            f"1. unity_create_scene_snapshot(label='{{task_id}}_before')\n"
            f"2. Player setup:\n"
            f"   unity_create_primitive('Capsule', name='Player')\n"
            f"   unity_set_position(name='Player', y=1.0)\n"
            f"   unity_attach_behaviour('Player', 'KeyboardMover',\n"
            f"      params={{'speed': 6.0, 'applyGravity': true}})\n"
            f"3. ProjectileTemplate (hidden, cloned by Shooter):\n"
            f"   unity_create_primitive('Sphere', name='ProjectileTemplate')\n"
            f"   unity_set_scale(name='ProjectileTemplate', uniform=0.3)\n"
            f"   unity_add_component('ProjectileTemplate', 'SphereCollider')\n"
            f"   (set isTrigger=true on the collider)\n"
            f"   unity_attach_behaviour('ProjectileTemplate', 'Projectile',\n"
            f"      params={{'speed': 18, 'lifetime': 3, 'damage': 1,\n"
            f"               'ignoreNamePrefix': 'Player'}})\n"
            f"4. Shooter on the Player:\n"
            f"   unity_attach_behaviour('Player', 'Shooter',\n"
            f"      params={{'projectileTemplateName': 'ProjectileTemplate',\n"
            f"               'fireRate': 5, 'aimAtMouse': true}})\n"
            f"5. EnemyTemplate (hidden, cloned by Spawner):\n"
            f"   unity_create_primitive('Cube', name='EnemyTemplate')\n"
            f"   unity_add_component('EnemyTemplate', 'BoxCollider')\n"
            f"   (set isTrigger=true)\n"
            f"   unity_attach_behaviour('EnemyTemplate', 'Enemy',\n"
            f"      params={{'health': 1, 'scoreOnDeath': 1,\n"
            f"               'contactDamage': 1, 'playerNamePrefix': 'Player'}})\n"
            f"   unity_attach_behaviour('EnemyTemplate', 'FollowTarget',\n"
            f"      params={{'targetName': 'Player', 'smoothing': 2.0,\n"
            f"               'lookAtTarget': true}})\n"
            f"6. Spawner on an empty GO at origin:\n"
            f"   unity_create_empty(name='Spawner')\n"
            f"   unity_attach_behaviour('Spawner', 'Spawner',\n"
            f"      params={{'templateName': 'EnemyTemplate',\n"
            f"               'interval': {spawn_interval},\n"
            f"               'maxAlive': {max_alive},\n"
            f"               'spawnRadius': {play_area_radius},\n"
            f"               'warmup': 2.0, 'flatXZ': true}})\n"
            f"7. GameSession:\n"
            f"   unity_create_empty(name='GameSession')\n"
            f"   unity_attach_behaviour('GameSession', 'GameSession',\n"
            f"      params={{'winScore': {target_kills},\n"
            f"               'winSceneName': '{win_scene_name}',\n"
            f"               'startingLives': 3,\n"
            f"               'loseSceneName': 'GameOverScene'}})\n"
            f"8. unity_save_scene(); studio_update_task_status('{{task_id}}', 'done')"
        ),
        (
            "ui_builder",
            "Build HUD + Pause Canvas",
            f"Step-by-step:\n"
            f"1. unity_create_ui_canvas(name='HUDCanvas')\n"
            f"2. unity_create_ui_text(canvas_name='HUDCanvas', name='ScoreText',\n"
            f"   text='Kills: 0/{target_kills}', position_x=0, position_y=320, font_size=42)\n"
            f"3. unity_attach_behaviour('ScoreText', 'ScoreHUD',\n"
            f"   params={{'format': 'Kills: {{score}}/{{win}}  Lives: {{lives}}'}})\n"
            f"4. unity_create_ui_canvas(name='PauseCanvas')\n"
            f"5. unity_create_ui_text(canvas_name='PauseCanvas', name='PausedLabel',\n"
            f"   text='Paused', position_y=80, font_size=64)\n"
            f"6. unity_attach_behaviour('PauseCanvas', 'PauseMenu',\n"
            f"   params={{'toggleKey': 'Escape'}})\n"
            f"7. unity_attach_behaviour('HUDCanvas', 'SettingsStore')\n"
            f"8. unity_save_scene(); studio_update_task_status('{{task_id}}', 'done')"
        ),
        (
            "lighting_director",
            "Light the arena",
            "Audit + add a directional light tinted toward the combat palette. "
            "Action games benefit from slightly higher contrast — keep "
            "shadow_casting_count low (the spawned enemies otherwise blow the "
            "shadow budget). Land verdict=pass."
        ),
        (
            "atmosphere_director",
            "Set sky + fog for the arena",
            "Tighter fog than collectathon (mode='Linear', start=15, end=80) "
            "so distant spawns fade in dramatically. Sky tinted to palette."
        ),
        (
            "camera_director",
            "Frame the arena top-down",
            f"Use studio_camera_frame_check(target_name='Player', "
            f"distance={play_area_radius * 1.4:.1f}, yaw_degrees=0, "
            f"pitch_degrees=75) for a near-overhead view. Action games need "
            f"the player to see incoming threats from all 4 directions."
        ),
        (
            "material_artist",
            "Make projectile + enemy POP",
            "ProjectileTemplate: set_material_pbr(emission_enabled=1, "
            "emission_intensity=2.5, emission_r=1.0, emission_g=0.8, "
            "emission_b=0.2) so it reads as bright energy bolt. "
            "EnemyTemplate: keep matte (metallic=0, smoothness=0.2) so it "
            "doesn't compete visually with projectiles."
        ),
        (
            "audio_director",
            "Draft Audio Brief — combat",
            "Aggressive / tense mood. 1 ambient music loop + 1 pickup SFX is "
            "NOT enough — list 4: ambient combat loop, projectile fire, enemy "
            "hit, enemy death. 44.1kHz / 16-bit. Save via studio_write_audio_brief."
        ),
        (
            "localization_lead",
            "Seed en + tr string tables",
            f"studio_write_strings('en', strings={{"
            f"'title.main': '{game_name}', 'btn.start': 'Start', 'btn.resume': 'Resume', "
            f"'hud.kills': 'Kills: ', 'hud.lives': 'Lives: ', "
            f"'screen.win': 'Survived!', 'screen.lose': 'Eliminated', "
            f"'screen.pause': 'Paused'"
            f"}}). Translate the same keys into 'tr'. Run "
            f"studio_localization_audit until verdict=pass."
        ),
        (
            "marketing_director",
            "Finalize PlayerSettings + press kit",
            f"unity_set_player_settings(product_name='{game_name}', "
            f"company_name='UnityTools Studio', version='0.1.0', "
            f"bundle_id='com.unitytools.{game_name.lower().replace(' ', '')}'). "
            "Capture a hero shot DURING combat (projectile mid-flight). "
            "Press kit must call out the wave-survival angle."
        ),
        (
            "physics_qa",
            "Profile under wave load",
            f"Run studio_perf_budget_check with the EnemyTemplate spawner active. "
            f"Worst case: {max_alive} live enemies + their FollowTarget update + "
            f"in-flight projectiles. If triangle / renderer budgets blow, file a "
            f"task for the Worker to drop EnemyTemplate scale or LOD."
        ),
        (
            "playtester",
            "Smoke-test the loop",
            "Run studio_playtest_smoke(expected_object_names=['Player', "
            "'GameSession', 'Spawner', 'HUDCanvas']). Block if any go missing "
            "or if play mode errors fire (template GO might fail to clone)."
        ),
        (
            "game_balancer",
            "Audit after first playtest",
            f"Once Playtester has run, call studio_balance_audit(days=1). If "
            f"playtest_failure_rate > 0.5 (player keeps dying before "
            f"{target_kills} kills), file a Worker task to halve "
            f"Enemy.contactDamage. If failure_rate < 0.1 (too easy), file a "
            f"task to raise it or increase spawn_interval."
        ),
        (
            "build_engineer",
            "Ship Windows build",
            f"Run studio_build_check; if pass, unity_build_player(target='windows', "
            f"output_path='studio/builds/<date>/windows/{game_name.replace(' ', '')}.exe'). "
            "Wave games leak particle systems if the spawner doesn't prune — "
            "watch the warning count."
        ),
    ]

    opened: list[dict] = []
    for role, title, description in tasks_spec:
        if role not in ROLES:
            continue
        task = Task(
            title=title,
            role=role,
            description=description,
            milestone=milestone_id,
        )
        state.add_task(task)
        opened.append({"task_id": task.id, "role": task.role, "title": task.title})

    return {
        "ok": True,
        "game_name": game_name,
        "target_kills": target_kills,
        "spawn_interval": spawn_interval,
        "max_alive": max_alive,
        "milestone_id": milestone_id,
        "milestone_name": milestone_name,
        "task_count": len(opened),
        "tasks": opened,
    }


@tool(description="Scaffold a complete platformer mini-game: drafts a milestone + a structured task batch using KeyboardMover (horizontal, gravity OFF) + Jumper (vertical + space-jump) + Collectible (coins on platforms) + GameSession (winScore = coin_count). Inputs: coin_count, platform_count, jump_height. One Producer call -> a full platformer backlog.")
def studio_scaffold_platformer_game(
    game_name: str = "Hop Quest",
    coin_count: int = 12,
    platform_count: int = 8,
    jump_height: float = 2.5,
    platform_spread_x: float = 12.0,
    platform_spread_y: float = 6.0,
    win_scene_name: str = "WinScene",
) -> dict:
    state = _require_state()
    if coin_count < 1 or coin_count > 100:
        return {"ok": False, "error": "coin_count must be in 1..100."}
    if platform_count < 1 or platform_count > 50:
        return {"ok": False, "error": "platform_count must be in 1..50."}
    if jump_height <= 0 or jump_height > 20:
        return {"ok": False, "error": "jump_height must be in (0, 20] units."}
    if platform_spread_x <= 0 or platform_spread_x > 40:
        return {"ok": False, "error": "platform_spread_x must be in (0, 40]."}
    if platform_spread_y <= 0 or platform_spread_y > 30:
        return {"ok": False, "error": "platform_spread_y must be in (0, 30]."}

    milestone_name = f"Ship MVP: {game_name}"
    milestone = Milestone(
        name=milestone_name,
        description=(
            f"End-to-end platformer MVP. Player jumps between "
            f"{platform_count} platforms collecting {coin_count} coins. "
            f"KeyboardMover (gravity off) + Jumper handle motion. "
            f"GameSession win at {coin_count} coins -> {win_scene_name!r}; "
            f"falling off the world -> LoseLife via a kill-plane collider."
        ),
    )
    state.add_milestone(milestone)
    milestone_id = milestone.id

    tasks_spec: list[tuple[str, str, str]] = [
        (
            "designer",
            f"Draft GDD for {game_name}",
            f"Platformer pitch: 'Jump between platforms, collect {coin_count} "
            f"coins, don't fall.' Pillars: precise jump arc, 90-second runs, "
            f"forgiving inputs (coyote time + jump buffer baked into Jumper). "
            f"Win scene: {win_scene_name!r}."
        ),
        (
            "art_director",
            "Draft Art Bible — readable silhouettes",
            "Platformers live or die on silhouette clarity. Player must read "
            "against every platform from any angle. Pick a 4-colour palette "
            "where Player is the BRIGHTEST element. Save via "
            "studio_write_art_bible."
        ),
        (
            "scene_director",
            "Draft scene catalog (4-scene MVP)",
            "Scenes: Title + Game + Win + GameOver. Transitions: Title->Game "
            "via Start, Game->Win via GameSession auto-win, Game->GameOver "
            "via lives=0 (falling off the world). Save via "
            "studio_write_scene_catalog."
        ),
        (
            "worker",
            f"Place player + {platform_count} platforms + {coin_count} coins + GameSession",
            f"Step-by-step:\n"
            f"1. unity_create_scene_snapshot(label='{{task_id}}_before')\n"
            f"2. Player (CharacterController + KeyboardMover + Jumper):\n"
            f"   unity_create_primitive('Capsule', name='Player')\n"
            f"   unity_set_position(name='Player', x=0, y=2, z=0)\n"
            f"   unity_add_component('Player', 'CharacterController')\n"
            f"   unity_attach_behaviour('Player', 'KeyboardMover',\n"
            f"      params={{'speed': 7.0, 'applyGravity': false}})\n"
            f"   (CRITICAL: applyGravity=false because Jumper handles vertical)\n"
            f"   unity_attach_behaviour('Player', 'Jumper',\n"
            f"      params={{'jumpHeight': {jump_height},\n"
            f"               'gravity': 25.0,\n"
            f"               'groundCheckDistance': 1.05,\n"
            f"               'coyoteTime': 0.1, 'jumpBuffer': 0.1}})\n"
            f"3. Place {platform_count} platforms at varying heights:\n"
            f"   for i in 0..{platform_count - 1}:\n"
            f"     x = (random in -{platform_spread_x/2:.1f}..{platform_spread_x/2:.1f})\n"
            f"     y = (random in 1..{platform_spread_y:.1f})\n"
            f"     z = (i * 2.0 starting from 5)\n"
            f"     unity_create_primitive('Cube', name='Platform_{{i}}')\n"
            f"     unity_set_scale(name='Platform_{{i}}', x=3, y=0.4, z=2)\n"
            f"     unity_set_position(name='Platform_{{i}}', x=x, y=y, z=z)\n"
            f"4. Place {coin_count} coins ABOVE platforms (1.5 units up):\n"
            f"   for i in 0..{coin_count - 1}:\n"
            f"     pick a platform p (random)\n"
            f"     unity_create_primitive('Sphere', name='Coin_{{i}}')\n"
            f"     unity_set_scale(name='Coin_{{i}}', uniform=0.4)\n"
            f"     unity_set_position(at platform position + (0, 1.5, 0))\n"
            f"     unity_add_component('Coin_{{i}}', 'SphereCollider')\n"
            f"     (set isTrigger=true)\n"
            f"     unity_attach_behaviour('Coin_{{i}}', 'Collectible',\n"
            f"        params={{'scoreValue': 1, 'playerFilter': 'Player'}})\n"
            f"     unity_attach_behaviour('Coin_{{i}}', 'Rotator',\n"
            f"        params={{'speedDegPerSec': 90}})\n"
            f"5. Kill plane (player falls -> LoseLife):\n"
            f"   unity_create_primitive('Cube', name='KillPlane')\n"
            f"   unity_set_position(name='KillPlane', x=0, y=-10, z=0)\n"
            f"   unity_set_scale(name='KillPlane', x=100, y=1, z=100)\n"
            f"   (set BoxCollider isTrigger=true)\n"
            f"   unity_attach_behaviour('KillPlane', 'Enemy',\n"
            f"      params={{'health': 9999, 'scoreOnDeath': 0,\n"
            f"               'contactDamage': 99, 'playerNamePrefix': 'Player'}})\n"
            f"   (contactDamage=99 with startingLives=3 means one fall = death)\n"
            f"6. GameSession:\n"
            f"   unity_create_empty(name='GameSession')\n"
            f"   unity_attach_behaviour('GameSession', 'GameSession',\n"
            f"      params={{'winScore': {coin_count},\n"
            f"               'winSceneName': '{win_scene_name}',\n"
            f"               'startingLives': 3,\n"
            f"               'loseSceneName': 'GameOverScene'}})\n"
            f"7. unity_save_scene(); studio_update_task_status('{{task_id}}', 'done')"
        ),
        (
            "ui_builder",
            "Build HUD + Pause Canvas",
            f"1. unity_create_ui_canvas(name='HUDCanvas')\n"
            f"2. unity_create_ui_text(canvas_name='HUDCanvas', name='ScoreText',\n"
            f"   text='Coins: 0/{coin_count}', position_x=-400, position_y=400,\n"
            f"   font_size=42)\n"
            f"3. unity_attach_behaviour('ScoreText', 'ScoreHUD',\n"
            f"   params={{'format': 'Coins: {{score}}/{{win}}'}})\n"
            f"4. unity_create_ui_text(canvas_name='HUDCanvas', name='LivesText',\n"
            f"   text='Lives: 3', position_x=400, position_y=400, font_size=42)\n"
            f"5. unity_attach_behaviour('LivesText', 'ScoreHUD',\n"
            f"   params={{'format': 'Lives: {{lives}}'}})\n"
            f"6. unity_create_ui_canvas(name='PauseCanvas')\n"
            f"7. unity_attach_behaviour('PauseCanvas', 'PauseMenu',\n"
            f"   params={{'toggleKey': 'Escape'}})\n"
            f"8. unity_attach_behaviour('HUDCanvas', 'SettingsStore')\n"
            f"9. unity_save_scene()"
        ),
        (
            "lighting_director",
            "Light the platforms",
            "Directional light from a high angle (45-60 degrees pitch) so "
            "platforms cast clear shadows the player uses to judge their jump "
            "landing. Add a fill light from the opposite side."
        ),
        (
            "atmosphere_director",
            "Set sky + light fog for depth cues",
            "Light fog (mode='Linear', start=20, end=80) so far platforms "
            "fade — that's a depth signal the player uses to read the level. "
            "Sky tinted to palette."
        ),
        (
            "camera_director",
            "Side-on platformer camera",
            f"Frame the playfield from the side. unity_set_camera_transform("
            f"name='Main Camera', position_x=0, position_y={platform_spread_y * 0.6:.1f}, "
            f"position_z=-{platform_spread_x * 0.7:.1f}, rotation_x=0). "
            f"Then attach FollowTarget(targetName='Player', smoothing=4.0, "
            f"offset={{'x':0,'y':2,'z':{-platform_spread_x * 0.5:.1f}}})."
        ),
        (
            "material_artist",
            "Player bright + platforms matte + coins gold",
            "Player: smoothness=0.6, emission_enabled=1, emission_intensity=0.5 "
            "(slight glow to read against any platform). Platforms: metallic=0, "
            "smoothness=0.15 (matte, doesn't compete with player). Coins: "
            "metallic=1.0, smoothness=0.85 (gold)."
        ),
        (
            "audio_director",
            "Draft Audio Brief — platformer feel",
            "Bouncy / playful music (90-110 BPM). 4 SFX: jump (whoosh), land "
            "(thud), coin pickup (chime), fall (descending tone). 44.1kHz."
        ),
        (
            "tutorial_designer",
            "Draft tutorial beats",
            "3 beats: Hook=camera pans across platforms with coin glints; "
            "First Action=A/D moves player on flat ground; First Choice=Space "
            "jumps to a high platform with a coin. Skip path: 'Hold Space at "
            "title'."
        ),
        (
            "localization_lead",
            "Seed en + tr string tables",
            f"studio_write_strings('en', strings={{"
            f"'title.main': '{game_name}', 'btn.start': 'Jump In', "
            f"'btn.resume': 'Resume', 'hud.coins': 'Coins: ', "
            f"'hud.lives': 'Lives: ', 'screen.win': 'All Coins!', "
            f"'screen.lose': 'Fell Off', 'screen.pause': 'Paused'"
            f"}}). Translate to 'tr'. Run audit until verdict=pass."
        ),
        (
            "marketing_director",
            "Finalize PlayerSettings + press kit",
            f"unity_set_player_settings(product_name='{game_name}', "
            f"company_name='UnityTools Studio', version='0.1.0', "
            f"bundle_id='com.unitytools.{game_name.lower().replace(' ', '')}'). "
            "Hero shot: capture mid-jump silhouette against a clear sky."
        ),
        (
            "physics_qa",
            "Profile platform-heavy scene",
            f"{platform_count} platforms + {coin_count} coins + a kill plane "
            f"= ~{platform_count + coin_count + 5} renderers. Run "
            f"studio_perf_budget_check. If shadow caster count blows budget, "
            f"file Worker task to disable shadow casting on small coins."
        ),
        (
            "playtester",
            "Smoke-test the jump arc",
            "studio_playtest_smoke(expected_object_names=['Player', "
            "'GameSession', 'KillPlane', 'HUDCanvas']). Verify Player still "
            "exists after 3s (didn't fall + die immediately from a bad spawn)."
        ),
        (
            "game_balancer",
            "Tune jump height + platform spacing",
            f"After playtest, run studio_balance_audit. If "
            f"playtest_failure_rate > 0.5 (player keeps falling), file Worker "
            f"task to either raise jump_height (currently {jump_height}) or "
            f"shrink platform_spread_y. If failure rate < 0.1 (too easy), "
            f"spread platforms further or add narrow platforms."
        ),
        (
            "build_engineer",
            "Ship Windows + WebGL builds",
            f"Run studio_ship_readiness_check. If pass:\n"
            f"  unity_build_player(target='windows', "
            f"output_path='studio/builds/<date>/windows/{game_name.replace(' ', '')}.exe')\n"
            f"  unity_build_player(target='webgl', "
            f"output_path='studio/builds/<date>/webgl/index.html')\n"
            "Platformers ship great as itch.io WebGL demos."
        ),
    ]

    opened: list[dict] = []
    for role, title, description in tasks_spec:
        if role not in ROLES:
            continue
        task = Task(
            title=title,
            role=role,
            description=description,
            milestone=milestone_id,
        )
        state.add_task(task)
        opened.append({"task_id": task.id, "role": task.role, "title": task.title})

    return {
        "ok": True,
        "game_name": game_name,
        "coin_count": coin_count,
        "platform_count": platform_count,
        "jump_height": jump_height,
        "milestone_id": milestone_id,
        "milestone_name": milestone_name,
        "task_count": len(opened),
        "tasks": opened,
    }


@tool(description="Scaffold a complete endless-runner mini-game: drafts a milestone + a structured task batch using AutoScroller + LanePositioner + Spawner + Collectible (so collecting coins-while-running drives the score). Inputs control pacing: scroll_speed, lane_count, obstacle_interval. One Producer call -> a full endless-runner backlog.")
def studio_scaffold_endless_runner_game(
    game_name: str = "Lane Sprinter",
    lane_count: int = 3,
    lane_width: float = 2.0,
    scroll_speed: float = 8.0,
    obstacle_interval: float = 1.5,
    target_score: int = 30,
    win_scene_name: str = "WinScene",
) -> dict:
    state = _require_state()
    if lane_count < 2 or lane_count > 7:
        return {"ok": False, "error": "lane_count must be in 2..7."}
    if lane_width <= 0 or lane_width > 10:
        return {"ok": False, "error": "lane_width must be in (0, 10]."}
    if scroll_speed <= 0 or scroll_speed > 30:
        return {"ok": False, "error": "scroll_speed must be in (0, 30]."}
    if obstacle_interval <= 0 or obstacle_interval > 30:
        return {"ok": False, "error": "obstacle_interval must be in (0, 30]."}
    if target_score < 1 or target_score > 500:
        return {"ok": False, "error": "target_score must be in 1..500."}

    milestone_name = f"Ship MVP: {game_name}"
    milestone = Milestone(
        name=milestone_name,
        description=(
            f"End-to-end endless-runner MVP. Player stays in place, "
            f"switches between {lane_count} lanes via A/D or arrow keys. "
            f"World scrolls at {scroll_speed} u/s via AutoScroller. "
            f"Obstacles + coins spawn every {obstacle_interval}s. Win at "
            f"{target_score} coins -> loads {win_scene_name!r}; collide "
            f"with obstacle -> LoseLife."
        ),
    )
    state.add_milestone(milestone)
    milestone_id = milestone.id

    play_width = lane_count * lane_width   # for camera framing

    tasks_spec: list[tuple[str, str, str]] = [
        (
            "designer",
            f"Draft GDD for {game_name}",
            f"Endless-runner pitch: 'Dodge obstacles, grab coins, "
            f"survive as long as possible to hit {target_score} score.' "
            f"Pillars: 1-thumb control (lane switch only), 60-second "
            f"runs, ramping difficulty. Win scene: {win_scene_name!r}."
        ),
        (
            "art_director",
            "Draft Art Bible — high-contrast lane palette",
            "Endless runners need HIGH contrast between lane / coin / "
            "obstacle / background so the player reads incoming threats "
            "fast at speed. Pick a 4-colour palette with one VERY "
            "saturated obstacle accent (red / orange). Save via "
            "studio_write_art_bible."
        ),
        (
            "worker",
            "Place runner + templates + GameSession + Spawner",
            f"Step-by-step:\n"
            f"1. unity_create_scene_snapshot(label='{{task_id}}_before')\n"
            f"2. Player (stays at z=0, switches lanes):\n"
            f"   unity_create_primitive('Capsule', name='Player')\n"
            f"   unity_set_position(name='Player', x=0, y=1, z=0)\n"
            f"   unity_attach_behaviour('Player', 'LanePositioner',\n"
            f"      params={{'laneCount': {lane_count},\n"
            f"               'laneWidth': {lane_width},\n"
            f"               'startLane': {lane_count // 2},\n"
            f"               'switchDuration': 0.12,\n"
            f"               'useHorizontalAxis': true}})\n"
            f"3. CoinTemplate (cloned by Spawner, AutoScrolled toward player):\n"
            f"   unity_create_primitive('Sphere', name='CoinTemplate')\n"
            f"   unity_set_scale(name='CoinTemplate', uniform=0.5)\n"
            f"   unity_add_component('CoinTemplate', 'SphereCollider')\n"
            f"   (set isTrigger=true)\n"
            f"   unity_attach_behaviour('CoinTemplate', 'Collectible',\n"
            f"      params={{'scoreValue': 1, 'playerFilter': 'Player',\n"
            f"               'destroyOnPickup': true}})\n"
            f"   unity_attach_behaviour('CoinTemplate', 'AutoScroller',\n"
            f"      params={{'direction': {{'x':0,'y':0,'z':-1}},\n"
            f"               'speed': {scroll_speed},\n"
            f"               'despawnPastThreshold': true,\n"
            f"               'despawnAt': -5}})\n"
            f"   unity_attach_behaviour('CoinTemplate', 'Rotator',\n"
            f"      params={{'speedDegPerSec': 120}})\n"
            f"4. ObstacleTemplate (same AutoScroller, but kills the player):\n"
            f"   unity_create_primitive('Cube', name='ObstacleTemplate')\n"
            f"   unity_add_component('ObstacleTemplate', 'BoxCollider')\n"
            f"   (set isTrigger=true)\n"
            f"   unity_attach_behaviour('ObstacleTemplate', 'Enemy',\n"
            f"      params={{'health': 9999, 'scoreOnDeath': 0,\n"
            f"               'contactDamage': 1, 'playerNamePrefix': 'Player'}})\n"
            f"   unity_attach_behaviour('ObstacleTemplate', 'AutoScroller',\n"
            f"      params={{'direction': {{'x':0,'y':0,'z':-1}},\n"
            f"               'speed': {scroll_speed},\n"
            f"               'despawnAt': -5}})\n"
            f"5. CoinSpawner ahead of player on a positive Z:\n"
            f"   unity_create_empty(name='CoinSpawner')\n"
            f"   unity_set_position(name='CoinSpawner', x=0, y=1, z=20)\n"
            f"   unity_attach_behaviour('CoinSpawner', 'Spawner',\n"
            f"      params={{'templateName': 'CoinTemplate',\n"
            f"               'interval': {obstacle_interval * 0.7},\n"
            f"               'maxAlive': 8,\n"
            f"               'spawnRadius': {(lane_count - 1) * lane_width / 2.0:.2f},\n"
            f"               'warmup': 1.5, 'flatXZ': false}})\n"
            f"   (Note: spawnRadius spans the lane band; flatXZ=false lets us tune x-only)\n"
            f"6. ObstacleSpawner ahead too:\n"
            f"   unity_create_empty(name='ObstacleSpawner')\n"
            f"   unity_set_position(name='ObstacleSpawner', x=0, y=1, z=25)\n"
            f"   unity_attach_behaviour('ObstacleSpawner', 'Spawner',\n"
            f"      params={{'templateName': 'ObstacleTemplate',\n"
            f"               'interval': {obstacle_interval},\n"
            f"               'maxAlive': 6,\n"
            f"               'spawnRadius': {(lane_count - 1) * lane_width / 2.0:.2f},\n"
            f"               'warmup': 3.0}})\n"
            f"7. GameSession (3 lives, win at target_score):\n"
            f"   unity_create_empty(name='GameSession')\n"
            f"   unity_attach_behaviour('GameSession', 'GameSession',\n"
            f"      params={{'winScore': {target_score},\n"
            f"               'winSceneName': '{win_scene_name}',\n"
            f"               'startingLives': 3,\n"
            f"               'loseSceneName': 'GameOverScene'}})\n"
            f"8. unity_save_scene(); studio_update_task_status('{{task_id}}', 'done')"
        ),
        (
            "ui_builder",
            "Build runner HUD + pause",
            f"1. unity_create_ui_canvas(name='HUDCanvas')\n"
            f"2. unity_create_ui_text(canvas_name='HUDCanvas', name='ScoreText',\n"
            f"   text='Coins: 0/{target_score}', position_x=-400, position_y=400,\n"
            f"   font_size=42)\n"
            f"3. unity_attach_behaviour('ScoreText', 'ScoreHUD',\n"
            f"   params={{'format': 'Coins: {{score}}/{{win}}'}})\n"
            f"4. unity_create_ui_text(canvas_name='HUDCanvas', name='LivesText',\n"
            f"   text='Lives: 3', position_x=400, position_y=400, font_size=42)\n"
            f"5. unity_attach_behaviour('LivesText', 'ScoreHUD',\n"
            f"   params={{'format': 'Lives: {{lives}}'}})\n"
            f"6. unity_create_ui_canvas(name='PauseCanvas')\n"
            f"7. unity_attach_behaviour('PauseCanvas', 'PauseMenu',\n"
            f"   params={{'toggleKey': 'Escape'}})\n"
            f"8. unity_save_scene()"
        ),
        (
            "lighting_director",
            "Light the runway",
            "Bright key light so obstacles read at speed. Shadow cast "
            "on Player only (Disable on Coin/Obstacle templates to keep "
            "shadow-caster budget under control)."
        ),
        (
            "atmosphere_director",
            "Set sky + fog for depth feel",
            "Heavier fog than collectathon (mode='Linear', start=10, end=40) "
            "so obstacles fade in dramatically. Provides the visual cue "
            "for speed."
        ),
        (
            "camera_director",
            "Behind-player runner camera",
            f"Place camera behind+above Player at offset (0, {lane_width * 1.5:.1f}, "
            f"{-lane_width * 2.0:.1f}). Use unity_set_camera_transform "
            f"(name='Main Camera', position_y={lane_width * 1.5:.1f}, "
            f"position_z={-lane_width * 2.0:.1f}, rotation_x=20). "
            f"Then unity_attach_behaviour('Main Camera', 'FollowTarget', "
            f"params={{'targetName': 'Player', 'smoothing': 5.0, "
            f"'offset': {{'x':0,'y':{lane_width * 1.5:.1f},'z':{-lane_width * 2.0:.1f}}}}})"
        ),
        (
            "material_artist",
            "Coin gold + obstacle warning-red",
            "CoinTemplate: PBR(metallic=1.0, smoothness=0.85). "
            "ObstacleTemplate: emission_enabled=1 with palette accent "
            "(red/orange) and emission_intensity=1.5 so it READS as a "
            "danger signal even at fog distance."
        ),
        (
            "audio_director",
            "Draft Audio Brief — running pace",
            "Upbeat / driving music (110-130 BPM). 3 SFX: lane-switch "
            "swoosh, coin pickup chime, obstacle hit thud. 44.1kHz."
        ),
        (
            "localization_lead",
            "Seed en + tr string tables",
            f"studio_write_strings('en', strings={{"
            f"'title.main': '{game_name}', 'btn.start': 'Run', "
            f"'btn.resume': 'Resume', 'hud.coins': 'Coins: ', "
            f"'hud.lives': 'Lives: ', 'screen.win': 'Course Cleared!', "
            f"'screen.lose': 'Crashed', 'screen.pause': 'Paused'"
            f"}}). Translate to 'tr'. Run audit until verdict=pass."
        ),
        (
            "marketing_director",
            "Finalize PlayerSettings + press kit",
            f"unity_set_player_settings(product_name='{game_name}', "
            f"company_name='UnityTools Studio', version='0.1.0', "
            f"bundle_id='com.unitytools.{game_name.lower().replace(' ', '')}'). "
            "Hero shot: capture mid-lane-switch with obstacle in frame."
        ),
        (
            "physics_qa",
            "Profile under continuous spawn",
            f"Endless runner spawns + despawns constantly. Run "
            f"studio_perf_budget_check after 30s of play. If "
            f"renderer / triangle budget blows due to spawned clones, "
            f"file Worker task to lower Spawner.maxAlive or shrink "
            f"templates."
        ),
        (
            "playtester",
            "Smoke-test the runner",
            "studio_playtest_smoke(expected_object_names=['Player', "
            "'GameSession', 'CoinSpawner', 'ObstacleSpawner', 'HUDCanvas'])"
        ),
        (
            "game_balancer",
            "Tune obstacle interval",
            f"After playtest, run studio_balance_audit. If failure_rate>0.5 "
            f"(player keeps crashing), file task to raise obstacle_interval "
            f"(currently {obstacle_interval}s) or shrink obstacle width. "
            f"If <0.1 (too easy), shrink the interval."
        ),
        (
            "build_engineer",
            "Ship Windows + WebGL builds",
            f"Run studio_ship_readiness_check. If pass, build BOTH:\n"
            f"  unity_build_player(target='windows', "
            f"output_path='studio/builds/<date>/windows/{game_name.replace(' ', '')}.exe')\n"
            f"  unity_build_player(target='webgl', "
            f"output_path='studio/builds/<date>/webgl/index.html')\n"
            f"Endless runners are perfect WebGL fodder."
        ),
    ]

    opened: list[dict] = []
    for role, title, description in tasks_spec:
        if role not in ROLES:
            continue
        task = Task(
            title=title,
            role=role,
            description=description,
            milestone=milestone_id,
        )
        state.add_task(task)
        opened.append({"task_id": task.id, "role": task.role, "title": task.title})

    return {
        "ok": True,
        "game_name": game_name,
        "lane_count": lane_count,
        "lane_width": lane_width,
        "scroll_speed": scroll_speed,
        "obstacle_interval": obstacle_interval,
        "target_score": target_score,
        "milestone_id": milestone_id,
        "milestone_name": milestone_name,
        "task_count": len(opened),
        "tasks": opened,
    }


# ─── Narrative / dialog (Phase 55) ─────────────────────────────────────

_DIALOG_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,30}$")


def _validate_dialog_id(dialog_id: str) -> tuple[bool, str]:
    if not dialog_id:
        return False, "dialog_id is required."
    if not _DIALOG_ID_RE.match(dialog_id):
        return False, (
            f"dialog_id {dialog_id!r} must be lowercase ascii + digits + "
            "underscores, start with a letter, <=31 chars (e.g. 'intro', "
            "'cave_entrance', 'boss_intro')."
        )
    return True, ""


@tool(description="List every dialog file under studio/dialogs/. Returns the id + line count per file. Storyteller uses this to see what's already drafted before adding new scenes.")
def studio_list_dialogs() -> dict:
    state = _require_state()
    base = state.paths.dialogs
    rows: list[dict] = []
    if base.exists():
        for p in sorted(base.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                count = len(data) if isinstance(data, list) else -1
            except (OSError, json.JSONDecodeError):
                count = -1
            rows.append({"dialog_id": p.stem, "path": str(p), "line_count": count})
    return {"ok": True, "count": len(rows), "dialogs": rows}


@tool(description="Read one dialog's lines from studio/dialogs/<dialog_id>.json. Returns the array of strings (ordered, advances on Space in runtime). Empty list if the file is absent. dialog_id is lowercase ASCII + digits + underscores (e.g. 'intro', 'boss_intro').")
def studio_read_dialog(dialog_id: str) -> dict:
    state = _require_state()
    ok, err = _validate_dialog_id(dialog_id)
    if not ok:
        return {"ok": False, "error": err}
    path = state.paths.dialogs / f"{dialog_id}.json"
    if not path.exists():
        return {"ok": True, "dialog_id": dialog_id, "lines": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"{path} is malformed JSON: {exc}"}
    if not isinstance(data, list):
        return {"ok": False, "error": f"{path} must be a flat JSON string array."}
    # Filter to strings only (defensive)
    cleaned = [str(x) for x in data if isinstance(x, str)]
    return {"ok": True, "dialog_id": dialog_id, "lines": cleaned, "line_count": len(cleaned)}


@tool(description="Replace a dialog file at studio/dialogs/<dialog_id>.json with a new ordered string array. Each entry is one line shown to the player; they advance on Space (configurable). dialog_id is lowercase ASCII + digits + underscores; lines is a list of strings.")
def studio_write_dialog(dialog_id: str, lines: list) -> dict:
    state = _require_state()
    ok, err = _validate_dialog_id(dialog_id)
    if not ok:
        return {"ok": False, "error": err}
    if not isinstance(lines, list):
        return {"ok": False, "error": "lines must be a list of strings."}
    for line in lines:
        if not isinstance(line, str):
            return {"ok": False, "error": f"every line must be a string (offender: {line!r})."}
    state.paths.dialogs.mkdir(parents=True, exist_ok=True)
    path = state.paths.dialogs / f"{dialog_id}.json"
    payload = json.dumps(list(lines), ensure_ascii=False, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    return {"ok": True, "dialog_id": dialog_id, "path": str(path), "line_count": len(lines)}


# ─── Localization (Phase 39) ───────────────────────────────────────────

_LOCALE_CODE_RE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")


def _validate_locale(locale: str) -> tuple[bool, str]:
    if not locale:
        return False, "locale is required."
    if not _LOCALE_CODE_RE.match(locale):
        return False, (
            f"locale {locale!r} should be a 2-letter code like 'en' or "
            "'pt-BR' (lowercase region, uppercase country)."
        )
    return True, ""


@tool(description="List every locale string-table file under studio/strings/. Each row reports the locale code, JSON path, and key count. Empty list if the directory doesn't exist yet.")
def studio_list_locales() -> dict:
    state = _require_state()
    base = state.paths.strings
    rows: list[dict] = []
    if base.exists():
        for p in sorted(base.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                count = len(data) if isinstance(data, dict) else 0
            except (OSError, json.JSONDecodeError):
                count = -1  # signal a malformed table
            rows.append({"locale": p.stem, "path": str(p), "key_count": count})
    return {"ok": True, "count": len(rows), "locales": rows}


@tool(description="Read one locale's string table from studio/strings/<locale>.json. Returns the {key: value} mapping. Empty dict if the file is absent. locale is a 2-letter code like 'en' or 'pt-BR'.")
def studio_read_strings(locale: str) -> dict:
    state = _require_state()
    ok, err = _validate_locale(locale)
    if not ok:
        return {"ok": False, "error": err}
    path = state.paths.strings / f"{locale}.json"
    if not path.exists():
        return {"ok": True, "locale": locale, "strings": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"{path} is malformed JSON: {exc}"}
    if not isinstance(data, dict):
        return {"ok": False, "error": f"{path} must be a JSON object."}
    return {"ok": True, "locale": locale, "strings": data, "key_count": len(data)}


@tool(description="Replace or merge a locale's string table at studio/strings/<locale>.json. strings is a flat {key: value} mapping. When mode='merge' (default), existing keys not in the new dict are preserved; mode='replace' wipes the file first. locale is a 2-letter code.")
def studio_write_strings(locale: str, strings: dict, mode: str = "merge") -> dict:
    state = _require_state()
    ok, err = _validate_locale(locale)
    if not ok:
        return {"ok": False, "error": err}
    if not isinstance(strings, dict):
        return {"ok": False, "error": "strings must be a dict."}
    if mode not in ("merge", "replace"):
        return {"ok": False, "error": f"mode must be 'merge' or 'replace'; got {mode!r}."}
    # Validate values are all strings
    for k, v in strings.items():
        if not isinstance(k, str) or not isinstance(v, str):
            return {"ok": False, "error": f"all keys + values must be strings (offender: {k!r})."}
    state.paths.strings.mkdir(parents=True, exist_ok=True)
    path = state.paths.strings / f"{locale}.json"
    merged: dict[str, str] = {}
    if mode == "merge" and path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                merged.update({k: v for k, v in existing.items() if isinstance(k, str) and isinstance(v, str)})
        except json.JSONDecodeError:
            # Stale / malformed file: replace it on this write
            pass
    merged.update(strings)
    # Sort keys deterministically for stable diffs
    payload = json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return {"ok": True, "locale": locale, "path": str(path), "key_count": len(merged), "mode": mode}


@tool(description="Audit the localization coverage: compares every other locale's keys to the chosen base_locale (default 'en'). Returns per-locale missing-key counts + sample names. No mutations.")
def studio_localization_audit(base_locale: str = "en") -> dict:
    state = _require_state()
    base = state.paths.strings
    if not base.exists():
        return {"ok": True, "base_locale": base_locale, "verdict": "fail",
                "violations": ["no_strings_dir"], "recommendations": [
                    "studio/strings/ doesn't exist; create at least one locale "
                    f"via studio_write_strings(locale='{base_locale}', strings={{...}})."
                ], "locales": []}
    base_path = base / f"{base_locale}.json"
    if not base_path.exists():
        return {"ok": True, "base_locale": base_locale, "verdict": "fail",
                "violations": [f"base_locale_missing:{base_locale}"], "recommendations": [
                    f"Base locale {base_locale!r} has no string table; create it first."
                ], "locales": []}
    try:
        base_data = json.loads(base_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"{base_path} is malformed: {exc}"}
    if not isinstance(base_data, dict):
        return {"ok": False, "error": f"{base_path} must be a JSON object."}
    base_keys = set(base_data.keys())

    other_rows: list[dict] = []
    violations: list[str] = []
    for p in sorted(base.glob("*.json")):
        if p.stem == base_locale:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            other_rows.append({"locale": p.stem, "key_count": -1, "missing_count": -1, "missing_keys": []})
            violations.append(f"malformed:{p.stem}")
            continue
        if not isinstance(data, dict):
            other_rows.append({"locale": p.stem, "key_count": -1, "missing_count": -1, "missing_keys": []})
            violations.append(f"not_object:{p.stem}")
            continue
        missing = sorted(base_keys - set(data.keys()))
        if missing:
            violations.append(f"missing_keys:{p.stem}:{len(missing)}")
        other_rows.append({
            "locale": p.stem,
            "key_count": len(data),
            "missing_count": len(missing),
            "missing_keys": missing[:10],   # sample
        })

    verdict = "pass" if not violations else "fail"
    return {
        "ok": True,
        "base_locale": base_locale,
        "verdict": verdict,
        "base_key_count": len(base_keys),
        "violations": violations,
        "locales": other_rows,
        "recommendations": [
            f"Use studio_write_strings(locale='<code>', strings={{...}}) to add the missing keys."
        ] if violations else [],
    }


# ─── Balance audit (Phase 38) ──────────────────────────────────────────

@tool(description="Aggregate the last `days` of regression data into balance-relevant signals: how many playtest smokes ran, which named objects went missing most often, vision-compare scores trending (composition_match average), recent perf budget violations. Read-only — the Game Balancer reads this and files specific tuning tasks. Use to answer 'what's going wrong recently?'.")
def studio_balance_audit(days: float = 7.0, max_top_offenders: int = 5) -> dict:
    state = _require_state()
    path = state.paths.qa_regression
    if not path.exists():
        return {
            "ok": True,
            "days": days,
            "total_entries": 0,
            "playtest_smokes": 0,
            "playtest_failures": 0,
            "missing_objects": {},
            "top_missing_objects": [],
            "vision_compares": 0,
            "avg_composition_match": None,
            "avg_palette_match": None,
            "asset_generations": 0,
            "perf_violations": 0,
            "recent_perf_violation_kinds": [],
        }
    cutoff = time.time() - max(0.0, float(days)) * 86400.0
    missing_counter: dict[str, int] = {}
    playtest_total = 0
    playtest_failures = 0
    composition_scores: list[float] = []
    palette_scores: list[float] = []
    vision_total = 0
    asset_generations = 0
    perf_violations = 0
    perf_kinds: list[str] = []
    total_entries = 0

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
                total_entries += 1
                kind = entry.get("kind", "")
                if kind == "playtest_smoke":
                    playtest_total += 1
                    missing = entry.get("missing") or []
                    if missing:
                        playtest_failures += 1
                    for name in missing:
                        if isinstance(name, str) and name:
                            missing_counter[name] = missing_counter.get(name, 0) + 1
                elif kind == "vision_compare":
                    vision_total += 1
                    cm = entry.get("composition_match")
                    pm = entry.get("palette_match")
                    if isinstance(cm, (int, float)):
                        composition_scores.append(float(cm))
                    if isinstance(pm, (int, float)):
                        palette_scores.append(float(pm))
                elif kind == "asset_generated":
                    asset_generations += 1
                elif kind == "perf_budget_violation":
                    perf_violations += 1
                    metric = entry.get("metric") or entry.get("violation") or ""
                    if metric:
                        perf_kinds.append(str(metric))
    except OSError as exc:
        return {"ok": False, "error": f"Could not read regression log: {exc}"}

    top = sorted(missing_counter.items(), key=lambda kv: kv[1], reverse=True)[:max(1, int(max_top_offenders))]
    avg_comp = (sum(composition_scores) / len(composition_scores)) if composition_scores else None
    avg_pal = (sum(palette_scores) / len(palette_scores)) if palette_scores else None

    return {
        "ok": True,
        "days": days,
        "total_entries": total_entries,
        "playtest_smokes": playtest_total,
        "playtest_failures": playtest_failures,
        "playtest_failure_rate": (playtest_failures / playtest_total) if playtest_total else 0.0,
        "missing_objects": missing_counter,
        "top_missing_objects": [{"name": n, "missing_count": c} for n, c in top],
        "vision_compares": vision_total,
        "avg_composition_match": round(avg_comp, 4) if avg_comp is not None else None,
        "avg_palette_match": round(avg_pal, 4) if avg_pal is not None else None,
        "asset_generations": asset_generations,
        "perf_violations": perf_violations,
        "recent_perf_violation_kinds": perf_kinds[-10:],
    }


# ─── Asset manifest (Phase 37) ─────────────────────────────────────────

@tool(description="Inventory the studio's asset directories: studio/refs/, studio/refs/audio/, studio/qa/screenshots/, studio/assets/generated/, studio/builds/. Returns counts + total bytes per bucket + the 10 newest files in each. Read-only; no Unity calls.")
def studio_asset_manifest() -> dict:
    state = _require_state()
    paths = state.paths

    def _scan(directory: Path, exts: tuple[str, ...] = ()) -> dict:
        if not directory.exists():
            return {"count": 0, "total_bytes": 0, "newest": []}
        rows: list[dict] = []
        for p in directory.rglob("*"):
            if not p.is_file():
                continue
            if exts and p.suffix.lower() not in exts:
                continue
            try:
                stat = p.stat()
            except OSError:
                continue
            rows.append({
                "path": str(p.relative_to(paths.root)) if p.is_relative_to(paths.root) else str(p),
                "size_bytes": stat.st_size,
                "mtime": stat.st_mtime,
            })
        rows.sort(key=lambda r: r["mtime"], reverse=True)
        total = sum(r["size_bytes"] for r in rows)
        return {
            "count": len(rows),
            "total_bytes": total,
            "newest": [{k: v for k, v in r.items() if k != "mtime"} for r in rows[:10]],
        }

    image_exts = (".png", ".jpg", ".jpeg", ".tga", ".webp", ".bmp")
    audio_exts = (".wav", ".mp3", ".ogg", ".aiff", ".flac")
    mesh_exts = (".fbx", ".obj", ".glb", ".gltf", ".blend")
    build_exts = (".exe", ".app", ".x86_64", ".apk", ".ipa", ".html", ".js", ".wasm", ".data")

    refs_audio = paths.refs / "audio"
    return {
        "ok": True,
        "project_root": str(paths.root),
        "references": _scan(paths.refs, image_exts),
        "audio_references": _scan(refs_audio, audio_exts),
        "screenshots": _scan(paths.qa_screenshots, image_exts),
        "generated_assets": _scan(paths.root / "assets" / "generated", mesh_exts),
        "builds": _scan(paths.root / "builds", build_exts),
    }


# ─── Atmosphere audit (Phase 35) ───────────────────────────────────────

@tool(description="Audit the scene's atmosphere against soft expectations: skybox present, fog state coherent with mode (Linear needs distances; Exp needs density). Returns verdict + violations + recommendations. No mutations.")
def studio_atmosphere_audit() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor is not connected."}
    try:
        state = _UNITY.call("get_atmosphere_state", {}, timeout=15)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"get_atmosphere_state failed: {exc}", "error_type": type(exc).__name__}
    if not isinstance(state, dict):
        return {"ok": False, "error": "Unity returned non-dict.", "raw": state}

    violations: list[str] = []
    recommendations: list[str] = []
    if not state.get("skybox_present"):
        violations.append("no_skybox")
        recommendations.append(
            "Scene has no skybox material; call unity_set_skybox(material_path='') "
            "for a tuned procedural sky."
        )
    fog_mode = (state.get("fog_mode") or "").lower()
    fog_enabled = bool(state.get("fog_enabled", False))
    fog_density = float(state.get("fog_density", 0.0))
    fog_start = float(state.get("fog_start_distance", 0.0))
    fog_end = float(state.get("fog_end_distance", 0.0))
    if fog_enabled:
        if fog_mode == "linear" and fog_end <= fog_start:
            violations.append("fog_linear_distances_inverted")
            recommendations.append(
                f"Linear fog has end_distance ({fog_end}) <= start_distance ({fog_start}); "
                "set start < end (typical: start=10, end=80)."
            )
        if fog_mode in ("exponential", "exponentialsquared") and fog_density <= 0.0:
            violations.append("fog_exp_density_zero")
            recommendations.append(
                "Exponential fog is enabled but density is 0; pick a small value (0.01–0.05)."
            )
    verdict = "pass" if not violations else "fail"
    return {
        "ok": True,
        "verdict": verdict,
        "skybox_present": bool(state.get("skybox_present", False)),
        "skybox_shader": state.get("skybox_shader", ""),
        "fog_enabled": fog_enabled,
        "fog_mode": state.get("fog_mode", ""),
        "fog_density": fog_density,
        "fog_start_distance": fog_start,
        "fog_end_distance": fog_end,
        "violations": violations,
        "recommendations": recommendations,
    }


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

@tool(description="Generate a procedural prop via Blender (AI asset layer) and write a DOCS-contract slot package (final.fbx + preview.png + notes.md) under studio/assets/generated/<name>/. Primitive set: rock/crate/pillar/column. Briar Hollow environment set (art-bible aligned): boulder/stump/deadtrunk/totem/shrine/gate/bench/banner/rack. Deterministic per seed. If import_into_unity=True, imports the FBX into Unity (fixed: uses the correct bridge param contract). Returns slot paths so the Worker can chain placement.")
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
    supported = getattr(_BLENDER, "SUPPORTED_PROP_TYPES",
                        ("rock", "crate", "pillar", "column"))
    if not prop_type or prop_type not in supported:
        return {"ok": False,
                "error": f"prop_type must be one of {', '.join(supported)}; got {prop_type!r}."}

    # Slot package per blender-realism-pipeline DOCS contract:
    #   <name>/final.fbx + preview.png + notes.md
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or f"{prop_type}_{seed}")).strip("_")
    if not safe_name:
        safe_name = f"{prop_type}_{seed}"
    slot_dir = state.paths.root / "assets" / "generated" / safe_name
    slot_dir.mkdir(parents=True, exist_ok=True)
    output_path = slot_dir / "final.fbx"
    preview_path = slot_dir / "preview.png"
    notes_path = slot_dir / "notes.md"

    result = _BLENDER.generate_prop(
        prop_type=prop_type,
        output_path=str(output_path),
        seed=seed,
        scale=scale,
        preview_path=str(preview_path),
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

    # Slot package: notes.md (DOCS contract) so the slot is auditable.
    has_preview = preview_path.exists()
    try:
        notes_path.write_text(
            f"# {safe_name}\n\n"
            f"- prop_type: `{prop_type}`\n"
            f"- seed: `{int(seed)}`\n"
            f"- scale: `{scale}`\n"
            f"- generator: `scripts/blender/generate_prop.py` (Blender, AI layer)\n"
            f"- final: `final.fbx` ({output_path.stat().st_size} bytes)\n"
            f"- preview: `{'preview.png' if has_preview else '(none)'}`\n"
            f"- source line: AI environment/blockout (DOCS blender-realism-pipeline AI usage line)\n"
            f"- palette: Briar Hollow art bible (wet earth / moss / ash)\n",
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass

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
        "slot_dir": str(slot_dir),
        "fbx_path": str(output_path),
        "preview_path": str(preview_path) if has_preview else None,
        "notes_path": str(notes_path),
        "size_bytes": output_path.stat().st_size,
    }

    # Optional Unity import. NOTE: the bridge ImportAsset handler wants
    # `src_path` + `dst_relative` (relative to Assets/, including the
    # filename) — the old source_path/destination params silently failed.
    if import_into_unity:
        if _UNITY is None:
            payload["unity_import"] = {"ok": False, "error": "Unity bridge not injected."}
        elif hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
            payload["unity_import"] = {"ok": False, "error": "Unity Editor is not connected."}
        else:
            dst_rel = unity_destination.replace("\\", "/").strip("/")
            if dst_rel.lower().startswith("assets/"):
                dst_rel = dst_rel[len("assets/"):]
            dst_rel = f"{dst_rel}/{safe_name}.fbx"
            try:
                imp = _UNITY.call(
                    "import_asset",
                    {"src_path": str(output_path), "dst_relative": dst_rel},
                    timeout=120,
                )
                payload["unity_import"] = imp if isinstance(imp, dict) else {"ok": True, "result": imp}
                payload["unity_asset_path"] = f"Assets/{dst_rel}"
            except Exception as exc:  # noqa: BLE001
                payload["unity_import"] = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
    return payload


# ─── Lightweight Blender forest (Phase 113) ────────────────────────────

@tool(description="Replace the heavy PolyHaven GLB forest (which tanked HDRP) with a CHEAP Blender-generated low-poly conifer forest. Generates pine/fir/deadpine via Blender (~200-400 tris, 1 mesh, 2 mats each), imports them once into Unity, then scatters them across the terrain's mid band with GPU instancing + cheap HDRP trunk/needle materials. tree_count default 150. This is the performance fix for the laggy HDRP forest.")
def studio_build_lowpoly_forest(tree_count: int = 150,
                                scene: str = "Assets/Scenes/ForgottenValley_VS.unity",
                                seed: int = 11) -> dict:
    state = _require_state()
    if _BLENDER is None or not _BLENDER.is_available():
        return {"ok": False, "error": "Blender unavailable; set BLENDER_EXECUTABLE."}
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}

    def call(cmd, params, timeout=180):
        try:
            return _UNITY.call(cmd, params, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:160]}

    call("open_scene", {"path": scene})

    # 1) Generate the 3 low-poly tree variants via Blender + import.
    # Resilient: the Blender step is reliable but the Unity import can
    # transiently fail when the editor is busy post-recompile. Retry
    # each, and proceed with whatever variants succeeded (a forest of
    # just pine is fine; only hard-fail if NOTHING imported).
    variants = [("LP_Pine", "pine", 11), ("LP_Fir", "fir", 22),
                ("LP_DeadPine", "deadpine", 33)]
    paths = {}
    for nm, ptype, sd in variants:
        for attempt in range(3):
            gen = studio_generate_prop_asset(
                prop_type=ptype, name=nm, seed=sd, scale=1.0,
                import_into_unity=True,
                unity_destination="Assets/Studio/Generated")
            if gen.get("ok") and gen.get("unity_asset_path"):
                paths[ptype] = gen["unity_asset_path"]
                break
            time.sleep(6)  # let Unity settle, then retry the import
    if not paths:
        return {"ok": False, "error": "all tree gens failed",
                "detail": gen.get("error", "")[:160] if isinstance(gen, dict) else ""}
    # Fill any missing variant with an available one so the scatter
    # always has live + dead pools.
    any_path = next(iter(paths.values()))
    paths.setdefault("pine", any_path)
    paths.setdefault("fir", paths["pine"])
    paths.setdefault("deadpine", paths["pine"])

    _GM = "Assets/FantasyRPG/Generated/Materials/"
    # 2) Scatter them cheap (GPU-instanced, per-slot HDRP materials).
    res = call("scatter_terrain_glb_trees", {
        "tree_count": tree_count, "forest_min": 0.05, "forest_max": 0.92,
        "max_slope_deg": 55, "scale_min": 1.4, "scale_max": 3.0,
        "dead_ratio": 0.14, "seed": seed, "clear_primitive_forest": True,
        "models": [paths["pine"], paths["fir"]],
        "dead_models": [paths["deadpine"]],
        "trunk_material_path": _GM + "HDRP_M_WetAgedWood.mat",
        "foliage_material_path": _GM + "HDRP_M_BlackPineNeedles.mat",
        "gpu_instancing": True,
    }, timeout=240)
    call("save_scene", {})
    state.append_regression_entry({"ts": time.time(),
                                   "kind": "lowpoly_forest",
                                   "placed": res.get("placed") if isinstance(res, dict) else 0})
    return {"ok": isinstance(res, dict) and bool(res.get("ok")),
            "scatter": res, "models": paths,
            "note": "cheap Blender low-poly conifer forest (HDRP perf fix)"}


# ─── DOCS-driven AI world-asset layer (Phase 108) ──────────────────────

@tool(description="AI learning layer: read the Briar Hollow slice's required environment props (level-instance-links.md anchors + art bible) and MANUFACTURE them in 3D via Blender, import each into Unity, and place each on the terrain surface at its level anchor. This is the intelligence layer that lets the AI generate its own DOCS-driven 3D assets instead of using only pre-bought packs. dry_run=True only reports the manifest. Stays within the DOCS AI-usage line (environment/blockout, not final hero/boss meshes).")
def studio_generate_world_assets(dry_run: bool = False,
                                 scene: str = "Assets/Scenes/ForgottenValley_VS.unity",
                                 base_object: str = "SK_Hero") -> dict:
    state = _require_state()
    if _BLENDER is None or not _BLENDER.is_available():
        return {"ok": False, "error": "Blender bridge unavailable; set BLENDER_EXECUTABLE."}
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not injected."}

    # Briar Hollow vertical-slice prop manifest, derived from
    # level-instance-links.md (Camp -> 3 Offerings -> SoulShrine ->
    # BossGate -> BossArena loop) + art-bible atmosphere layers.
    # (slot, prop_type, scale, dx, dz, seed)  — dx/dz are metres from base.
    MANIFEST = [
        ("SoulShrine_OldRoots", "shrine",    2.2,   56,  44, 401),
        ("BossGate_RootVeil",   "gate",      2.6,   84,  66, 402),
        ("RestTotem_Bridge",    "totem",     1.6,   28,  20, 403),
        ("RestTotem_Shrine",    "totem",     1.6,   52,  40, 404),
        ("CraftingBench_Camp",  "bench",     1.3,   14,   8, 405),
        ("WarBanner_Camp",      "banner",    1.5,   18,  12, 406),
        ("WeaponRack_Camp",     "rack",      1.2,   12,  14, 407),
        ("Atmo_DeadTrunk_A",    "deadtrunk", 2.0,   38,  30, 408),
        ("Atmo_DeadTrunk_B",    "deadtrunk", 2.4,   70,  54, 409),
        ("Atmo_Boulder_A",      "boulder",   2.2,   24,  34, 410),
        ("Atmo_Boulder_B",      "boulder",   3.0,   64,  48, 411),
        ("Atmo_Stump_A",        "stump",     1.6,   20,  26, 412),
    ]
    if dry_run:
        return {"ok": True, "dry_run": True, "count": len(MANIFEST),
                "manifest": [
                    {"slot": s, "type": t, "scale": sc, "dx": dx, "dz": dz}
                    for (s, t, sc, dx, dz, _sd) in MANIFEST]}

    def call(cmd, params, timeout=120):
        try:
            return _UNITY.call(cmd, params, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:160]}

    call("open_scene", {"path": scene})

    # Base anchor = the hero spawn (good playable ground). Pass the
    # hero's elevation as ref_y so each prop snaps to ground near the
    # playable band (not the underwater valley floor the blind offsets
    # used to hit), and min_surface_y keeps them above the water plane.
    bx, by, bz = 225.0, 57.0, 75.0
    info = call("get_object_details", {"name": base_object})
    if isinstance(info, dict):
        pos = info.get("position") or {}
        if isinstance(pos, dict) and "x" in pos:
            bx, by, bz = float(pos["x"]), float(pos.get("y", 57.0)), float(pos["z"])
    min_sy = by - 25.0  # keep props within the playable elevation band

    results = []
    for (slot, ptype, pscale, dx, dz, seed) in MANIFEST:
        gen = studio_generate_prop_asset(
            prop_type=ptype, name=slot, seed=seed, scale=pscale,
            import_into_unity=True,
            unity_destination="Assets/Studio/Generated",
        )
        row = {"slot": slot, "type": ptype, "generated": bool(gen.get("ok"))}
        if not gen.get("ok"):
            row["error"] = gen.get("error", "")[:160]
            results.append(row)
            continue
        asset_path = gen.get("unity_asset_path")
        ui = gen.get("unity_import")
        row["imported"] = bool(isinstance(ui, dict) and ui.get("ok", True)) and bool(asset_path)
        if asset_path:
            # FBX-from-Blender materials render wrong in HDRP -> force a
            # known-good art-bible HDRP material by prop category so the
            # AI props never import white.
            _GM = "Assets/FantasyRPG/Generated/Materials/"
            _stone = {"shrine", "gate", "totem", "boulder"}
            _wood = {"bench", "banner", "rack"}
            if ptype in _stone:
                mat = _GM + "HDRP_M_WetRock.mat"
            elif ptype in _wood:
                mat = _GM + "HDRP_M_WetAgedWood.mat"
            else:  # stump / deadtrunk -> bark
                mat = _GM + "HDRP_M_WetAgedWood.mat"
            placed = call("place_asset_on_terrain", {
                "asset_path": asset_path, "name": slot,
                "x": bx + dx, "z": bz + dz,
                "rot_y": (seed * 37) % 360, "scale": 1.0,
                "parent": "WorldGeneratedProps",
                "material_path": mat,
                "ref_y": by, "min_surface_y": min_sy,
                "max_slope_deg": 34, "search_radius": 160,
            })
            row["placed"] = bool(isinstance(placed, dict) and placed.get("ok"))
            row["place"] = placed if isinstance(placed, dict) else {}
        results.append(row)

    call("save_scene", {})
    ok_n = sum(1 for r in results if r.get("placed"))
    state.append_regression_entry({"ts": time.time(),
                                   "kind": "world_assets_generated",
                                   "placed": ok_n, "total": len(MANIFEST)})
    return {"ok": True, "placed": ok_n, "total": len(MANIFEST),
            "results": results,
            "note": "AI-manufactured Briar Hollow env props (Blender -> Unity -> terrain)"}


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


@tool(description="Phase 96: intelligent world-realism orchestrator. Composes ALREADY-COMPILED bridge handlers (no C# recompile) into one smart pass that makes the real-world terrain look real: naturalistic biome repaint, a water plane filling the low valleys, sparse valley forest, HDRP Automatic adaptive exposure + scaled fog, and a smart interior camera (never shows the void edge). Reads scene state and adapts. The 'intelligence layer' — reasoning + composition over primitives instead of a new handler per step.")
def studio_realize_world(
    water_level: float = 0.10,
    forest_count: int = 240,
    relief_m: float = 1168.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "Unity bridge not wired"}
    if hasattr(_UNITY, "is_connected") and not _UNITY.is_connected():
        return {"ok": False, "error": "Unity Editor not connected"}

    def call(cmd, params, timeout=120):
        try:
            return _UNITY.call(cmd, params, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:160]}

    layers: list[dict] = []
    call("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"})

    # 0) ENSURE A SUN. Root cause of the white/black/pale variance all
    # session: the scene often had NO directional light at all (cleared
    # by rebuilds), so exposure was meaningless. A proper HDRP daylight
    # sun + Fixed exposure 13 is the locked-in recipe that produced the
    # believable green terrain. Idempotent (create if missing, then set).
    lights = call("list_lights", {})
    if isinstance(lights, dict) and lights.get("count", 0) == 0:
        call("create_light", {"name": "Sun", "light_type": "Directional",
                              "position_x": 0, "position_y": 500, "position_z": 0,
                              "r": 1.0, "g": 0.96, "b": 0.88,
                              "intensity": 1.0, "range_val": 200})
        call("set_rotation", {"name": "Sun", "x": 48, "y": -34, "z": 0})
    call("set_light_properties", {"name": "Sun", "intensity": 22000.0,
                                  "shadows_enabled": 1, "shadow_strength": 0.7})
    layers.append({"sun": "ensured (HDRP daylight 22000 lux)"})

    # scene state — find the terrain root + its world position
    roots = call("list_root_objects", {})
    terr = None
    for r in (roots.get("roots", []) if isinstance(roots, dict) else []):
        if r.get("name") == "WorldTerrain":
            terr = r
            break
    if terr is None:
        return {"ok": False, "error": "WorldTerrain not in scene", "roots": roots}
    tx, ty, tz = terr.get("pos", [-8000.0, 0.0, -8000.0])
    foot = abs(tx) * 2.0 if tx < 0 else 16000.0    # corner-origin convention
    cx, cz = tx + foot / 2.0, tz + foot / 2.0

    # 1) Ground. Intelligence layer: prefer REAL 2K PBR ground/rock
    # layers (diffuse+normal) chosen to match the Briar Hollow art
    # bible palette (moss green -> wet dark earth -> mossy rock ->
    # burnt grey rock). Fall back to solid-colour biome splat if the
    # PBR handler isn't compiled yet or a texture is missing.
    _tx = "Assets/FantasyRPG/Textures"
    pbr = call("apply_terrain_pbr_layers", {
        "cutoffs": [0.34, 0.62, 0.88],
        "layers": [
            {"name": "Moss",     "tile": 10,
             "diffuse": f"{_tx}/Ground/Ground037/Ground037_2K-JPG_Color.jpg",
             "normal":  f"{_tx}/Ground/Ground037/Ground037_2K-JPG_NormalGL.jpg"},
            {"name": "WetEarth", "tile": 11,
             "diffuse": f"{_tx}/Ground/Ground103/Ground103_2K-JPG_Color.jpg",
             "normal":  f"{_tx}/Ground/Ground103/Ground103_2K-JPG_NormalGL.jpg"},
            {"name": "MossRock", "tile": 13,
             "diffuse": f"{_tx}/Rock/Rock063/Rock063_2K-JPG_Color.jpg",
             "normal":  f"{_tx}/Rock/Rock063/Rock063_2K-JPG_NormalGL.jpg"},
            {"name": "DarkRock", "tile": 15,
             "diffuse": f"{_tx}/Rock/Rock058/Rock058_2K-JPG_Color.jpg",
             "normal":  f"{_tx}/Rock/Rock058/Rock058_2K-JPG_NormalGL.jpg"},
        ],
    }, timeout=180)
    if isinstance(pbr, dict) and pbr.get("ok"):
        layers.append({"biomes": pbr, "biome_kind": "real_pbr"})
    else:
        layers.append({"biomes_pbr_skipped": pbr})
        layers.append({"biomes": call("repaint_terrain_biomes", {
            "plains_to": 0.34, "forest_to": 0.66, "rock_to": 0.90,
            "plains_color": [0.33, 0.44, 0.22],
            "forest_color": [0.16, 0.30, 0.15],
            "rock_color": [0.42, 0.40, 0.37],
            "snow_color": [0.92, 0.94, 0.97],
        }), "biome_kind": "solid_fallback"})

    # 2) Water plane filling the low valleys (the big realism jump)
    wy = ty + water_level * relief_m
    call("create_primitive", {"type": "Plane", "name": "WorldWater",
                              "position_x": cx, "position_y": wy, "position_z": cz})
    call("set_scale", {"name": "WorldWater", "x": foot / 10.0, "y": 1.0,
                       "z": foot / 10.0})
    call("set_material_color", {"name": "WorldWater", "r": 0.05, "g": 0.19,
                                "b": 0.27, "a": 1.0})
    layers.append({"water": {"y": wy, "footprint": foot}})

    # 3) Sparse valley forest. PERF: the heavy PolyHaven GLB trees
    # (multi-hundred renderers each) tanked HDRP, so prefer the CHEAP
    # Blender low-poly conifers (1 mesh / 2 mats, GPU-instanced) if
    # they've been generated into Assets/Studio/Generated; gracefully
    # fall back to procedural pines (still cheap) otherwise. The heavy
    # PolyHaven path is intentionally retired from the main pipeline.
    _GM = "Assets/FantasyRPG/Generated/Materials/"
    lp = call("scatter_terrain_glb_trees", {
        "tree_count": forest_count, "forest_min": 0.05, "forest_max": 0.92,
        "max_slope_deg": 55, "scale_min": 1.4, "scale_max": 3.0,
        "dead_ratio": 0.14, "seed": 11, "clear_primitive_forest": True,
        "models": ["Assets/Studio/Generated/LP_Pine.fbx",
                   "Assets/Studio/Generated/LP_Fir.fbx"],
        "dead_models": ["Assets/Studio/Generated/LP_DeadPine.fbx"],
        "trunk_material_path": _GM + "HDRP_M_WetAgedWood.mat",
        "foliage_material_path": _GM + "HDRP_M_BlackPineNeedles.mat",
        "gpu_instancing": True,
    })
    if isinstance(lp, dict) and lp.get("ok") and lp.get("placed", 0) > 0:
        layers.append({"forest": lp, "forest_kind": "lowpoly_blender"})
    else:
        layers.append({"forest_lowpoly_skipped": lp})
        layers.append({"forest": call("scatter_terrain_trees", {
            "tree_count": forest_count, "forest_min": 0.14, "forest_max": 0.52,
            "max_slope_deg": 33, "scale_min": 8, "scale_max": 16, "seed": 11,
        }), "forest_kind": "procedural_fallback"})

    # 4) Fixed exposure 16 — ROOT CAUSE of the long "pale ground"
    # saga: EV 13 with the 22000-lux sun blows out real 2K PBR albedo
    # to flat pale (solid-colour biomes never blew out, which is why
    # earlier shots looked green and masked this). HDRP Fixed EV is
    # inverted (higher = darker); an exposure sweep showed EV~16 is
    # the balanced natural-daylight point where the moss/wet-earth/
    # rock textures actually read. The terrain DATA was correct all
    # along (list_terrains: 4 PBR layers + HDRP/TerrainLit).
    layers.append({"exposure": call("setup_hdrp_volume", {
        "exposure_mode": "Fixed", "fixed_exposure": 16.0,
        "fog": True, "fog_distance": 2200,
    })})

    # 5) Smart interior camera (auto-frames terrain; never the void edge)
    layers.append({"camera": call("setup_smart_camera", {
        "target": "WorldTerrain", "pitch": 32, "yaw": 40, "distance_factor": 0.55,
    })})

    call("save_scene", {})
    ok = all(
        (list(l.values())[0] or {}).get("ok", True)
        if isinstance(list(l.values())[0], dict) else True
        for l in layers
    )
    return {
        "ok": True,
        "applied_ok": ok,
        "terrain_center": [cx, ty, cz],
        "footprint_m": foot,
        "water_y": wy,
        "layers": layers,
        "note": "composed compiled handlers — biomes+water+forest+adaptive-exposure+smart-cam",
    }


# ─── Convenience: list of all studio tool names (used by RoleConfig) ───

ALL_STUDIO_TOOL_NAMES: tuple[str, ...] = (
    # docs
    "studio_read_gdd",
    "studio_write_gdd",
    "studio_read_art_bible",
    "studio_write_art_bible",
    "studio_read_audio_brief",
    "studio_write_audio_brief",
    "studio_read_press_kit",
    "studio_write_press_kit",
    "studio_read_tutorial",
    "studio_write_tutorial",
    "studio_read_scene_catalog",
    "studio_write_scene_catalog",
    "studio_read_achievements",
    "studio_write_achievements",
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
    # atmosphere (Phase 35)
    "studio_atmosphere_audit",
    # marketing / press kit (Phase 37)
    "studio_asset_manifest",
    # balance (Phase 38)
    "studio_balance_audit",
    # localization (Phase 39)
    "studio_list_locales",
    "studio_read_strings",
    "studio_write_strings",
    "studio_localization_audit",
    # narrative / dialog (Phase 55)
    "studio_list_dialogs",
    "studio_read_dialog",
    "studio_write_dialog",
    # game template scaffolder (Phase 42)
    "studio_scaffold_collectathon_game",
    # game template scaffolder (Phase 44)
    "studio_scaffold_top_down_shooter_game",
    # game template scaffolder (Phase 46)
    "studio_scaffold_endless_runner_game",
    # game template scaffolder (Phase 50)
    "studio_scaffold_platformer_game",
    # ship readiness (Phase 45)
    "studio_ship_readiness_check",
    # internal consistency audit (Phase 49)
    "studio_internal_consistency_check",
    # studio dashboard (Phase 58)
    "studio_dashboard",
    # studio sync (Phase 63)
    "studio_sync",
    # recent activity
    "studio_recent_regressions",
    "studio_recent_commits",
    "studio_query_archive",
)
