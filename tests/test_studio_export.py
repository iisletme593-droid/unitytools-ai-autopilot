"""Phase 19 tests: studio snapshot export.

Verifies the snapshot shape and that optional sections (doctor,
history, reviews) toggle on/off cleanly. JSON output round-trips
through json.loads. No network, no Anthropic, no Ollama.
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

from unitytools.core.config import Config
from unitytools.studio import (
    EXPORT_SCHEMA_VERSION,
    Decision,
    DecisionStatus,
    Milestone,
    MilestoneStatus,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
    archive_old_tasks,
    build_snapshot,
    init_studio_tools,
    snapshot_to_json,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="export-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_full_studio(state: StudioState) -> dict:
    """Populate every section so the snapshot has real content to assert against."""
    state.write_doc(state.paths.gdd, "# GDD\n\nMicro-tactics roguelite.\n")
    state.write_doc(state.paths.art_bible, "# Art Bible\n\nPS1 lo-fi.\n")
    state.write_doc(state.paths.sprint_current, "# Sprint\n\n- block out level 1\n")

    m = state.add_milestone(Milestone(name="Vertical slice", status=MilestoneStatus.IN_PROGRESS))
    pending = state.add_task(Task(title="Refine GDD pillars", role="designer", status=TaskStatus.PENDING, milestone=m.id))
    done_now = state.add_task(Task(title="Block out room 1", role="level_designer", status=TaskStatus.DONE, milestone=m.id))

    state.append_decision(Decision(title="Hex grid combat", summary="use hex", status=DecisionStatus.PROPOSED))

    # Old done task that will archive
    old = Task(title="ancient placeholder", role="designer", status=TaskStatus.DONE, milestone=m.id)
    old.created_at = old.updated_at = time.time() - 100 * 86400
    state.add_task(old)
    archive_old_tasks(state, older_than_days=30, now=time.time())

    # Drop a review file so review_files isn't empty
    state.paths.daily_review("2026-05-11").write_text("# 2026-05-11\nMorning standup.\n", encoding="utf-8")

    # Regression entries
    state.append_regression_entry({"ts": time.time(), "kind": "pixel_diff", "similarity": 0.92})
    state.append_regression_entry({"ts": time.time(), "kind": "vision_compare", "composition_match": 0.7})

    return {"milestone_id": m.id, "pending_id": pending.id, "done_id": done_now.id, "archived_id": old.id}


# ───────────────────────────────────────── shape


def test_snapshot_has_canonical_top_level_keys() -> None:
    state, _ = _fresh_studio()
    snap = build_snapshot(state)
    expected = {
        "schema_version",
        "exported_at",
        "exported_at_iso",
        "project_root",
        "studio_root",
        "docs",
        "tasks",
        "decisions",
        "milestones",
        "archive_summary",
        "thresholds",
        "thresholds_default",
        "review_files",
        "qa_regression_tail",  # default include_regression=50
    }
    assert expected.issubset(set(snap.keys()))
    assert snap["schema_version"] == EXPORT_SCHEMA_VERSION
    print("OK snapshot has canonical top-level keys")


def test_snapshot_docs_contain_full_markdown() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    snap = build_snapshot(state)
    assert "Micro-tactics roguelite" in snap["docs"]["gdd"]
    assert "PS1 lo-fi" in snap["docs"]["art_bible"]
    assert "block out level 1" in snap["docs"]["sprint_current"]
    print("OK docs section embeds full markdown")


def test_snapshot_tasks_only_active_backlog() -> None:
    state, _ = _fresh_studio()
    ids = _seed_full_studio(state)
    snap = build_snapshot(state)
    task_ids = {t["id"] for t in snap["tasks"]}
    # Active: pending + done_now (the freshly-done one)
    assert ids["pending_id"] in task_ids
    assert ids["done_id"] in task_ids
    # Archived (>30d done) should NOT be in active tasks
    assert ids["archived_id"] not in task_ids
    print("OK tasks section = active backlog only")


def test_snapshot_decisions_are_current_state_only() -> None:
    state, _ = _fresh_studio()
    d = state.append_decision(Decision(title="X", summary="s", status=DecisionStatus.PROPOSED))
    # Ratify -> two raw rows but one current
    from unitytools.studio import ratify_decision
    ratify_decision(state, d.id, DecisionStatus.ACCEPTED)

    snap = build_snapshot(state)
    assert len(snap["decisions"]) == 1  # deduped
    assert snap["decisions"][0]["status"] == "accepted"
    print("OK decisions reflect current state (latest_decisions semantics)")


def test_snapshot_milestones_include_progress() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    snap = build_snapshot(state)
    assert len(snap["milestones"]) == 1
    m = snap["milestones"][0]
    # The seeded milestone has 1 pending + 1 done active + 1 archived done = 2/3 done
    assert m["task_count"] == 3
    assert m["done_count"] == 2
    assert abs(m["completion_pct"] - (2.0 / 3.0)) < 1e-6
    print("OK milestones embed computed progress (counts archived done too)")


def test_snapshot_archive_summary_present() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    snap = build_snapshot(state)
    summary = snap["archive_summary"]
    assert summary["total"] >= 1
    assert isinstance(summary["years"], list)
    print("OK archive_summary embedded")


def test_snapshot_thresholds_default_and_effective_both_present() -> None:
    state, _ = _fresh_studio()
    # No config.json -> effective == default
    snap = build_snapshot(state)
    assert snap["thresholds"] == snap["thresholds_default"]
    # Override
    (state.paths.root / "config.json").write_text(
        '{"max_tasks_per_producer_run": 10}', encoding="utf-8"
    )
    snap2 = build_snapshot(state)
    assert snap2["thresholds"]["max_tasks_per_producer_run"] == 10
    assert snap2["thresholds_default"]["max_tasks_per_producer_run"] != 10
    print("OK thresholds: effective + default both surfaced")


# ───────────────────────────────────────── optional sections


def test_snapshot_history_capped_by_include_history() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    # Without include_history: archive_recent absent
    snap = build_snapshot(state, include_history=0)
    assert "archive_recent" not in snap
    # With include_history=10: present, capped
    snap2 = build_snapshot(state, include_history=10)
    assert "archive_recent" in snap2
    assert len(snap2["archive_recent"]) >= 1
    print("OK include_history toggles archive_recent section")


def test_snapshot_reviews_embedded_when_requested() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    snap = build_snapshot(state, include_reviews=0)
    assert "reviews" not in snap
    snap2 = build_snapshot(state, include_reviews=5)
    assert "reviews" in snap2
    # Filename keys map to markdown content
    assert any("Morning standup" in body for body in snap2["reviews"].values())
    print("OK include_reviews embeds markdown bodies")


def test_snapshot_doctor_section_when_config_provided() -> None:
    state, _ = _fresh_studio()
    cfg = Config(api_key="", provider="ollama", ollama_model="gemma4:latest")

    # include_doctor without config -> section absent
    snap_no = build_snapshot(state, include_doctor=True)
    assert "doctor" not in snap_no

    # include_doctor with config -> doctor list present
    snap_yes = build_snapshot(state, config=cfg, include_doctor=True)
    assert "doctor" in snap_yes
    assert isinstance(snap_yes["doctor"], list)
    assert all(set(c.keys()) >= {"name", "status", "detail"} for c in snap_yes["doctor"])
    print("OK doctor section requires config + flag")


def test_snapshot_regression_tail_present_and_capped() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    snap = build_snapshot(state, include_regression=1)
    assert "qa_regression_tail" in snap
    assert len(snap["qa_regression_tail"]) == 1
    print("OK qa_regression_tail respects include_regression cap")


# ───────────────────────────────────────── serialization


def test_snapshot_round_trips_through_json() -> None:
    state, _ = _fresh_studio()
    _seed_full_studio(state)
    snap = build_snapshot(state)
    pretty = snapshot_to_json(snap, pretty=True)
    compact = snapshot_to_json(snap, pretty=False)
    assert pretty.endswith("\n")
    assert compact.endswith("\n")
    # Both must parse back to an equivalent dict
    parsed_pretty = json.loads(pretty)
    parsed_compact = json.loads(compact)
    assert parsed_pretty["schema_version"] == parsed_compact["schema_version"]
    assert parsed_pretty["project_root"] == parsed_compact["project_root"]
    # Pretty is bigger (indented)
    assert len(pretty) > len(compact)
    print("OK snapshot JSON round-trips, pretty vs compact both valid")


def test_snapshot_on_empty_studio_produces_valid_skeleton() -> None:
    state, _ = _fresh_studio()
    snap = build_snapshot(state)
    # Should not crash and must produce empty-but-valid sections
    assert snap["tasks"] == []
    assert snap["decisions"] == []
    assert snap["milestones"] == []
    assert snap["archive_summary"]["total"] == 0
    assert snap["review_files"] == []
    assert snap["docs"]["gdd"] == ""
    payload = snapshot_to_json(snap)
    json.loads(payload)  # parses cleanly
    print("OK empty studio still produces a valid snapshot")


def run_test() -> None:
    test_snapshot_has_canonical_top_level_keys()
    test_snapshot_docs_contain_full_markdown()
    test_snapshot_tasks_only_active_backlog()
    test_snapshot_decisions_are_current_state_only()
    test_snapshot_milestones_include_progress()
    test_snapshot_archive_summary_present()
    test_snapshot_thresholds_default_and_effective_both_present()
    test_snapshot_history_capped_by_include_history()
    test_snapshot_reviews_embedded_when_requested()
    test_snapshot_doctor_section_when_config_provided()
    test_snapshot_regression_tail_present_and_capped()
    test_snapshot_round_trips_through_json()
    test_snapshot_on_empty_studio_produces_valid_skeleton()
    print("All Phase 19 export tests passed")


if __name__ == "__main__":
    run_test()
