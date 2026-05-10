"""Phase 5 tests: Worker role with engine tools.

Drives the Worker through a realistic backlog task using:
- A FakeUnityBridge that responds to the RPCs our Worker actually
  invokes (create_scene_snapshot, get_scene_catalog, create_primitive,
  set_transform, save_scene, run_visual_qa).
- A FakeVision that returns a pre-set diff so the verify step has
  something concrete to assert against.
- A scripted FakeLLM that walks the Worker through:
  read GDD -> snapshot -> catalog -> place primitive -> set position ->
  save -> screenshot -> compare -> update_task_status(done) -> final text.

The test then verifies:
- All expected RPCs hit the bridge in the right order.
- The task's status flips from in_progress to done.
- A vision_compare entry is appended to qa/regression.jsonl.
- The studio screenshot was copied into qa/screenshots/.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import unitytools.tools as _tools_pkg  # noqa: F401  (registers unity_* tools)
from unitytools.tools import init_tools as _init_engine_tools

from unitytools.studio import (
    Task,
    TaskStatus,
    StudioPaths,
    StudioState,
    WORKER,
    RoleRunner,
    init_studio_tools,
    init_studio_unity,
    init_studio_vision,
)
from unitytools.studio.runner import _filter_tools


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
        self.systems_seen: list[str] = []
        self.tools_seen: list[set[str]] = []

    def complete(self, system, tools, messages):
        self.systems_seen.append(system)
        self.tools_seen.append({t["name"] for t in tools})
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


class FakeVision:
    def __init__(self, diff: dict):
        self.diff = diff
        self.calls: list[dict] = []

    def compare(self, reference_bytes, reference_mime, candidate_bytes, candidate_mime, instruction=""):
        self.calls.append(
            {
                "ref_size": len(reference_bytes),
                "cand_size": len(candidate_bytes),
            }
        )
        return dict(self.diff)


class FakeUnityBridge:
    """Records all RPCs and returns canned responses keyed by method name."""

    def __init__(self, screenshot_source: Path):
        self.screenshot_source = screenshot_source
        self.calls: list[tuple[str, dict]] = []
        self._objects: dict[str, dict] = {}

    def is_connected(self) -> bool:
        return True

    def call(self, method: str, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((method, params))

        if method == "create_scene_snapshot":
            return {"ok": True, "path": "Assets/AutopilotSnapshots/snapshot_001.unity", "label": params.get("label")}

        if method == "get_scene_catalog":
            return {"ok": True, "objects": list(self._objects.values()), "categories": {}}

        if method == "create_primitive":
            name = params.get("name") or params.get("type") or "Cube"
            self._objects[name] = {"name": name, "type": params.get("type"), "position": params.get("position", {"x": 0, "y": 0, "z": 0})}
            return {"ok": True, "name": name, "id": f"go-{len(self._objects)}"}

        if method == "set_transform":
            name = params.get("name", "")
            obj = self._objects.setdefault(name, {"name": name})
            for key in ("position", "rotation", "scale"):
                if key in params:
                    obj[key] = params[key]
            return {"ok": True, "name": name}

        if method == "save_scene":
            return {"ok": True}

        if method == "run_visual_qa":
            return {"ok": True, "screenshot_path": str(self.screenshot_source)}

        if method == "search_assets_semantic" or method == "find_assets":
            return {"ok": True, "count": 0, "results": []}

        raise AssertionError(f"FakeUnityBridge: unhandled method {method!r} (params={params})")


# ───────────────────────────────────────────────── helpers


def _fresh_studio_with_engine() -> tuple[StudioState, Path, FakeUnityBridge]:
    tmp = Path(tempfile.mkdtemp(prefix="worker-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)

    # Fake Unity
    src = tmp / "fake_unity_screenshot.png"
    src.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108020000"
            "00907753DE0000000C49444154789C636060000000040003000160C0"
            "B5C70000000049454E44AE426082"
        )
    )
    bridge = FakeUnityBridge(screenshot_source=src)
    _init_engine_tools(blender_bridge=None, unity_bridge=bridge, unreal_bridge=None)
    init_studio_unity(bridge)
    return state, tmp, bridge


# ──────────────────────────────────────────────────── tests


def test_worker_role_advertises_studio_and_engine_tools_after_registry_loaded() -> None:
    """Validation no longer rejects engine tool names; once unity tools are
    registered (which happens when the Worker test imports them), the runner
    advertises every Worker tool to the LLM."""
    advertised = {t["name"] for t in _filter_tools(WORKER)}
    # Studio side
    assert {"studio_capture_screenshot", "studio_update_task_status", "studio_propose_decision"} <= advertised
    # Engine side
    assert {"unity_create_scene_snapshot", "unity_create_primitive", "unity_set_position", "unity_save_scene"} <= advertised
    # Worker must NOT see studio_write_gdd
    assert "studio_write_gdd" not in advertised
    print("OK Worker role allowlist resolves both studio + unity tools")


def test_worker_executes_place_primitive_task_end_to_end() -> None:
    state, tmp, bridge = _fresh_studio_with_engine()

    # Reference + screenshot prep
    ref = state.paths.refs / "level_target.png"
    ref.write_bytes(b"reference-bytes-here-1234567890")
    init_studio_vision(
        FakeVision(
            {
                "composition_match": 0.82,
                "palette_match": 0.9,
                "missing": [],
                "extra": [],
                "misplaced": [],
                "notes": "Placement matches reference well.",
            }
        )
    )

    # Open task
    task = state.add_task(
        Task(
            title="Place pine tree on the left ridge",
            role="level_designer",
            description=f"Reference: {ref}. Place a Cube placeholder at x=-5 y=0 z=0 on the left ridge.",
            status=TaskStatus.IN_PROGRESS,
        )
    )

    # Scripted turns: snapshot -> catalog -> create_primitive -> set_position ->
    # save -> screenshot -> compare -> update_task_status -> final text.
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "unity_create_scene_snapshot", "input": {"label": f"before_{task.id}"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c2", "name": "unity_get_scene_catalog", "input": {}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c3", "name": "unity_create_primitive", "input": {"type": "Cube", "name": "PineTreePlaceholder"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c4", "name": "unity_set_position", "input": {"name": "PineTreePlaceholder", "x": -5.0, "y": 0.0, "z": 0.0}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c5", "name": "unity_save_scene", "input": {}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c6", "name": "studio_capture_screenshot", "input": {"name": f"{task.id}_after"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c7",
                    "name": "studio_compare_to_reference",
                    "input": {"reference_path": str(ref), "screenshot_path": "__PATCH__"},
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c8", "name": "studio_update_task_status", "input": {"task_id": task.id, "status": "done"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            text="Snapshot created, primitive placed at (-5,0,0), scene saved, vision compare 0.82/0.9 — task done.",
            stop_reason="end_turn",
        ),
    ]
    fake_llm = FakeLLM(turns)

    # The compare call needs the real screenshot path; patch it after capture.
    captured: list[str] = []

    def on_result(name: str, result):
        if name == "studio_capture_screenshot" and isinstance(result, dict) and result.get("ok"):
            captured.append(result["path"])
            for t in turns:
                for tc in t.tool_calls:
                    if tc["name"] == "studio_compare_to_reference":
                        tc["input"]["screenshot_path"] = result["path"]

    runner = RoleRunner(fake_llm, max_iterations=12)
    result = runner.run(WORKER, brief=f"Execute task {task.id}: {task.title}", on_tool_result=on_result)

    assert result.stop_reason == "end_turn"
    tool_names = [tc.name for tc in result.tool_calls]
    assert tool_names == [
        "unity_create_scene_snapshot",
        "unity_get_scene_catalog",
        "unity_create_primitive",
        "unity_set_position",
        "unity_save_scene",
        "studio_capture_screenshot",
        "studio_compare_to_reference",
        "studio_update_task_status",
    ]
    # Bridge saw the right RPCs in order
    bridge_methods = [m for m, _ in bridge.calls]
    assert bridge_methods == [
        "create_scene_snapshot",
        "get_scene_catalog",
        "create_primitive",
        "set_transform",
        "save_scene",
        "run_visual_qa",
    ]

    # Task flipped to done
    final = next(t for t in state.load_tasks() if t.id == task.id)
    assert final.status is TaskStatus.DONE

    # Screenshot ended up in the studio's qa folder
    assert captured and Path(captured[0]).parent == state.paths.qa_screenshots

    # Regression log got a vision_compare row
    log = state.paths.qa_regression.read_text(encoding="utf-8").strip().splitlines()
    assert len(log) == 1
    entry = json.loads(log[0])
    assert entry["kind"] == "vision_compare"
    assert entry["composition_match"] == 0.82

    # Worker system prompt was the one used
    assert "Worker" in fake_llm.systems_seen[0]
    print("OK Worker end-to-end: snapshot -> place -> verify -> mark done")


def test_worker_blocks_task_when_verification_regresses() -> None:
    state, _tmp, bridge = _fresh_studio_with_engine()

    ref = state.paths.refs / "level_target.png"
    ref.write_bytes(b"ref-bytes")
    init_studio_vision(
        FakeVision(
            {
                "composition_match": 0.30,  # well below 0.5
                "palette_match": 0.4,
                "missing": ["entire foreground"],
                "extra": [],
                "misplaced": [],
                "notes": "Composition collapsed.",
            }
        )
    )
    task = state.add_task(
        Task(
            title="Bad placement",
            role="level_designer",
            description=f"Reference: {ref}.",
            status=TaskStatus.IN_PROGRESS,
        )
    )

    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "unity_create_scene_snapshot", "input": {"label": "before"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c2", "name": "studio_capture_screenshot", "input": {"name": "after"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c3",
                    "name": "studio_compare_to_reference",
                    "input": {"reference_path": str(ref), "screenshot_path": "__PATCH__"},
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c4", "name": "studio_update_task_status", "input": {"task_id": task.id, "status": "blocked"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="Verification regressed (0.30 < 0.5) — blocking task.", stop_reason="end_turn"),
    ]
    fake_llm = FakeLLM(turns)

    def on_result(name: str, result):
        if name == "studio_capture_screenshot" and isinstance(result, dict) and result.get("ok"):
            for t in turns:
                for tc in t.tool_calls:
                    if tc["name"] == "studio_compare_to_reference":
                        tc["input"]["screenshot_path"] = result["path"]

    runner = RoleRunner(fake_llm, max_iterations=8)
    result = runner.run(WORKER, brief=f"Execute task {task.id}", on_tool_result=on_result)

    assert result.stop_reason == "end_turn"
    final = next(t for t in state.load_tasks() if t.id == task.id)
    assert final.status is TaskStatus.BLOCKED
    print("OK Worker blocks task on verification regression")


def test_worker_engine_tool_failure_does_not_crash_loop() -> None:
    state, tmp, bridge = _fresh_studio_with_engine()
    init_studio_vision(FakeVision({"composition_match": 1.0}))
    task = state.add_task(Task(title="Tiny", role="level_designer", status=TaskStatus.IN_PROGRESS))

    # FakeUnityBridge raises for an unknown method — the runner should record
    # the failure and the LLM (scripted) should still continue and update status.
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "unity_create_scene_snapshot", "input": {"label": "x"}}],
            stop_reason="tool_use",
        ),
        # Worker tries to call a method the bridge does not know about — the
        # tool wrapper catches the error and returns ok=False.
        _ScriptedTurn(
            tool_calls=[{"id": "c2", "name": "unity_set_parent", "input": {"name": "X", "parent_name": "Y"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[{"id": "c3", "name": "studio_update_task_status", "input": {"task_id": task.id, "status": "blocked"}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="Engine RPC failed; blocking.", stop_reason="end_turn"),
    ]
    fake_llm = FakeLLM(turns)
    runner = RoleRunner(fake_llm, max_iterations=8)
    result = runner.run(WORKER, brief="x")
    # The set_parent record should be ok=False (because FakeUnityBridge raised)
    parent_call = [tc for tc in result.tool_calls if tc.name == "unity_set_parent"]
    assert parent_call and parent_call[0].ok is False
    final = next(t for t in state.load_tasks() if t.id == task.id)
    assert final.status is TaskStatus.BLOCKED
    print("OK Worker survives engine RPC failure, still updates status")


def run_test() -> None:
    test_worker_role_advertises_studio_and_engine_tools_after_registry_loaded()
    test_worker_executes_place_primitive_task_end_to_end()
    test_worker_blocks_task_when_verification_regresses()
    test_worker_engine_tool_failure_does_not_crash_loop()
    print("All Phase 5 worker tests passed")


if __name__ == "__main__":
    run_test()
