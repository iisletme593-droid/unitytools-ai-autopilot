"""Phase 20 tests: studio-import (inverse of studio-export).

Verifies round-trip behaviour (export -> import recreates the state),
merge vs overwrite semantics, dry-run no-write, schema_version
gating, and graceful handling of missing / malformed sections.
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
    Decision,
    DecisionStatus,
    EXPORT_SCHEMA_VERSION,
    ImportResult,
    Milestone,
    MilestoneStatus,
    SnapshotIncompatibleError,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
    archive_old_tasks,
    build_snapshot,
    import_snapshot,
    init_studio_tools,
    latest_decisions,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="imp-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_full_source(state: StudioState) -> dict:
    """Populate the source studio so a snapshot will have real content."""
    state.write_doc(state.paths.gdd, "# GDD\n\nRoguelite tactics.\n")
    state.write_doc(state.paths.art_bible, "# Art Bible\n\nLo-fi.\n")
    m = state.add_milestone(Milestone(name="Vertical slice", status=MilestoneStatus.IN_PROGRESS))
    pending = state.add_task(Task(title="pillars", role="designer", status=TaskStatus.PENDING, milestone=m.id))
    done = state.add_task(Task(title="room 1", role="level_designer", status=TaskStatus.DONE, milestone=m.id))
    d = state.append_decision(Decision(title="Hex grid", summary="use hex", status=DecisionStatus.PROPOSED))
    state.append_regression_entry({"ts": time.time(), "kind": "pixel_diff", "similarity": 0.9})
    return {"milestone_id": m.id, "pending_id": pending.id, "done_id": done.id, "decision_id": d.id}


# ──────────────────────────────────────────── round trip


def test_round_trip_into_empty_studio_recreates_state() -> None:
    src, _ = _fresh_studio()
    ids = _seed_full_source(src)
    snapshot = build_snapshot(src, include_history=10, include_reviews=10)

    dst, _ = _fresh_studio()
    result = import_snapshot(dst, snapshot, mode="merge")

    assert result.docs_written == 2  # gdd + art_bible (no sprint yet)
    assert result.tasks_added == 2
    assert result.tasks_updated == 0
    assert result.decisions_appended == 1
    assert result.milestones_added == 1

    # Verify destination state matches source
    assert "Roguelite tactics" in dst.read_doc(dst.paths.gdd)
    assert "Lo-fi" in dst.read_doc(dst.paths.art_bible)
    dst_tasks = {t.id for t in dst.load_tasks()}
    assert ids["pending_id"] in dst_tasks
    assert ids["done_id"] in dst_tasks
    dst_decisions = latest_decisions(dst)
    assert len(dst_decisions) == 1 and dst_decisions[0].id == ids["decision_id"]
    dst_milestones = dst.load_milestones()
    assert len(dst_milestones) == 1 and dst_milestones[0].id == ids["milestone_id"]
    print("OK round-trip: empty studio -> import -> matches source")


def test_round_trip_preserves_milestone_link_on_tasks() -> None:
    src, _ = _fresh_studio()
    ids = _seed_full_source(src)
    snapshot = build_snapshot(src)
    dst, _ = _fresh_studio()
    import_snapshot(dst, snapshot, mode="merge")
    pending = next(t for t in dst.load_tasks() if t.id == ids["pending_id"])
    assert pending.milestone == ids["milestone_id"]
    print("OK task.milestone field survives round trip")


# ──────────────────────────────────────────── merge semantics


def test_merge_preserves_existing_unrelated_tasks() -> None:
    src, _ = _fresh_studio()
    _seed_full_source(src)
    snapshot = build_snapshot(src)

    dst, _ = _fresh_studio()
    # Pre-existing task that's NOT in the source snapshot
    keep = dst.add_task(Task(title="keep me", role="critic", status=TaskStatus.PENDING))
    result = import_snapshot(dst, snapshot, mode="merge")

    ids_after = {t.id for t in dst.load_tasks()}
    assert keep.id in ids_after, "merge dropped a pre-existing task"
    assert result.tasks_added == 2
    print("OK merge keeps pre-existing tasks not in snapshot")


def test_merge_upserts_task_with_matching_id() -> None:
    src, _ = _fresh_studio()
    src_task = src.add_task(Task(title="original title", role="designer", status=TaskStatus.PENDING))
    snapshot = build_snapshot(src)

    dst, _ = _fresh_studio()
    # Pre-existing version with same id but different title
    same_id_task = Task(title="old title in dst", role="designer", status=TaskStatus.PENDING)
    same_id_task.id = src_task.id
    dst.add_task(same_id_task)

    result = import_snapshot(dst, snapshot, mode="merge")
    assert result.tasks_updated == 1
    # Imported version wins
    after = next(t for t in dst.load_tasks() if t.id == src_task.id)
    assert after.title == "original title"
    print("OK merge upserts task by id (imported version wins)")


def test_overwrite_wipes_existing_tasks_before_restore() -> None:
    src, _ = _fresh_studio()
    _seed_full_source(src)
    snapshot = build_snapshot(src)

    dst, _ = _fresh_studio()
    dst.add_task(Task(title="will be wiped", role="critic", status=TaskStatus.PENDING))

    import_snapshot(dst, snapshot, mode="overwrite")
    titles = sorted(t.title for t in dst.load_tasks())
    assert "will be wiped" not in titles
    # Only the snapshot's tasks remain
    assert "pillars" in titles and "room 1" in titles
    print("OK overwrite mode discards pre-existing tasks")


# ──────────────────────────────────────────── dry run


def test_dry_run_does_not_write_anything() -> None:
    src, _ = _fresh_studio()
    _seed_full_source(src)
    snapshot = build_snapshot(src)

    dst, _ = _fresh_studio()
    initial_gdd = dst.read_doc(dst.paths.gdd)
    initial_tasks = len(dst.load_tasks())

    result = import_snapshot(dst, snapshot, mode="merge", dry_run=True)
    # Counters reflect what WOULD happen
    assert result.dry_run is True
    assert result.tasks_added >= 1
    # But nothing was written
    assert dst.read_doc(dst.paths.gdd) == initial_gdd
    assert len(dst.load_tasks()) == initial_tasks
    print("OK dry-run reports actions but writes nothing")


# ──────────────────────────────────────────── schema gating


def test_missing_schema_version_is_rejected() -> None:
    dst, _ = _fresh_studio()
    raised = False
    try:
        import_snapshot(dst, {})
    except SnapshotIncompatibleError as exc:
        raised = True
        assert "schema_version" in str(exc)
    assert raised
    print("OK missing schema_version rejected")


def test_newer_schema_version_is_rejected() -> None:
    dst, _ = _fresh_studio()
    fake_snapshot = {"schema_version": EXPORT_SCHEMA_VERSION + 99}
    raised = False
    try:
        import_snapshot(dst, fake_snapshot)
    except SnapshotIncompatibleError as exc:
        raised = True
        assert "newer than this code" in str(exc)
    assert raised
    print("OK newer schema_version rejected")


def test_invalid_mode_raises_value_error() -> None:
    dst, _ = _fresh_studio()
    raised = False
    try:
        import_snapshot(dst, {"schema_version": EXPORT_SCHEMA_VERSION}, mode="weird")  # type: ignore[arg-type]
    except ValueError:
        raised = True
    assert raised
    print("OK invalid mode rejected at API level")


# ──────────────────────────────────────────── partial / malformed input


def test_missing_sections_are_skipped_gracefully() -> None:
    dst, _ = _fresh_studio()
    bare = {"schema_version": EXPORT_SCHEMA_VERSION}
    result = import_snapshot(dst, bare, mode="merge")
    # Nothing imported, no exception
    assert result.docs_written == 0
    assert result.tasks_added == 0
    assert result.decisions_appended == 0
    assert "tasks (missing or not a list)" in result.skipped
    print("OK missing sections recorded in skipped, no crash")


def test_malformed_rows_collected_as_errors_not_raised() -> None:
    dst, _ = _fresh_studio()
    snap = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "tasks": [{"id": "valid", "title": "ok", "role": "designer", "status": "pending"},
                  "not a dict",
                  {"bogus": True}],  # missing required fields
    }
    result = import_snapshot(dst, snap)
    # The valid task imports; bad rows collect as errors
    assert result.tasks_added == 1
    assert len(result.errors) >= 1
    print("OK malformed rows produce errors, not exceptions")


# ──────────────────────────────────────────── thresholds


def test_thresholds_with_overrides_write_config_json() -> None:
    src, _ = _fresh_studio()
    (src.paths.root / "config.json").write_text(
        '{"max_tasks_per_producer_run": 9}', encoding="utf-8"
    )
    snapshot = build_snapshot(src)

    dst, _ = _fresh_studio()
    result = import_snapshot(dst, snapshot, mode="merge")
    assert result.config_written
    dst_config = json.loads((dst.paths.root / "config.json").read_text(encoding="utf-8"))
    assert dst_config["max_tasks_per_producer_run"] == 9
    print("OK threshold overrides round-trip into config.json")


def test_thresholds_matching_defaults_do_not_write_config_in_merge() -> None:
    src, _ = _fresh_studio()  # no config.json
    snapshot = build_snapshot(src)

    dst, _ = _fresh_studio()
    (dst.paths.root / "config.json").write_text(
        '{"max_tasks_per_producer_run": 8}', encoding="utf-8"
    )
    result = import_snapshot(dst, snapshot, mode="merge")
    # In merge mode with no overrides in snapshot, we leave the existing
    # config alone (it might be the destination's own tuning).
    assert not result.config_written
    dst_config = json.loads((dst.paths.root / "config.json").read_text(encoding="utf-8"))
    assert dst_config["max_tasks_per_producer_run"] == 8
    print("OK merge mode does not clobber destination's own config.json")


# ──────────────────────────────────────────── archive + reviews + regression


def test_archive_recent_round_trips() -> None:
    src, _ = _fresh_studio()
    old = Task(title="ancient", role="designer", status=TaskStatus.DONE)
    old.created_at = old.updated_at = time.time() - 120 * 86400
    src.add_task(old)
    archive_old_tasks(src, older_than_days=30, now=time.time())
    snapshot = build_snapshot(src, include_history=10)

    dst, _ = _fresh_studio()
    result = import_snapshot(dst, snapshot, mode="merge")
    assert result.archive_added == 1
    # Archive file exists in destination
    from unitytools.studio import load_archived_tasks
    archived = load_archived_tasks(dst)
    assert len(archived) == 1
    assert archived[0].title == "ancient"
    print("OK archive_recent restores into per-year archive files")


def test_reviews_round_trip() -> None:
    src, _ = _fresh_studio()
    src.paths.daily_review("2026-05-11").write_text(
        "# 2026-05-11\nMorning standup notes.\n", encoding="utf-8"
    )
    snapshot = build_snapshot(src, include_reviews=5)

    dst, _ = _fresh_studio()
    result = import_snapshot(dst, snapshot, mode="merge")
    assert result.reviews_written == 1
    body = (dst.paths.reviews / "2026-05-11.md").read_text(encoding="utf-8")
    assert "Morning standup" in body
    print("OK reviews round-trip into reviews/ folder")


def test_regression_tail_appends() -> None:
    src, _ = _fresh_studio()
    for s in (0.95, 0.85, 0.7):
        src.append_regression_entry({"ts": time.time(), "kind": "pixel_diff", "similarity": s})
    snapshot = build_snapshot(src, include_regression=10)

    dst, _ = _fresh_studio()
    result = import_snapshot(dst, snapshot, mode="merge")
    assert result.regression_rows_appended == 3
    log_lines = dst.paths.qa_regression.read_text(encoding="utf-8").strip().splitlines()
    assert len(log_lines) == 3
    print("OK qa_regression_tail rows appended")


def test_reviews_rejects_suspicious_filenames() -> None:
    """A snapshot trying to escape the reviews dir via path traversal
    must be refused per-entry without crashing the whole import."""
    dst, _ = _fresh_studio()
    snap = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "reviews": {
            "../../etc/passwd": "owned",
            "ok.md": "fine\n",
        },
    }
    result = import_snapshot(dst, snap, mode="merge")
    assert result.reviews_written == 1
    assert any("suspicious filename" in err for err in result.errors)
    print("OK suspicious review filenames refused, valid ones still apply")


def run_test() -> None:
    test_round_trip_into_empty_studio_recreates_state()
    test_round_trip_preserves_milestone_link_on_tasks()
    test_merge_preserves_existing_unrelated_tasks()
    test_merge_upserts_task_with_matching_id()
    test_overwrite_wipes_existing_tasks_before_restore()
    test_dry_run_does_not_write_anything()
    test_missing_schema_version_is_rejected()
    test_newer_schema_version_is_rejected()
    test_invalid_mode_raises_value_error()
    test_missing_sections_are_skipped_gracefully()
    test_malformed_rows_collected_as_errors_not_raised()
    test_thresholds_with_overrides_write_config_json()
    test_thresholds_matching_defaults_do_not_write_config_in_merge()
    test_archive_recent_round_trips()
    test_reviews_round_trip()
    test_regression_tail_appends()
    test_reviews_rejects_suspicious_filenames()
    print("All Phase 20 import tests passed")


if __name__ == "__main__":
    run_test()
