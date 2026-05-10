"""Phase 12 tests: auto-archival of old done/rejected tasks.

Covers cutoff semantics, multi-year grouping, idempotent re-archive,
dry-run preview, load helpers, and the new diagnostics check that
suggests running the CLI when stale tasks pile up.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    DEFAULT_AGE_DAYS,
    DEFAULT_ARCHIVABLE_STATUSES,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
    archive_old_tasks,
    archive_summary,
    init_studio_tools,
    load_archived_tasks,
)
from unitytools.studio.diagnostics import _check_archivable_tasks


# ───────────────────────────────────────────── helpers


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="archive-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_done_task(state: StudioState, age_days: float, *, now: float, year_override: int | None = None) -> Task:
    """Create a DONE task whose updated_at is `age_days` in the past."""
    ts = now - age_days * 86400.0
    if year_override is not None:
        # Force the task's year by adjusting timestamp into that calendar year.
        struct = time.localtime(ts)
        target = time.mktime((year_override, struct.tm_mon, struct.tm_mday, struct.tm_hour, struct.tm_min, struct.tm_sec, 0, 0, struct.tm_isdst))
        ts = target
    t = Task(title=f"done {age_days:g}d ago", role="designer", status=TaskStatus.DONE)
    t.created_at = ts
    t.updated_at = ts
    state.add_task(t)
    return t


# ───────────────────────────────────────────── cutoff


def test_archive_does_nothing_when_backlog_is_empty() -> None:
    state, _ = _fresh_studio()
    result = archive_old_tasks(state)
    assert result.count == 0
    assert result.kept == 0
    assert result.archive_paths == []
    print("OK empty backlog -> no archive")


def test_archive_skips_recent_tasks() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_done_task(state, age_days=5, now=now)        # too fresh
    _seed_done_task(state, age_days=29, now=now)       # still under 30d
    result = archive_old_tasks(state, older_than_days=30, now=now)
    assert result.count == 0
    assert len(state.load_tasks()) == 2
    print("OK tasks within window stay in backlog")


def test_archive_moves_old_done_tasks() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    fresh = _seed_done_task(state, age_days=5, now=now)
    old1 = _seed_done_task(state, age_days=45, now=now)
    old2 = _seed_done_task(state, age_days=120, now=now)
    result = archive_old_tasks(state, older_than_days=30, now=now)
    assert result.count == 2
    assert {t.id for t in result.moved} == {old1.id, old2.id}
    # Backlog still has the fresh one
    remaining = state.load_tasks()
    assert len(remaining) == 1 and remaining[0].id == fresh.id
    # Archive file written
    assert len(result.archive_paths) >= 1
    for p in result.archive_paths:
        assert p.exists()
    print("OK old DONE tasks moved out of backlog")


def test_archive_skips_pending_and_in_progress_regardless_of_age() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    # Ancient task but still pending -> must NOT archive
    ancient = Task(title="ancient pending", role="designer", status=TaskStatus.PENDING)
    ancient.created_at = ancient.updated_at = now - 365 * 86400.0
    state.add_task(ancient)
    # Ancient in_progress -> also stays
    ip = Task(title="ancient in progress", role="designer", status=TaskStatus.IN_PROGRESS)
    ip.created_at = ip.updated_at = now - 365 * 86400.0
    state.add_task(ip)
    result = archive_old_tasks(state, older_than_days=30, now=now)
    assert result.count == 0
    assert len(state.load_tasks()) == 2
    print("OK pending / in_progress never archive (regardless of age)")


def test_archive_moves_rejected_too() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    rej = Task(title="rejected old", role="designer", status=TaskStatus.REJECTED)
    rej.created_at = rej.updated_at = now - 60 * 86400.0
    state.add_task(rej)
    result = archive_old_tasks(state, older_than_days=30, now=now)
    assert result.count == 1
    assert result.moved[0].status is TaskStatus.REJECTED
    print("OK REJECTED is archivable by default")


def test_archive_status_filter_narrows_set() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_done_task(state, age_days=60, now=now)
    rej = Task(title="r", role="designer", status=TaskStatus.REJECTED)
    rej.created_at = rej.updated_at = now - 60 * 86400.0
    state.add_task(rej)
    # Only archive REJECTED, not DONE
    result = archive_old_tasks(state, older_than_days=30, statuses={TaskStatus.REJECTED}, now=now)
    assert result.count == 1
    assert result.moved[0].status is TaskStatus.REJECTED
    # Backlog still has the DONE one
    remaining = state.load_tasks()
    assert len(remaining) == 1
    assert remaining[0].status is TaskStatus.DONE
    print("OK status filter narrows archive scope")


# ───────────────────────────────────────── multi-year grouping


def test_archive_groups_tasks_by_year() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    # Year 2024 task
    t_2024 = Task(title="from 2024", role="designer", status=TaskStatus.DONE)
    t_2024.created_at = t_2024.updated_at = time.mktime((2024, 6, 15, 12, 0, 0, 0, 0, 0))
    state.add_task(t_2024)
    # Year 2025 task
    t_2025 = Task(title="from 2025", role="designer", status=TaskStatus.DONE)
    t_2025.created_at = t_2025.updated_at = time.mktime((2025, 6, 15, 12, 0, 0, 0, 0, 0))
    state.add_task(t_2025)

    result = archive_old_tasks(state, older_than_days=30, now=now)
    assert result.count == 2
    # Two archive files written, one per year
    by_year = result.by_year()
    assert by_year.get(2024) == 1
    assert by_year.get(2025) == 1
    assert state.paths.archive(2024).exists()
    assert state.paths.archive(2025).exists()
    print("OK tasks group into per-year archive files")


# ───────────────────────────────────── idempotency + dedup


def test_archive_idempotent_when_called_twice() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    old = _seed_done_task(state, age_days=60, now=now)

    result1 = archive_old_tasks(state, older_than_days=30, now=now)
    assert result1.count == 1
    # Backlog now empty
    assert len(state.load_tasks()) == 0

    # Second call has nothing to archive
    result2 = archive_old_tasks(state, older_than_days=30, now=now)
    assert result2.count == 0

    # Archive still has exactly one entry
    archived = load_archived_tasks(state)
    assert len(archived) == 1
    assert archived[0].id == old.id
    print("OK second archive is a no-op")


def test_archive_merges_existing_archive_by_id() -> None:
    """Re-archiving the same id (e.g. two-step lifecycle) keeps newest copy."""
    state, _ = _fresh_studio()
    now = time.time()
    t = _seed_done_task(state, age_days=60, now=now)
    archive_old_tasks(state, older_than_days=30, now=now)

    # Manually re-add the same id with a different title (simulating
    # a re-run of an old task that got revived and re-completed).
    revived = Task(title="UPDATED title", role="designer", status=TaskStatus.DONE)
    revived.id = t.id
    revived.created_at = t.created_at
    revived.updated_at = now - 60 * 86400.0
    state.add_task(revived)
    archive_old_tasks(state, older_than_days=30, now=now)

    archived = load_archived_tasks(state)
    assert len(archived) == 1  # merged-by-id, not duplicated
    assert archived[0].title == "UPDATED title"
    print("OK re-archiving same id merges, not duplicates")


# ───────────────────────────────────── dry run


def test_archive_dry_run_does_not_write() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_done_task(state, age_days=60, now=now)
    _seed_done_task(state, age_days=120, now=now)
    initial_backlog = len(state.load_tasks())

    result = archive_old_tasks(state, older_than_days=30, now=now, dry_run=True)
    assert result.dry_run is True
    assert result.count == 2
    # Backlog unchanged
    assert len(state.load_tasks()) == initial_backlog
    # No archive files written
    for p in result.archive_paths:
        assert not p.exists()
    print("OK dry-run reports moves but does not touch disk")


# ───────────────────────────────────── load helpers


def test_load_archived_tasks_returns_empty_for_missing_archive() -> None:
    state, _ = _fresh_studio()
    assert load_archived_tasks(state) == []
    assert load_archived_tasks(state, year=2024) == []
    print("OK load_archived_tasks tolerates missing archive")


def test_load_archived_tasks_skips_malformed_year_files() -> None:
    state, _ = _fresh_studio()
    state.paths.archive_root.mkdir(parents=True, exist_ok=True)
    # Write a malformed file
    (state.paths.archive_root / "9999.json").write_text("{not valid", encoding="utf-8")
    # Write a valid file
    valid = {"tasks": [{"id": "abc", "title": "from 2024", "role": "designer", "status": "done"}]}
    (state.paths.archive_root / "2024.json").write_text(json.dumps(valid), encoding="utf-8")

    out = load_archived_tasks(state)
    assert len(out) == 1
    assert out[0].id == "abc"
    print("OK malformed year file skipped, valid one returned")


def test_load_archived_tasks_year_filter() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    # 2024 + 2025 tasks
    t_2024 = Task(title="x", role="designer", status=TaskStatus.DONE)
    t_2024.created_at = t_2024.updated_at = time.mktime((2024, 6, 1, 12, 0, 0, 0, 0, 0))
    state.add_task(t_2024)
    t_2025 = Task(title="y", role="designer", status=TaskStatus.DONE)
    t_2025.created_at = t_2025.updated_at = time.mktime((2025, 6, 1, 12, 0, 0, 0, 0, 0))
    state.add_task(t_2025)
    archive_old_tasks(state, older_than_days=30, now=now)

    only_2024 = load_archived_tasks(state, year=2024)
    only_2025 = load_archived_tasks(state, year=2025)
    all_archived = load_archived_tasks(state)
    assert len(only_2024) == 1 and only_2024[0].title == "x"
    assert len(only_2025) == 1 and only_2025[0].title == "y"
    assert len(all_archived) == 2
    print("OK year filter returns only that year's tasks")


# ───────────────────────────────────── archive_summary


def test_archive_summary_reports_per_year_counts() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    # Use only past years so every task crosses the cutoff cleanly.
    for year in (2023, 2023, 2024, 2025):
        t = Task(title=f"y{year}", role="designer", status=TaskStatus.DONE)
        t.created_at = t.updated_at = time.mktime((year, 6, 1, 12, 0, 0, 0, 0, 0))
        state.add_task(t)
    archive_old_tasks(state, older_than_days=30, now=now)

    summary = archive_summary(state)
    assert summary["total"] == 4
    assert sorted(summary["years"]) == [2023, 2024, 2025]
    counts_by_year = {f["year"]: f["count"] for f in summary["files"]}
    assert counts_by_year[2023] == 2
    assert counts_by_year[2024] == 1
    assert counts_by_year[2025] == 1
    print("OK archive_summary aggregates correctly")


# ───────────────────────────────────── diagnostics check


def test_archivable_tasks_diagnostic_warns_only_when_many() -> None:
    state, _ = _fresh_studio()
    now = time.time()

    # 0 archivable -> ok
    c = _check_archivable_tasks(state, now=now)
    assert c.status == "ok"
    assert "0 stale" in c.detail

    # 5 archivable, under threshold -> ok with hint
    for _ in range(5):
        _seed_done_task(state, age_days=60, now=now)
    c = _check_archivable_tasks(state, now=now)
    assert c.status == "ok"
    assert "no rush" in c.detail

    # Add 25 more -> over threshold -> warn
    for _ in range(25):
        _seed_done_task(state, age_days=60, now=now)
    c = _check_archivable_tasks(state, now=now)
    assert c.status == "warn"
    assert "studio-archive" in c.detail
    print("OK archivable_tasks diagnostic warns at the right point")


# ───────────────────────────────────── defaults sanity


def test_default_constants_match_documented_values() -> None:
    assert DEFAULT_AGE_DAYS == 30.0
    assert TaskStatus.DONE in DEFAULT_ARCHIVABLE_STATUSES
    assert TaskStatus.REJECTED in DEFAULT_ARCHIVABLE_STATUSES
    print("OK exported defaults match documentation")


def run_test() -> None:
    test_archive_does_nothing_when_backlog_is_empty()
    test_archive_skips_recent_tasks()
    test_archive_moves_old_done_tasks()
    test_archive_skips_pending_and_in_progress_regardless_of_age()
    test_archive_moves_rejected_too()
    test_archive_status_filter_narrows_set()
    test_archive_groups_tasks_by_year()
    test_archive_idempotent_when_called_twice()
    test_archive_merges_existing_archive_by_id()
    test_archive_dry_run_does_not_write()
    test_load_archived_tasks_returns_empty_for_missing_archive()
    test_load_archived_tasks_skips_malformed_year_files()
    test_load_archived_tasks_year_filter()
    test_archive_summary_reports_per_year_counts()
    test_archivable_tasks_diagnostic_warns_only_when_many()
    test_default_constants_match_documented_values()
    print("All Phase 12 archive tests passed")


if __name__ == "__main__":
    run_test()
