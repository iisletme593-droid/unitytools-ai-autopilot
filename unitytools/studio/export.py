"""Single-file snapshot of a studio's state.

Bundles GDD, art bible, sprint, backlog, decisions (current state),
milestones (with computed progress), archive summary, thresholds, and
optional doctor + history slices into one JSON document. Useful for
backup, PR review (a reviewer can see the whole studio in one file),
and migration between machines.

Pure read: never mutates state. Crash-proof against missing files —
each section degrades to a sensible empty default.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from ..core.config import Config
from .archive import archive_summary, load_archived_tasks
from .config import STUDIO_DEFAULTS, StudioThresholds
from .decisions import latest_decisions
from .diagnostics import Check, run_diagnostics
from .milestones import all_milestones_with_progress
from .state import StudioState

logger = logging.getLogger(__name__)


SCHEMA_VERSION = 1


def _read_doc_safe(state: StudioState, path: Path) -> str:
    try:
        return state.read_doc(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read %s: %s", path, exc)
        return ""


def _list_review_filenames(state: StudioState) -> list[str]:
    reviews = state.paths.reviews
    if not reviews.is_dir():
        return []
    return sorted(p.name for p in reviews.glob("*.md") if p.is_file())


def _tail_regression_log(state: StudioState, limit: int = 50) -> list[dict]:
    path = state.paths.qa_regression
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("Could not read regression log: %s", exc)
        return []
    out: list[dict] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out[-max(1, int(limit or 1)):] if limit else out


def _serialize_check(c: Check) -> dict:
    return {"name": c.name, "status": c.status, "detail": c.detail}


def build_snapshot(
    state: StudioState,
    *,
    config: Optional[Config] = None,
    include_doctor: bool = False,
    include_history: int = 0,
    include_reviews: int = 0,
    include_regression: int = 50,
    now: Optional[float] = None,
) -> dict:
    """Build a structured snapshot of the entire studio.

    - `include_doctor` runs the diagnostics checks (needs `config`).
    - `include_history` caps how many recent archived tasks to embed
      (0 = none, just the summary; useful because archives can be large).
    - `include_reviews` caps how many recent review markdowns to embed
      verbatim (0 = just the filename list).
    - `include_regression` caps the tail of qa/regression.jsonl
      (default 50; pass 0 to omit).
    """
    now = now if now is not None else time.time()
    paths = state.paths

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": now,
        "exported_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "project_root": str(paths.project_root),
        "studio_root": str(paths.root),
        "docs": {
            "gdd": _read_doc_safe(state, paths.gdd),
            "art_bible": _read_doc_safe(state, paths.art_bible),
            "sprint_current": _read_doc_safe(state, paths.sprint_current),
        },
        "tasks": [t.to_dict() for t in state.load_tasks()],
        "decisions": [d.to_dict() for d in latest_decisions(state)],
        "milestones": all_milestones_with_progress(state),
        "archive_summary": archive_summary(state),
        "thresholds": dataclasses.asdict(state.thresholds),
        "thresholds_default": dataclasses.asdict(STUDIO_DEFAULTS),
        "review_files": _list_review_filenames(state),
    }

    if include_regression:
        snapshot["qa_regression_tail"] = _tail_regression_log(state, limit=include_regression)

    if include_history > 0:
        # Sort newest-first by completion timestamp, then cap.
        archived = sorted(
            load_archived_tasks(state),
            key=lambda t: t.updated_at or t.created_at or 0.0,
            reverse=True,
        )[: int(include_history)]
        snapshot["archive_recent"] = [t.to_dict() for t in archived]

    if include_reviews > 0:
        review_files = _list_review_filenames(state)[-int(include_reviews):]
        snapshot["reviews"] = {
            name: _read_doc_safe(state, paths.reviews / name) for name in review_files
        }

    if include_doctor:
        if config is None:
            logger.warning("include_doctor=True but no config provided; skipping doctor section")
        else:
            checks = run_diagnostics(state, config, unity_bridge=None, now=now)
            snapshot["doctor"] = [_serialize_check(c) for c in checks]

    return snapshot


def snapshot_to_json(snapshot: dict, *, pretty: bool = True) -> str:
    """Serialize a snapshot dict to JSON. UTF-8 safe, newline-terminated."""
    if pretty:
        return json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    return json.dumps(snapshot, ensure_ascii=False) + "\n"
