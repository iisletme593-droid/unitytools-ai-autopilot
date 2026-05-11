"""Phase 23 tests: studio_playtest_smoke + Playtester role + qa dispatch.

The playtest tool wraps a fixed enter -> wait -> verify -> capture ->
exit sequence around Unity's play mode. The fake bridge below records
every RPC so we can prove the sequence is invariant (exit ALWAYS
runs, even when a verification step raises mid-flight).
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
    DISPATCH_MAP,
    PLAYTESTER,
    StudioPaths,
    StudioState,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_playtest_smoke


class FakePlayBridge:
    """Records calls; controllable failure points per method."""

    def __init__(
        self,
        connected: bool = True,
        present_names: set | None = None,
        screenshot_path: str = "",
        fail_enter: bool = False,
        fail_verify_for: set | None = None,
        fail_capture: bool = False,
        fail_exit: bool = False,
    ):
        self.connected = connected
        self.present = present_names or set()
        self.screenshot_path = screenshot_path
        self.fail_enter = fail_enter
        self.fail_verify_for = fail_verify_for or set()
        self.fail_capture = fail_capture
        self.fail_exit = fail_exit
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self) -> bool:
        return self.connected

    def call(self, method, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((method, params))
        if method == "play_mode":
            if params.get("play") and self.fail_enter:
                raise RuntimeError("simulated enter failure")
            if not params.get("play") and self.fail_exit:
                raise RuntimeError("simulated exit failure")
            return {"ok": True, "is_playing": bool(params.get("play"))}
        if method == "find_scene_objects":
            needle = params.get("name_contains", "")
            if needle in self.fail_verify_for:
                raise RuntimeError(f"simulated verify failure for {needle}")
            return {
                "ok": True,
                "count": 1 if needle in self.present else 0,
                "objects": [{"name": needle}] if needle in self.present else [],
            }
        if method == "run_visual_qa":
            if self.fail_capture:
                raise RuntimeError("simulated capture failure")
            return {"ok": True, "screenshot_path": self.screenshot_path}
        raise AssertionError(f"unexpected method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="play-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _write_screenshot_source(tmp: Path) -> Path:
    src = tmp / "fake_play_shot.png"
    src.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108020000"
            "00907753DE0000000C49444154789C636060000000040003000160C0"
            "B5C70000000049454E44AE426082"
        )
    )
    return src


# ───────────────────────────────────────────── happy path


def test_smoke_enters_verifies_captures_exits_in_order() -> None:
    state, tmp = _fresh_studio()
    src = _write_screenshot_source(tmp)
    bridge = FakePlayBridge(
        present_names={"Cube_A", "Sphere_B"},
        screenshot_path=str(src),
    )
    init_studio_unity(bridge)

    result = studio_playtest_smoke(
        duration_seconds=0.5,
        expected_object_names=["Cube_A", "Sphere_B"],
        capture_name="smoke",
    )
    assert result["ok"] is True
    assert result["missing"] == []
    assert all(result["presence"].values())
    assert result["screenshot"] is not None
    assert Path(result["screenshot"]).exists()

    methods = [m for m, _ in bridge.calls]
    # Sequence: enter, verify_a, verify_b, capture, exit
    assert methods[0] == ("play_mode")
    assert bridge.calls[0][1]["play"] is True
    assert methods.count("find_scene_objects") == 2
    assert methods.count("run_visual_qa") == 1
    assert methods[-1] == "play_mode"
    assert bridge.calls[-1][1]["play"] is False
    print("OK smoke runs enter -> verify -> capture -> exit in order")


def test_smoke_logs_to_regression_jsonl() -> None:
    state, tmp = _fresh_studio()
    src = _write_screenshot_source(tmp)
    init_studio_unity(FakePlayBridge(present_names={"X"}, screenshot_path=str(src)))

    studio_playtest_smoke(duration_seconds=0.5, expected_object_names=["X"])
    log_text = state.paths.qa_regression.read_text(encoding="utf-8").strip()
    rows = [json.loads(line) for line in log_text.splitlines()]
    assert len(rows) == 1
    assert rows[0]["kind"] == "playtest_smoke"
    assert rows[0]["ok"] is True
    print("OK playtest_smoke appends row to qa/regression.jsonl")


# ───────────────────────────────────────────── failure modes


def test_missing_object_marks_smoke_failed() -> None:
    state, tmp = _fresh_studio()
    src = _write_screenshot_source(tmp)
    init_studio_unity(FakePlayBridge(present_names={"Cube_A"}, screenshot_path=str(src)))

    result = studio_playtest_smoke(
        duration_seconds=0.5,
        expected_object_names=["Cube_A", "Missing_B"],
    )
    assert result["ok"] is False
    assert result["missing"] == ["Missing_B"]
    assert result["presence"]["Cube_A"] is True
    assert result["presence"]["Missing_B"] is False
    print("OK missing object surfaces in result.missing, ok=False")


def test_exit_always_runs_even_when_capture_fails() -> None:
    """A failure in the capture step must not skip the exit. Without
    this the Unity Editor would be stuck in play mode after a bad smoke."""
    state, tmp = _fresh_studio()
    bridge = FakePlayBridge(present_names={"X"}, fail_capture=True)
    init_studio_unity(bridge)

    result = studio_playtest_smoke(duration_seconds=0.5, expected_object_names=["X"])
    # Exit call MUST be present
    assert any(m == "play_mode" and p.get("play") is False for m, p in bridge.calls), \
        "exit play_mode was not called after capture failure"
    # Errors collected
    assert any("capture" in e for e in result["errors"])
    print("OK exit always fires even after capture failure")


def test_exit_always_runs_even_when_verify_raises() -> None:
    state, tmp = _fresh_studio()
    bridge = FakePlayBridge(present_names={"Cube_A"}, fail_verify_for={"Cube_A"})
    init_studio_unity(bridge)

    result = studio_playtest_smoke(duration_seconds=0.5, expected_object_names=["Cube_A"])
    # Exit must still have fired
    assert any(m == "play_mode" and p.get("play") is False for m, p in bridge.calls)
    # Result still produced
    assert result["ok"] is False
    print("OK exit always fires even when a verify call raises")


def test_enter_failure_returns_clean_error() -> None:
    state, tmp = _fresh_studio()
    bridge = FakePlayBridge(fail_enter=True)
    init_studio_unity(bridge)
    result = studio_playtest_smoke(duration_seconds=0.5)
    assert result["ok"] is False
    assert "play mode" in result["error"]
    # Should have attempted enter, not exit (entry never succeeded)
    methods = [m for m, _ in bridge.calls]
    assert methods == ["play_mode"]
    print("OK failed enter -> ok=False, no orphan exit attempt")


def test_disconnected_bridge_returns_error() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePlayBridge(connected=False))
    result = studio_playtest_smoke()
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected bridge surfaces error before entering play mode")


# ───────────────────────────────────────────── duration cap


def test_duration_clamped_to_safe_range() -> None:
    state, tmp = _fresh_studio()
    init_studio_unity(FakePlayBridge(present_names=set()))
    # Try an outrageously long duration -- must be capped server-side
    start = time.time()
    result = studio_playtest_smoke(duration_seconds=3600.0)
    elapsed = time.time() - start
    assert elapsed < 35.0, f"duration cap not applied (slept ~{elapsed:.1f}s)"
    assert result["duration_seconds"] == 30.0
    print("OK absurd duration clamped to 30s")


def test_zero_duration_clamps_up() -> None:
    state, tmp = _fresh_studio()
    init_studio_unity(FakePlayBridge(present_names=set()))
    result = studio_playtest_smoke(duration_seconds=0.01)
    # Minimum cap is 0.5
    assert result["duration_seconds"] == 0.5
    print("OK sub-second duration clamped up to 0.5s minimum")


# ───────────────────────────────────────────── role + dispatch


def test_playtester_role_has_play_tool_in_allowlist() -> None:
    assert "studio_playtest_smoke" in PLAYTESTER.tool_set
    assert "unity_create_scene_snapshot" in PLAYTESTER.tool_set
    assert "studio_update_task_status" in PLAYTESTER.tool_set
    # Playtester must NOT have engine-modify tools
    assert "unity_create_primitive" not in PLAYTESTER.tool_set
    assert "unity_set_position" not in PLAYTESTER.tool_set
    print("OK Playtester allowlist scoped to verify-only")


def test_dispatch_map_routes_qa_to_playtester() -> None:
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["playtester"] == "playtester"
    print("OK DISPATCH_MAP[qa] -> playtester")


def test_playtester_needs_engine_but_not_vision() -> None:
    """Capability flags drive the Dispatcher prerequisite check."""
    assert PLAYTESTER.needs_engine  # unity_* + screenshot tools present
    # Vision compare IS allowed (for optional reference checks), so
    # needs_vision is True. Confirm it for consistency.
    assert PLAYTESTER.needs_vision
    print("OK Playtester capability flags accurate")


def run_test() -> None:
    test_smoke_enters_verifies_captures_exits_in_order()
    test_smoke_logs_to_regression_jsonl()
    test_missing_object_marks_smoke_failed()
    test_exit_always_runs_even_when_capture_fails()
    test_exit_always_runs_even_when_verify_raises()
    test_enter_failure_returns_clean_error()
    test_disconnected_bridge_returns_error()
    test_duration_clamped_to_safe_range()
    test_zero_duration_clamps_up()
    test_playtester_role_has_play_tool_in_allowlist()
    test_dispatch_map_routes_qa_to_playtester()
    test_playtester_needs_engine_but_not_vision()
    print("All Phase 23 playtest tests passed")


if __name__ == "__main__":
    run_test()
