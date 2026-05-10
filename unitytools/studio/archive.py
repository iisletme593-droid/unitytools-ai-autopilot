"""Auto-archival of completed tasks.

`backlog.json` is the working set: pending, in_progress, blocked,
review tasks plus the recently-done ones. Once a project runs for a
few months, the file fills with stale `done` rows that nothing reads.
This module moves them out:

    studio/backlog.json   <- working set (small, hot)
    studio/archive/<YYYY>.json   <- frozen history per year

The archive groups tasks by the year of their `updated_at` timestamp
so navigating history is "open the right year file." Re-archiving the
same task is idempotent: existing entries are merged by id, the
newest copy wins.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .models import Task, TaskStatus
from .state import StudioState

logger = logging.getLogger(__name__)


# Default: tasks done/rejected for at least 30 days move out
DEFAULT_AGE_DAYS = 30.0

# Default: only DONE and REJECTED are archived. PENDING / IN_PROGRESS /
# BLOCKED / REVIEW always stay in the working backlog regardless of age.
DEFAULT_ARCHIVABLE_STATUSES = (TaskStatus.DONE, TaskStatus.REJECTED)


@dataclass
class ArchiveResult:
    """Outcome of a single archive_old_tasks() call."""

    moved: list[Task] = field(default_factory=list)
    kept: int = 0
    archive_paths: list[Path] = field(default_factory=list)
    dry_run: bool = False

    @property
    def count(self) -> int:
        return len(self.moved)

    def by_status(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.moved:
            out[t.status.value] = out.get(t.status.value, 0) + 1
        return out

    def by_year(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for t in self.moved:
            ts = t.updated_at or t.created_at
            year = time.localtime(ts).tm_year
            out[year] = out.get(year, 0) + 1
        return out


def _atomic_write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def archive_old_tasks(
    state: StudioState,
    older_than_days: float = DEFAULT_AGE_DAYS,
    statuses: Optional[Iterable[TaskStatus]] = None,
    now: Optional[float] = None,
    dry_run: bool = False,
) -> ArchiveResult:
    """Move tasks matching `statuses` and older than `older_than_days`
    from backlog.json into studio/archive/<YYYY>.json files.

    Age is measured against `task.updated_at` (falling back to
    created_at) compared with `now` (defaults to wall clock). The
    archive file format mirrors backlog.json so the same Task.from_dict
    parses it.

    Idempotent across runs: re-archiving a task just rewrites the same
    archive entry (merge-by-id, latest copy wins).

    `dry_run=True` returns the same ArchiveResult shape but does NOT
    touch disk — useful for `studio-archive --dry-run` previews.
    """
    statuses_set = set(statuses) if statuses else set(DEFAULT_ARCHIVABLE_STATUSES)
    if not statuses_set:
        return ArchiveResult([], 0, [], dry_run=dry_run)
    now = now if now is not None else time.time()
    cutoff = now - max(0.0, float(older_than_days)) * 86400.0

    tasks = state.load_tasks()
    to_move: list[Task] = []
    keep: list[Task] = []
    for t in tasks:
        ts = t.updated_at or t.created_at
        if t.status in statuses_set and ts is not None and ts < cutoff:
            to_move.append(t)
        else:
            keep.append(t)

    result = ArchiveResult(moved=to_move, kept=len(keep), dry_run=dry_run)
    if not to_move:
        return result

    by_year: dict[int, list[Task]] = defaultdict(list)
    for t in to_move:
        ts = t.updated_at or t.created_at or now
        by_year[time.localtime(ts).tm_year].append(t)

    for year, batch in sorted(by_year.items()):
        archive_path = state.paths.archive(year)
        existing: dict[str, Task] = {}
        if archive_path.exists():
            try:
                data = json.loads(archive_path.read_text(encoding="utf-8"))
                for raw in data.get("tasks", []):
                    parsed = Task.from_dict(raw)
                    existing[parsed.id] = parsed
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "archive %s malformed (%s); recreating from current batch", archive_path, exc
                )
                existing = {}
        for t in batch:
            existing[t.id] = t
        merged = sorted(existing.values(), key=lambda x: x.updated_at or x.created_at or 0.0)
        if not dry_run:
            _atomic_write_json(archive_path, {"tasks": [t.to_dict() for t in merged]})
        result.archive_paths.append(archive_path)

    if not dry_run:
        state.save_tasks(keep)
    return result


def load_archived_tasks(state: StudioState, year: Optional[int] = None) -> list[Task]:
    """Read archived tasks from one year (or all years when year=None).

    Returns an empty list when the archive folder or year file is
    absent. Malformed year files are skipped with a warning, not
    raised, so a partial archive corruption does not break callers.
    """
    archive_dir = state.paths.archive_root
    if not archive_dir.is_dir():
        return []
    if year is not None:
        path = state.paths.archive(year)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [Task.from_dict(t) for t in data.get("tasks", [])]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("archive %s unreadable (%s)", path, exc)
            return []

    out: list[Task] = []
    for path in sorted(archive_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("archive %s unreadable (%s); skipping", path, exc)
            continue
        out.extend(Task.from_dict(t) for t in data.get("tasks", []))
    return out


def archive_summary(state: StudioState) -> dict:
    """High-level archive stats for diagnostics / status output."""
    archive_dir = state.paths.archive_root
    if not archive_dir.is_dir():
        return {"years": [], "total": 0, "files": []}
    files: list[dict] = []
    total = 0
    for path in sorted(archive_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            count = len(data.get("tasks", []))
        except (json.JSONDecodeError, OSError):
            count = 0
        try:
            year = int(path.stem)
        except ValueError:
            year = -1
        files.append({"year": year, "path": str(path), "count": count})
        total += count
    return {
        "years": sorted({f["year"] for f in files if f["year"] >= 0}),
        "total": total,
        "files": files,
    }
