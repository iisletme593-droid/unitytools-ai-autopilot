"""Phase 4 tests: recent_regressions filter, recent_commits via git,
review file write, LoopRunner with --once and an injected sleep_fn that
proves the cadence path executes without actually sleeping.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    PRODUCER,
    LoopRunner,
    Phase,
    RoleRunner,
    StudioPaths,
    StudioState,
    init_studio_tools,
    run_review,
    write_review,
)
from unitytools.studio.tools import (
    studio_recent_commits,
    studio_recent_regressions,
)


# ─────────────────────────────────────────────────────── fakes


@dataclass
class _ScriptedTurn:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"


class FakeLLM:
    def __init__(self, turns: list[_ScriptedTurn]):
        self.turns = turns
        self.cursor = 0

    def complete(self, system, tools, messages):
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


class CyclingFakeLLM:
    """For loop tests: each iteration uses one turn that just emits final text."""

    def __init__(self, label: str = "review pass"):
        self.label = label
        self.calls = 0

    def complete(self, system, tools, messages):
        self.calls += 1
        return {
            "text": f"{self.label} {self.calls}",
            "tool_calls": [],
            "stop_reason": "end_turn",
            "raw_content": None,
        }


# ───────────────────────────────────────────────── helpers


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="loop-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_regressions(state: StudioState, *entries: dict) -> None:
    for entry in entries:
        state.append_regression_entry(entry)


# ───────────────────────────────────────────────── tests


def test_recent_regressions_filters_by_age_and_kind() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_regressions(
        state,
        {"ts": now - 3600, "kind": "vision_compare", "score": 0.8},   # 1h ago
        {"ts": now - 90_000, "kind": "vision_compare", "score": 0.5},  # 25h ago
        {"ts": now - 1800, "kind": "fps", "frame_ms": 18.4},          # 30m ago
    )

    # All within 24h: vision_compare returns 1 (the 25h one drops out)
    r = studio_recent_regressions(hours=24, kind="vision_compare")
    assert r["ok"] is True
    assert r["count"] == 1
    assert r["entries"][0]["score"] == 0.8

    # No kind filter, 24h: 2 entries
    r = studio_recent_regressions(hours=24)
    assert r["count"] == 2

    # Wider window: 26h pulls in the 25h-old vision_compare too
    r = studio_recent_regressions(hours=26, kind="vision_compare")
    assert r["count"] == 2

    # Empty file path returns count 0
    state.paths.qa_regression.unlink()
    r = studio_recent_regressions(hours=24)
    assert r["ok"] is True and r["count"] == 0
    print("OK recent_regressions filtering")


def test_recent_commits_handles_non_repo_directory() -> None:
    state, _ = _fresh_studio()
    # Tempdir is not a git repo; tool should return 0 cleanly without crashing.
    r = studio_recent_commits(limit=5)
    assert r["ok"] is True
    assert r["count"] == 0
    assert "commits" in r and r["commits"] == []
    print("OK recent_commits non-repo fallback")


def test_recent_commits_against_real_repo() -> None:
    state, tmp = _fresh_studio()
    # Init git in tmp and create one commit. Skip if git is absent.
    try:
        subprocess.run(["git", "-C", str(tmp), "init", "-q"], check=True, timeout=10)
        subprocess.run(["git", "-C", str(tmp), "config", "user.email", "test@example.com"], check=True, timeout=10)
        subprocess.run(["git", "-C", str(tmp), "config", "user.name", "Test"], check=True, timeout=10)
        # Stage something — the studio scaffold itself counts.
        (tmp / "README.md").write_text("hi", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp), "add", "README.md"], check=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(tmp), "commit", "-m", "test commit", "--allow-empty-message"],
            check=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("SKIP recent_commits real-repo test (git unavailable)")
        return
    r = studio_recent_commits(limit=5)
    assert r["ok"] is True
    assert r["count"] == 1
    assert r["commits"][0]["subject"]
    assert len(r["commits"][0]["sha"]) == 12
    print("OK recent_commits against real git repo")


def test_write_review_creates_and_appends_same_day() -> None:
    state, _ = _fresh_studio()
    from unitytools.studio.runner import RoleRunResult, ToolCallRecord

    morning = RoleRunResult(
        role_id="producer",
        text="opened 3 tasks. blocker: GDD pillars unclear.",
        tool_calls=[ToolCallRecord(name="studio_get_summary", input={}, result={"ok": True}, ok=True)],
        iterations=2,
        stop_reason="end_turn",
    )
    evening = RoleRunResult(
        role_id="producer",
        text="2 of 3 tasks done. tomorrow: clarify pillars.",
        tool_calls=[],
        iterations=1,
        stop_reason="end_turn",
    )

    fixed = time.mktime(time.strptime("2026-05-10 09:30:00", "%Y-%m-%d %H:%M:%S"))
    rec1 = write_review(state, "morning", morning, now=fixed)
    same_day_pm = fixed + 9 * 3600  # 18:30 same day
    rec2 = write_review(state, "evening", evening, now=same_day_pm)

    assert rec1.path == rec2.path  # both wrote into the same file
    content = Path(rec1.path).read_text(encoding="utf-8")
    assert content.startswith("# 2026-05-10")
    assert "Morning standup" in content and "Evening retro" in content
    assert "opened 3 tasks" in content and "tomorrow: clarify pillars" in content
    # Tool list line shows up only when there are calls
    assert "studio_get_summary" in content
    print("OK write_review same-day append")


def test_run_review_uses_phase_brief_and_persists() -> None:
    state, _ = _fresh_studio()
    fake = FakeLLM([_ScriptedTurn(text="Standup: nothing urgent.")])
    runner = RoleRunner(fake)

    result, record = run_review(state, runner, phase="morning")
    assert result.text.startswith("Standup")
    assert Path(record.path).exists()
    body = Path(record.path).read_text(encoding="utf-8")
    assert "Standup: nothing urgent." in body
    assert "Morning standup" in body
    print("OK run_review persists to reviews/")


def test_loop_runner_once_runs_single_pass() -> None:
    state, _ = _fresh_studio()
    fake = CyclingFakeLLM("morning pass")
    runner = RoleRunner(fake)

    sleep_calls: list[float] = []

    def fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    loop = LoopRunner(state, runner, sleep_fn=fake_sleep)
    stats = loop.run(once=True, interval_seconds=999.0, phase_picker=lambda _now: "morning")
    assert stats.iterations == 1
    assert stats.last_phase == "morning"
    assert sleep_calls == []  # once=True bypasses the sleep loop entirely
    assert fake.calls == 1
    print("OK LoopRunner --once runs exactly one pass")


def test_loop_runner_max_iterations_with_injected_sleep() -> None:
    state, _ = _fresh_studio()
    fake = CyclingFakeLLM("pass")
    runner = RoleRunner(fake)

    sleep_calls: list[float] = []

    def fake_sleep(s: float) -> None:
        sleep_calls.append(s)
        # Simulated time advances; fine because we don't read time elsewhere.

    loop = LoopRunner(state, runner, sleep_fn=fake_sleep)
    # 3-pass loop with 2-second interval — the fake sleep returns immediately,
    # so this completes deterministically without burning real seconds.
    stats = loop.run(
        once=False,
        interval_seconds=2.0,
        max_iterations=3,
        phase_picker=lambda _n: "adhoc",
    )
    assert stats.iterations == 3
    # 2 sleeps between 3 passes (no sleep after the last one)
    assert sum(sleep_calls) == 4.0
    assert fake.calls == 3
    print("OK LoopRunner cadence with injected sleep")


def test_loop_runner_with_dispatch_runs_review_then_dispatch() -> None:
    """When a Dispatcher is wired in, each pass: review writes to disk,
    then dispatch_pending walks the backlog. Verifies the full cycle:
    review file written, pending task picked up by Dispatcher, task moves
    out of PENDING. Pure local — no network, no engine."""
    from unitytools.studio import (
        Dispatcher,
        Task,
        TaskStatus,
    )

    state, _ = _fresh_studio()
    # Seed one designer-owned pending task; the FakeLLM below scripts both
    # the review pass and a designer dispatch pass.
    seeded = state.add_task(
        Task(title="Refine pillars", role="designer", status=TaskStatus.PENDING)
    )

    # Three turns: 1 for review (terminate immediately), 2 for the Designer
    # dispatch run (call studio_update_task_status -> done, then end).
    review_turn = _ScriptedTurn(text="standup OK")
    dispatch_turn_1 = _ScriptedTurn(
        tool_calls=[
            {
                "id": "d1",
                "name": "studio_update_task_status",
                "input": {"task_id": seeded.id, "status": "done"},
            }
        ],
        stop_reason="tool_use",
    )
    dispatch_turn_2 = _ScriptedTurn(text="task done", stop_reason="end_turn")
    fake = FakeLLM([review_turn, dispatch_turn_1, dispatch_turn_2])
    runner = RoleRunner(fake, max_iterations=4)

    dispatcher = Dispatcher(state, lambda _role_id: fake, max_iterations=4)
    loop = LoopRunner(state, runner, dispatcher=dispatcher)

    stats = loop.run(once=True, interval_seconds=999.0, phase_picker=lambda _n: "morning")

    assert stats.iterations == 1
    assert stats.last_record is not None  # review was written
    assert len(stats.dispatch_summaries) == 1
    summary = stats.dispatch_summaries[0]
    assert summary.total == 1
    assert summary.results[0].action == "completed"

    # Task actually moved to DONE
    final = next(t for t in state.load_tasks() if t.id == seeded.id)
    assert final.status is TaskStatus.DONE
    print("OK loop --with-dispatch closes the cycle: review + dispatch")


def test_loop_runner_dispatch_failure_does_not_stop_loop() -> None:
    """If the Dispatcher raises mid-cycle, the loop logs and continues to
    the next iteration. We use a Dispatcher whose dispatch_pending raises
    on the first call but not the second."""
    from unitytools.studio import Dispatcher, Task, TaskStatus

    state, _ = _fresh_studio()
    state.add_task(Task(title="Something", role="designer", status=TaskStatus.PENDING))

    fake = CyclingFakeLLM("review")
    runner = RoleRunner(fake)

    class FlakyDispatcher(Dispatcher):
        calls: int = 0

        def dispatch_pending(self, *args, **kwargs):
            FlakyDispatcher.calls += 1
            if FlakyDispatcher.calls == 1:
                raise RuntimeError("simulated dispatch failure")
            return super().dispatch_pending(*args, **kwargs)

    flaky = FlakyDispatcher(state, lambda _r: fake)

    sleeps: list[float] = []
    loop = LoopRunner(state, runner, sleep_fn=lambda s: sleeps.append(s), dispatcher=flaky)
    stats = loop.run(once=False, interval_seconds=2.0, max_iterations=2, phase_picker=lambda _n: "adhoc")

    # Both iterations completed; first dispatch raised, second ran cleanly
    assert stats.iterations == 2
    assert FlakyDispatcher.calls == 2
    # Only the second dispatch succeeded — first one's exception was caught
    assert len(stats.dispatch_summaries) == 1
    print("OK dispatch failure does not abort loop")


def test_loop_runner_request_stop_breaks_immediately() -> None:
    state, _ = _fresh_studio()
    fake = CyclingFakeLLM("p")
    runner = RoleRunner(fake)

    sleep_calls: list[float] = []
    loop_holder: dict = {}

    def fake_sleep(s: float) -> None:
        sleep_calls.append(s)
        if len(sleep_calls) == 1:
            loop_holder["loop"].request_stop()

    loop = LoopRunner(state, runner, sleep_fn=fake_sleep)
    loop_holder["loop"] = loop
    stats = loop.run(
        once=False,
        interval_seconds=10.0,
        max_iterations=10,
        phase_picker=lambda _n: "adhoc",
    )
    # First pass runs, then sleep_fn requests stop, so no further passes.
    assert stats.iterations == 1
    print("OK LoopRunner respects request_stop mid-sleep")


def run_test() -> None:
    test_recent_regressions_filters_by_age_and_kind()
    test_recent_commits_handles_non_repo_directory()
    test_recent_commits_against_real_repo()
    test_write_review_creates_and_appends_same_day()
    test_run_review_uses_phase_brief_and_persists()
    test_loop_runner_once_runs_single_pass()
    test_loop_runner_max_iterations_with_injected_sleep()
    test_loop_runner_with_dispatch_runs_review_then_dispatch()
    test_loop_runner_dispatch_failure_does_not_stop_loop()
    test_loop_runner_request_stop_breaks_immediately()
    print("All Phase 4 loop tests passed")


if __name__ == "__main__":
    run_test()
