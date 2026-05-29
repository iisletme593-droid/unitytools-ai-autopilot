"""Phase 7 tests: Dispatcher autonomous loop.

Covers the full autopilot flow:
- Routing: task.role -> dispatch target -> role agent runs
- Engine prerequisite enforcement: tasks targeting Worker are skipped
  when no Unity bridge is available
- Status reconciliation: completed -> done; blocked -> blocked; agent
  forgot to update -> coerced to review
- Limit honoured: dispatch_pending stops at max_tasks
- Filtering by source role works
- needs_engine / needs_vision capability flags on RoleConfig
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ART_DIRECTOR,
    CRITIC,
    DESIGNER,
    DISPATCH_MAP,
    Dispatcher,
    LEVEL_DESIGNER,
    PRODUCER,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
    WORKER,
    init_studio_tools,
)


# ───────────────────────────────────────── fakes


@dataclass
class _ScriptedTurn:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"


class FakeLLM:
    """Replays a fixed turn list. Reused across multiple role runs by being
    constructed fresh per role via the client_factory pattern."""

    def __init__(self, turns: list[_ScriptedTurn]):
        self.turns = turns
        self.cursor = 0
        self.systems_seen: list[str] = []

    def complete(self, system, tools, messages):
        self.systems_seen.append(system)
        if self.cursor >= len(self.turns):
            raise AssertionError("FakeLLM exhausted")
        turn = self.turns[self.cursor]
        self.cursor += 1
        return {
            "text": turn.text,
            "tool_calls": list(turn.tool_calls),
            "stop_reason": turn.stop_reason,
            "raw_content": None,
        }


# ───────────────────────────────────────── helpers


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="autopilot-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _designer_finishes_task(task_id: str) -> list[_ScriptedTurn]:
    """A scripted designer that updates the task to 'done' and stops."""
    return [
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c1",
                    "name": "studio_update_task_status",
                    "input": {"task_id": task_id, "status": "done"},
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text=f"Task {task_id} completed.", stop_reason="end_turn"),
    ]


def _agent_does_nothing() -> list[_ScriptedTurn]:
    """A scripted agent that just emits text without changing status —
    Dispatcher should coerce the task to 'review'."""
    return [_ScriptedTurn(text="No-op.", stop_reason="end_turn")]


# ───────────────────────────────────────── tests


def test_role_capability_flags_match_tool_lists() -> None:
    # Doc-only roles need neither engine nor vision
    assert PRODUCER.needs_engine is False
    assert PRODUCER.needs_vision is False
    assert DESIGNER.needs_engine is False
    assert DESIGNER.needs_vision is False
    assert CRITIC.needs_engine is False
    assert CRITIC.needs_vision is False

    # Engine roles
    assert LEVEL_DESIGNER.needs_engine is True
    assert LEVEL_DESIGNER.needs_vision is True
    assert ART_DIRECTOR.needs_engine is True
    assert ART_DIRECTOR.needs_vision is True
    assert WORKER.needs_engine is True
    # Worker has compare in its allowlist
    assert WORKER.needs_vision is True
    print("OK role capability flags")


def test_dispatch_map_routes_engine_filers_to_worker() -> None:
    # Filer roles route to Worker; doc roles route to themselves
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["critic"] == "critic"
    assert DISPATCH_MAP["art_director"] == "art_director"
    assert DISPATCH_MAP["level_designer"] == "worker"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"  # Phase 24: tech_artist -> Physics QA
    assert DISPATCH_MAP["qa"] == "playtester"  # Phase 23: qa goes to Playtester
    assert DISPATCH_MAP["worker"] == "worker"
    # Producer is intentionally not auto-dispatched
    assert DISPATCH_MAP["producer"] is None
    print("OK dispatch map routing")


def test_dispatch_one_runs_designer_and_marks_done() -> None:
    state, _ = _fresh_studio()
    task = state.add_task(
        Task(
            title="Refine GDD pillar 2",
            role="designer",
            description="Sharpen the second pillar.",
            status=TaskStatus.PENDING,
        )
    )

    fake = FakeLLM(_designer_finishes_task(task.id))
    dispatcher = Dispatcher(state, lambda role_id: fake)
    result = dispatcher.dispatch_one(task)

    assert result.action == "completed"
    assert result.target_role == "designer"
    final = next(t for t in state.load_tasks() if t.id == task.id)
    assert final.status is TaskStatus.DONE
    assert "Designer" in fake.systems_seen[0]
    print("OK dispatch_one runs designer end-to-end")


def test_dispatch_one_skips_engine_task_when_unity_missing() -> None:
    state, _ = _fresh_studio()
    task = state.add_task(
        Task(
            title="Place pine tree",
            role="level_designer",
            status=TaskStatus.PENDING,
        )
    )
    # No unity_bridge, no client_factory call expected
    factory_calls: list[str] = []

    def factory(role_id: str):
        factory_calls.append(role_id)
        raise AssertionError("client_factory should not be called when prereqs fail")

    dispatcher = Dispatcher(state, factory)
    result = dispatcher.dispatch_one(task)
    assert result.action == "skipped"
    assert "engine" in result.reason
    assert factory_calls == []
    # Task status was not touched
    final = next(t for t in state.load_tasks() if t.id == task.id)
    assert final.status is TaskStatus.PENDING
    print("OK dispatch_one skips engine tasks without bridge")


def test_dispatch_one_skips_when_no_dispatch_rule() -> None:
    state, _ = _fresh_studio()
    task = state.add_task(Task(title="Tea break", role="producer", status=TaskStatus.PENDING))
    dispatcher = Dispatcher(state, lambda _r: FakeLLM([]))
    result = dispatcher.dispatch_one(task)
    assert result.action == "skipped"
    assert "no dispatch rule" in result.reason
    print("OK producer-owned task is not auto-dispatched")


def test_dispatch_one_coerces_unfinished_task_to_review() -> None:
    state, _ = _fresh_studio()
    task = state.add_task(Task(title="Hmm", role="designer", status=TaskStatus.PENDING))
    fake = FakeLLM(_agent_does_nothing())
    dispatcher = Dispatcher(state, lambda _r: fake)
    result = dispatcher.dispatch_one(task)
    # Designer ran but never updated status -> Dispatcher coerces to review
    assert result.action == "review"
    final = next(t for t in state.load_tasks() if t.id == task.id)
    assert final.status is TaskStatus.REVIEW
    print("OK dispatcher coerces stale in_progress to review")


def test_dispatch_pending_runs_in_order_until_limit() -> None:
    state, _ = _fresh_studio()
    a = state.add_task(Task(title="First", role="designer", status=TaskStatus.PENDING))
    b = state.add_task(Task(title="Second", role="designer", status=TaskStatus.PENDING))
    c = state.add_task(Task(title="Third", role="designer", status=TaskStatus.PENDING))

    # Build a single FakeLLM with enough turns for two designer runs
    turns = _designer_finishes_task(a.id) + _designer_finishes_task(b.id)
    fake = FakeLLM(turns)
    dispatcher = Dispatcher(state, lambda _r: fake)

    summary = dispatcher.dispatch_pending(limit=2)
    assert summary.total == 2
    assert [r.task_id for r in summary.results] == [a.id, b.id]
    assert all(r.action == "completed" for r in summary.results)
    # Third task untouched
    final_c = next(t for t in state.load_tasks() if t.id == c.id)
    assert final_c.status is TaskStatus.PENDING
    print("OK dispatch_pending honours limit and order")


def test_dispatch_pending_filters_by_role() -> None:
    state, _ = _fresh_studio()
    state.add_task(Task(title="Designer task", role="designer", status=TaskStatus.PENDING))
    target = state.add_task(Task(title="Critic task", role="critic", status=TaskStatus.PENDING))

    fake = FakeLLM(_designer_finishes_task(target.id))
    dispatcher = Dispatcher(state, lambda _r: fake)
    summary = dispatcher.dispatch_pending(limit=10, only_roles=("critic",))
    assert summary.total == 1
    assert summary.results[0].task_id == target.id
    assert summary.results[0].target_role == "critic"
    # The designer task is still pending
    designer_task = next(t for t in state.load_tasks() if t.role == "designer")
    assert designer_task.status is TaskStatus.PENDING
    print("OK dispatch_pending only_roles filter works")


def test_dispatch_pending_skips_non_pending_tasks() -> None:
    state, _ = _fresh_studio()
    done_task = Task(title="Already done", role="designer", status=TaskStatus.DONE)
    state.add_task(done_task)
    block_task = Task(title="Blocked", role="critic", status=TaskStatus.BLOCKED)
    state.add_task(block_task)
    pending = state.add_task(Task(title="Real work", role="designer", status=TaskStatus.PENDING))

    fake = FakeLLM(_designer_finishes_task(pending.id))
    dispatcher = Dispatcher(state, lambda _r: fake)
    summary = dispatcher.dispatch_pending(limit=10)
    assert [r.task_id for r in summary.results] == [pending.id]
    print("OK dispatch_pending only picks PENDING")


def test_dispatcher_summary_counts() -> None:
    state, _ = _fresh_studio()
    pending = state.add_task(Task(title="A", role="designer", status=TaskStatus.PENDING))
    skip = state.add_task(Task(title="B", role="producer", status=TaskStatus.PENDING))
    fake = FakeLLM(_designer_finishes_task(pending.id))
    dispatcher = Dispatcher(state, lambda _r: fake)
    summary = dispatcher.dispatch_pending(limit=10)
    counts = summary.by_action()
    assert counts.get("completed") == 1
    assert counts.get("skipped") == 1
    assert summary.total == 2
    print("OK summary.by_action counts dispatch outcomes")


def run_test() -> None:
    test_role_capability_flags_match_tool_lists()
    test_dispatch_map_routes_engine_filers_to_worker()
    test_dispatch_one_runs_designer_and_marks_done()
    test_dispatch_one_skips_engine_task_when_unity_missing()
    test_dispatch_one_skips_when_no_dispatch_rule()
    test_dispatch_one_coerces_unfinished_task_to_review()
    test_dispatch_pending_runs_in_order_until_limit()
    test_dispatch_pending_filters_by_role()
    test_dispatch_pending_skips_non_pending_tasks()
    test_dispatcher_summary_counts()
    print("All Phase 7 autopilot tests passed")


if __name__ == "__main__":
    run_test()
