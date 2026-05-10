"""Round-trip tests for unitytools/studio state I/O."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make the in-tree package importable when run directly (editable installs
# in other worktrees may shadow this checkout).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    Decision,
    DecisionStatus,
    Milestone,
    MilestoneStatus,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
)


def _fresh_state() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="studio-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    return StudioState(paths), tmp


def run_test() -> None:
    state, tmp = _fresh_state()

    # Tasks: add → load → update → status filter
    t1 = state.add_task(Task(title="Write GDD", role="designer"))
    t2 = state.add_task(Task(title="Block out level 1", role="level_designer", milestone="m1"))
    assert len(state.load_tasks()) == 2
    t1.status = TaskStatus.IN_PROGRESS
    state.update_task(t1)
    reloaded = {t.id: t for t in state.load_tasks()}
    assert reloaded[t1.id].status is TaskStatus.IN_PROGRESS
    assert reloaded[t1.id].updated_at >= reloaded[t1.id].created_at
    assert reloaded[t2.id].milestone == "m1"
    print("OK task round-trip + update")

    # Decisions: append-only, ordering preserved
    state.append_decision(Decision(title="Use Ollama", summary="Local-first dev", status=DecisionStatus.ACCEPTED))
    state.append_decision(Decision(title="Hex grid", summary="Tactical levels"))
    decisions = state.load_decisions()
    assert len(decisions) == 2
    assert decisions[0].title == "Use Ollama"
    assert decisions[0].status is DecisionStatus.ACCEPTED
    assert decisions[1].status is DecisionStatus.PROPOSED
    print("OK decision append + iter")

    # Milestones
    state.add_milestone(Milestone(name="Vertical slice", status=MilestoneStatus.IN_PROGRESS, success_criteria=["3 rooms playable"]))
    milestones = state.load_milestones()
    assert len(milestones) == 1
    assert milestones[0].status is MilestoneStatus.IN_PROGRESS
    print("OK milestone round-trip")

    # Regression log append-only
    state.append_regression_entry({"ts": 1.0, "fps": 60, "scene": "level_1"})
    state.append_regression_entry({"ts": 2.0, "fps": 58, "scene": "level_1"})
    lines = state.paths.qa_regression.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    print("OK regression jsonl append")

    # Summary
    summary = state.summary()
    assert summary["task_count"] == 2
    assert summary["decision_count"] == 2
    assert summary["milestone_count"] == 1
    assert summary["tasks_by_status"]["pending"] == 1
    assert summary["tasks_by_status"]["in_progress"] == 1
    assert summary["tasks_by_role"]["level_designer"] == 1
    print("OK summary counts")

    # Atomic write: writing the same file twice does not corrupt it
    state.save_tasks([t1, t2, Task(title="Third", role="qa")])
    assert len(state.load_tasks()) == 3
    print("OK atomic re-write")

    # Path layout sanity
    assert state.paths.qa_screenshots.is_dir()
    assert state.paths.refs.is_dir()
    print("OK directory layout")

    print(f"All studio state tests passed (workspace: {tmp})")


if __name__ == "__main__":
    run_test()
