"""Phase 16 tests: milestone progress + extended studio_list_tasks filters.

Verifies:
- milestone_progress joins backlog + archive correctly
- archived done tasks still count toward completion percent
- unknown milestone id returns None / ok=False (no exception)
- studio_milestone_progress tool wraps with validation
- studio_list_tasks gains milestone + search filters (back-compat:
  empty filters behave like the old impl)
- PRODUCER + CRITIC both carry studio_milestone_progress
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    CRITIC,
    Milestone,
    MilestoneStatus,
    PRODUCER,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
    all_milestones_with_progress,
    archive_old_tasks,
    init_studio_tools,
    milestone_progress,
)
from unitytools.studio.tools import studio_list_tasks, studio_milestone_progress


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="ms-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ─────────────────────────────────────────────── milestone progress


def test_milestone_progress_unknown_id_returns_none() -> None:
    state, _ = _fresh_studio()
    assert milestone_progress(state, "no-such-id") is None
    print("OK unknown milestone -> None")


def test_milestone_progress_no_tasks_zero_percent() -> None:
    state, _ = _fresh_studio()
    m = state.add_milestone(Milestone(name="Vertical slice"))
    result = milestone_progress(state, m.id)
    assert result is not None
    assert result["task_count"] == 0
    assert result["done_count"] == 0
    assert result["completion_pct"] == 0.0
    assert result["by_status"] == {}
    print("OK milestone with no tasks -> 0%")


def test_milestone_progress_with_mixed_active_tasks() -> None:
    state, _ = _fresh_studio()
    m = state.add_milestone(Milestone(name="Slice A"))
    # 2 done, 1 pending, 1 blocked = 25% if we measure done/total
    state.add_task(Task(title="done 1", role="designer", status=TaskStatus.DONE, milestone=m.id))
    state.add_task(Task(title="done 2", role="designer", status=TaskStatus.DONE, milestone=m.id))
    state.add_task(Task(title="pending", role="designer", status=TaskStatus.PENDING, milestone=m.id))
    state.add_task(Task(title="blocked", role="designer", status=TaskStatus.BLOCKED, milestone=m.id))
    # Unrelated task (different milestone) should not count
    state.add_task(Task(title="other", role="designer", status=TaskStatus.DONE, milestone="other-ms"))

    result = milestone_progress(state, m.id)
    assert result["task_count"] == 4
    assert result["done_count"] == 2
    assert result["completion_pct"] == 0.5
    assert result["by_status"]["done"] == 2
    assert result["by_status"]["pending"] == 1
    assert result["by_status"]["blocked"] == 1
    print("OK milestone progress counts only linked tasks")


def test_milestone_progress_includes_archived_done_tasks() -> None:
    """Once tasks age out and move into archive/<YYYY>.json they must still
    contribute to the milestone's completion percent. Otherwise a project
    appears to lose progress whenever auto-archive runs."""
    state, _ = _fresh_studio()
    m = state.add_milestone(Milestone(name="Old slice"))
    now = time.time()
    # Two done tasks well over 30d -> will archive on the next call
    for i in range(2):
        t = Task(title=f"old done {i}", role="designer", status=TaskStatus.DONE, milestone=m.id)
        t.created_at = t.updated_at = now - 90 * 86400
        state.add_task(t)
    # One fresh pending task stays in backlog
    state.add_task(Task(title="fresh pending", role="designer", status=TaskStatus.PENDING, milestone=m.id))

    # Before archive: 2/3 done
    pre = milestone_progress(state, m.id)
    assert pre["task_count"] == 3
    assert pre["done_count"] == 2

    archive_old_tasks(state, older_than_days=30, now=now)

    # After archive: same numbers should hold -- the two done tasks now live
    # in archive but still count.
    post = milestone_progress(state, m.id)
    assert post["task_count"] == 3
    assert post["done_count"] == 2
    assert post["completion_pct"] == pre["completion_pct"]
    print("OK archived done tasks still count toward milestone completion")


def test_all_milestones_with_progress_returns_ordered_list() -> None:
    state, _ = _fresh_studio()
    m_old = state.add_milestone(Milestone(name="first"))
    # Small sleep would slow tests; instead poke the created_at field
    m_old.created_at = time.time() - 100
    state.save_milestones([m_old])
    m_new = state.add_milestone(Milestone(name="second"))

    rows = all_milestones_with_progress(state)
    assert [m["name"] for m in rows] == ["first", "second"]
    assert all("completion_pct" in m for m in rows)
    print("OK all_milestones_with_progress ordered by created_at")


# ─────────────────────────────────────────────── tool wrapper


def test_studio_milestone_progress_tool_validates() -> None:
    state, _ = _fresh_studio()
    bad = studio_milestone_progress("no-such-id")
    assert bad["ok"] is False
    assert "not found" in bad["error"]

    m = state.add_milestone(Milestone(name="MVP"))
    good = studio_milestone_progress(m.id)
    assert good["ok"] is True
    assert good["name"] == "MVP"
    assert good["task_count"] == 0
    print("OK studio_milestone_progress tool: ok=False on bad id, ok=True on real")


def test_studio_milestone_progress_in_producer_and_critic() -> None:
    assert "studio_milestone_progress" in PRODUCER.tool_set
    assert "studio_milestone_progress" in CRITIC.tool_set
    print("OK Producer + Critic both have studio_milestone_progress")


# ─────────────────────────────────────────────── studio_list_tasks filters


def test_list_tasks_milestone_filter() -> None:
    state, _ = _fresh_studio()
    state.add_task(Task(title="A", role="designer", status=TaskStatus.PENDING, milestone="m1"))
    state.add_task(Task(title="B", role="designer", status=TaskStatus.PENDING, milestone="m2"))
    state.add_task(Task(title="C", role="critic", status=TaskStatus.PENDING))

    only_m1 = studio_list_tasks(milestone="m1")
    assert only_m1["count"] == 1
    assert only_m1["tasks"][0]["title"] == "A"
    print("OK studio_list_tasks milestone filter")


def test_list_tasks_search_filter() -> None:
    state, _ = _fresh_studio()
    state.add_task(Task(title="Refine GDD pillars", description="shape pillar 2", role="designer", status=TaskStatus.PENDING))
    state.add_task(Task(title="Lock palette", description="PS1 vibe", role="art_director", status=TaskStatus.PENDING))

    pillar_hits = studio_list_tasks(search="pillar")
    assert pillar_hits["count"] == 1
    palette_hits = studio_list_tasks(search="palette")
    assert palette_hits["count"] == 1
    # Description hit
    ps1_hits = studio_list_tasks(search="ps1")
    assert ps1_hits["count"] == 1
    print("OK studio_list_tasks search filter (title + description, case-insensitive)")


def test_list_tasks_back_compat_no_filters() -> None:
    """Calling studio_list_tasks() with all-empty arguments matches the
    pre-Phase-16 behaviour (return everything)."""
    state, _ = _fresh_studio()
    for _ in range(3):
        state.add_task(Task(title="x", role="designer", status=TaskStatus.PENDING))
    all_tasks = studio_list_tasks()
    assert all_tasks["count"] == 3
    print("OK studio_list_tasks default args still return all")


def run_test() -> None:
    test_milestone_progress_unknown_id_returns_none()
    test_milestone_progress_no_tasks_zero_percent()
    test_milestone_progress_with_mixed_active_tasks()
    test_milestone_progress_includes_archived_done_tasks()
    test_all_milestones_with_progress_returns_ordered_list()
    test_studio_milestone_progress_tool_validates()
    test_studio_milestone_progress_in_producer_and_critic()
    test_list_tasks_milestone_filter()
    test_list_tasks_search_filter()
    test_list_tasks_back_compat_no_filters()
    print("All Phase 16 milestone + task-browse tests passed")


if __name__ == "__main__":
    run_test()
