"""Restore a studio from a snapshot produced by `build_snapshot`.

Inverse of `export.build_snapshot`. Two modes:

- **merge** (default): upsert by id, append decisions, overwrite the
  three docs only if snapshot has them. Existing studio state is
  preserved where the snapshot is silent.
- **overwrite**: wipe the canonical files first, then write everything
  from the snapshot. Destructive; the caller is expected to confirm.

What restores cleanly:
- docs (gdd, art_bible, sprint_current) -> write_doc
- active tasks (backlog.json) -> upsert by id
- decisions -> append (jsonl is append-only; latest_decisions handles
  dedupe on read)
- milestones -> upsert by id (strip the computed `progress` block)
- thresholds -> studio/config.json (overrides only; defaults skipped)
- archive_recent -> per-year archive files (upsert by id)
- reviews -> studio/reviews/<filename>.md
- qa_regression_tail -> append to qa/regression.jsonl

What does NOT round-trip:
- archive entries beyond `include_history` (snapshot only carries a
  capped tail; older entries from the source studio are lost)
- review files beyond `include_reviews` (filenames listed, bodies
  absent)
- regression entries beyond `include_regression`
- doctor section is ignored (it's a runtime report, not state)
- the snapshot's `exported_at` / `project_root` / `studio_root` are
  metadata only and not restored
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .archive import _atomic_write_json
from .config import STUDIO_DEFAULTS
from .export import SCHEMA_VERSION
from .models import Decision, Milestone, Task
from .state import StudioState

logger = logging.getLogger(__name__)


ImportMode = Literal["merge", "overwrite"]


@dataclass
class ImportResult:
    """Per-section counters from one import_snapshot call."""

    docs_written: int = 0
    tasks_added: int = 0
    tasks_updated: int = 0
    decisions_appended: int = 0
    milestones_added: int = 0
    milestones_updated: int = 0
    archive_added: int = 0
    archive_updated: int = 0
    reviews_written: int = 0
    regression_rows_appended: int = 0
    config_written: bool = False
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False

    def summary_line(self) -> str:
        return (
            f"docs={self.docs_written}, tasks(+{self.tasks_added}/~{self.tasks_updated}), "
            f"decisions(+{self.decisions_appended}), "
            f"milestones(+{self.milestones_added}/~{self.milestones_updated}), "
            f"archive(+{self.archive_added}/~{self.archive_updated}), "
            f"reviews(+{self.reviews_written}), regression(+{self.regression_rows_appended}), "
            f"config={'written' if self.config_written else 'skipped'}"
        )


# ─── validation ────────────────────────────────────────────────────────


class SnapshotIncompatibleError(RuntimeError):
    """Raised when the snapshot can't be read by this version of the code."""


def _validate_schema(snapshot: dict) -> None:
    sv = snapshot.get("schema_version")
    if sv is None:
        raise SnapshotIncompatibleError("snapshot has no schema_version")
    if not isinstance(sv, int):
        raise SnapshotIncompatibleError(f"schema_version is not an int: {sv!r}")
    if sv > SCHEMA_VERSION:
        raise SnapshotIncompatibleError(
            f"snapshot schema_version={sv} is newer than this code ({SCHEMA_VERSION}). "
            "Upgrade unitytools or downgrade the snapshot."
        )
    # sv < SCHEMA_VERSION is permitted; older snapshots are forward-compatible
    # so long as future schema versions only ADD fields.


# ─── per-section restorers ─────────────────────────────────────────────


def _restore_docs(state: StudioState, snapshot: dict, mode: ImportMode, result: ImportResult, dry_run: bool) -> None:
    docs = snapshot.get("docs")
    if not isinstance(docs, dict):
        result.skipped.append("docs (missing or not a dict)")
        return
    mapping = {
        "gdd": state.paths.gdd,
        "art_bible": state.paths.art_bible,
        "sprint_current": state.paths.sprint_current,
    }
    for key, path in mapping.items():
        body = docs.get(key)
        if not isinstance(body, str):
            continue
        if mode == "merge" and not body:
            # Don't overwrite an existing doc with an empty string in merge mode.
            continue
        if not dry_run:
            state.write_doc(path, body)
        result.docs_written += 1


def _restore_tasks(state: StudioState, snapshot: dict, mode: ImportMode, result: ImportResult, dry_run: bool) -> None:
    rows = snapshot.get("tasks")
    if not isinstance(rows, list):
        result.skipped.append("tasks (missing or not a list)")
        return
    incoming: list[Task] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        try:
            incoming.append(Task.from_dict(raw))
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"task row {raw.get('id')!r}: {exc}")
    if mode == "overwrite":
        existing: dict[str, Task] = {}
    else:
        existing = {t.id: t for t in state.load_tasks()}
    for t in incoming:
        if t.id in existing:
            result.tasks_updated += 1
        else:
            result.tasks_added += 1
        existing[t.id] = t
    if not dry_run:
        state.save_tasks(existing.values())


def _restore_decisions(state: StudioState, snapshot: dict, mode: ImportMode, result: ImportResult, dry_run: bool) -> None:
    rows = snapshot.get("decisions")
    if not isinstance(rows, list):
        result.skipped.append("decisions (missing or not a list)")
        return
    if mode == "overwrite" and not dry_run:
        # Wipe the existing log so the restore starts fresh.
        state.paths.decisions.write_text("", encoding="utf-8")
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        try:
            decision = Decision.from_dict(raw)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"decision row {raw.get('id')!r}: {exc}")
            continue
        if not dry_run:
            state.append_decision(decision)
        result.decisions_appended += 1


def _restore_milestones(state: StudioState, snapshot: dict, mode: ImportMode, result: ImportResult, dry_run: bool) -> None:
    rows = snapshot.get("milestones")
    if not isinstance(rows, list):
        result.skipped.append("milestones (missing or not a list)")
        return
    incoming: list[Milestone] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        # build_snapshot serialises milestones via all_milestones_with_progress
        # which emits `milestone_id` (alongside computed progress fields).
        # Strip computed fields and map `milestone_id` -> `id` so
        # Milestone.from_dict receives a clean dataclass payload.
        valid = {
            k: v
            for k, v in raw.items()
            if k in {"id", "name", "description", "status", "target_date", "success_criteria", "created_at"}
        }
        if "id" not in valid and "milestone_id" in raw:
            valid["id"] = raw["milestone_id"]
        # `created_at` may not be in older snapshots; fill if absent.
        valid.setdefault("created_at", time.time())
        try:
            incoming.append(Milestone.from_dict(valid))
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"milestone row {valid.get('id')!r}: {exc}")
    if mode == "overwrite":
        existing: dict[str, Milestone] = {}
    else:
        existing = {m.id: m for m in state.load_milestones()}
    for m in incoming:
        if m.id in existing:
            result.milestones_updated += 1
        else:
            result.milestones_added += 1
        existing[m.id] = m
    if not dry_run:
        state.save_milestones(existing.values())


def _restore_thresholds(state: StudioState, snapshot: dict, mode: ImportMode, result: ImportResult, dry_run: bool) -> None:
    thresholds = snapshot.get("thresholds")
    if not isinstance(thresholds, dict):
        result.skipped.append("thresholds (missing or not a dict)")
        return
    import dataclasses as _dc

    default_dict = _dc.asdict(STUDIO_DEFAULTS)
    overrides = {k: v for k, v in thresholds.items() if k in default_dict and v != default_dict[k]}
    if not overrides:
        # Snapshot matches defaults; remove an existing config.json so the
        # studio settles back on defaults too.
        config_file = state.paths.root / "config.json"
        if mode == "overwrite" and config_file.exists():
            if not dry_run:
                config_file.unlink()
            result.config_written = True
        return
    if not dry_run:
        _atomic_write_json(state.paths.root / "config.json", overrides)
    result.config_written = True


def _restore_archive_recent(state: StudioState, snapshot: dict, result: ImportResult, dry_run: bool) -> None:
    rows = snapshot.get("archive_recent")
    if not isinstance(rows, list):
        # Section is opt-in; absence is not an error
        return
    by_year: dict[int, dict[str, Task]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        try:
            t = Task.from_dict(raw)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"archive_recent row {raw.get('id')!r}: {exc}")
            continue
        ts = t.updated_at or t.created_at or time.time()
        year = time.localtime(ts).tm_year
        by_year.setdefault(year, {})[t.id] = t
    for year, tasks in by_year.items():
        path = state.paths.archive(year)
        existing: dict[str, Task] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for r in data.get("tasks", []):
                    parsed = Task.from_dict(r)
                    existing[parsed.id] = parsed
            except (json.JSONDecodeError, OSError):
                existing = {}
        for t in tasks.values():
            if t.id in existing:
                result.archive_updated += 1
            else:
                result.archive_added += 1
            existing[t.id] = t
        merged = sorted(existing.values(), key=lambda x: x.updated_at or x.created_at or 0.0)
        if not dry_run:
            _atomic_write_json(path, {"tasks": [t.to_dict() for t in merged]})


def _restore_reviews(state: StudioState, snapshot: dict, result: ImportResult, dry_run: bool) -> None:
    reviews = snapshot.get("reviews")
    if not isinstance(reviews, dict):
        return
    for name, body in reviews.items():
        if not isinstance(name, str) or not isinstance(body, str):
            continue
        # Basic sanity: name must not climb out of the reviews dir.
        if "/" in name or "\\" in name or name.startswith("."):
            result.errors.append(f"review {name!r}: suspicious filename, skipped")
            continue
        path = state.paths.reviews / name
        if not dry_run:
            state.write_doc(path, body)
        result.reviews_written += 1


def _restore_regression(state: StudioState, snapshot: dict, result: ImportResult, dry_run: bool) -> None:
    rows = snapshot.get("qa_regression_tail")
    if not isinstance(rows, list):
        return
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        if not dry_run:
            state.append_regression_entry(entry)
        result.regression_rows_appended += 1


# ─── main entry point ──────────────────────────────────────────────────


def import_snapshot(
    state: StudioState,
    snapshot: dict,
    mode: ImportMode = "merge",
    dry_run: bool = False,
) -> ImportResult:
    """Restore studio state from a snapshot dict.

    Raises SnapshotIncompatibleError if the schema_version is missing or
    newer than this code supports. Per-row failures inside a section are
    captured in `result.errors`, not raised.

    In `dry_run` mode, the per-section counters reflect what WOULD
    happen but no file is written.
    """
    if mode not in ("merge", "overwrite"):
        raise ValueError(f"mode must be 'merge' or 'overwrite', got {mode!r}")
    _validate_schema(snapshot)

    result = ImportResult(dry_run=dry_run)
    # The order matters: docs/tasks/milestones/decisions are independent;
    # archive can reference task ids that aren't in the active set;
    # config / reviews / regression are append-only.
    _restore_docs(state, snapshot, mode, result, dry_run)
    _restore_tasks(state, snapshot, mode, result, dry_run)
    _restore_decisions(state, snapshot, mode, result, dry_run)
    _restore_milestones(state, snapshot, mode, result, dry_run)
    _restore_thresholds(state, snapshot, mode, result, dry_run)
    _restore_archive_recent(state, snapshot, result, dry_run)
    _restore_reviews(state, snapshot, result, dry_run)
    _restore_regression(state, snapshot, result, dry_run)
    return result


def load_snapshot_file(path) -> dict:
    """Read a snapshot JSON from disk. Convenience wrapper."""
    from pathlib import Path as _P

    p = _P(path)
    if not p.exists():
        raise FileNotFoundError(f"Snapshot not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))
