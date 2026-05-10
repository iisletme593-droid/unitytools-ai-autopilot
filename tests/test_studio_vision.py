"""Phase 3 tests: vision tools, fake Unity bridge, fake VisionClient.

Covers:
- studio_capture_screenshot: source PNG copied into studio/qa/screenshots/
- studio_capture_screenshot fails gracefully when bridge is missing or
  Unity is not connected
- studio_compare_to_reference dispatches to the injected VisionClient and
  appends a regression entry on success
- _extract_json_object handles fenced and prose-wrapped vision replies
- LEVEL_DESIGNER and ART_DIRECTOR roles see the right tools (and not the
  wrong ones)
- End-to-end: a scripted FakeLLM drives the Level Designer through
  list_references → capture → compare → add_task with a fake bridge and
  fake vision; tasks land in the backlog with the expected titles.
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

from unitytools.studio import (
    ALL_STUDIO_TOOL_NAMES,
    ART_DIRECTOR,
    LEVEL_DESIGNER,
    RoleRunner,
    StudioPaths,
    StudioState,
    get_role,
    init_studio_tools,
    init_studio_unity,
    init_studio_vision,
)
from unitytools.studio.tools import (
    studio_capture_screenshot,
    studio_compare_to_reference,
    studio_list_references,
)
from unitytools.studio.vision import _extract_json_object


# ──────────────────────────────────────────────────── fakes


class FakeUnityBridge:
    """Drop-in for UnityBridge.is_connected() + .call().

    Pretends to capture a screenshot to a configurable path on disk.
    """

    def __init__(self, screenshot_source: Path, connected: bool = True):
        self.screenshot_source = screenshot_source
        self.connected = connected
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self) -> bool:
        return self.connected

    def call(self, method: str, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if method != "run_visual_qa":
            raise AssertionError(f"unexpected method: {method}")
        return {"ok": True, "screenshot_path": str(self.screenshot_source)}


class FakeVision:
    """VisionClient fake. Returns a canned diff and records inputs."""

    def __init__(self, diff: dict):
        self.diff = diff
        self.calls: list[dict] = []

    def compare(self, reference_bytes, reference_mime, candidate_bytes, candidate_mime, instruction=""):
        self.calls.append(
            {
                "ref_size": len(reference_bytes),
                "ref_mime": reference_mime,
                "cand_size": len(candidate_bytes),
                "cand_mime": candidate_mime,
                "instruction_len": len(instruction),
            }
        )
        return dict(self.diff)


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


# ──────────────────────────────────────────────── helpers


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="vision-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _fake_screenshot_source(tmp: Path) -> Path:
    src = tmp / "fake_unity_screenshot.png"
    # 1×1 PNG so the bytes are real but tiny.
    src.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108020000"
            "00907753DE0000000C49444154789C636060000000040003000160C0"
            "B5C70000000049454E44AE426082"
        )
    )
    return src


# ───────────────────────────────────────────────────── tests


def test_extract_json_object_strips_fences_and_prose() -> None:
    cases = [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('Here you go: {"a": 1, "b": [2,3]} -- enjoy', {"a": 1, "b": [2, 3]}),
        ('```\n{"composition_match": 0.7}\n```', {"composition_match": 0.7}),
    ]
    for raw, expected in cases:
        assert _extract_json_object(raw) == expected
    print("OK _extract_json_object")


def test_capture_screenshot_copies_into_qa_folder() -> None:
    state, tmp = _fresh_studio()
    src = _fake_screenshot_source(tmp)
    bridge = FakeUnityBridge(screenshot_source=src)
    init_studio_unity(bridge)

    result = studio_capture_screenshot(name="level_1")
    assert result["ok"] is True, result
    dest = Path(result["path"])
    assert dest.exists()
    assert dest.parent == state.paths.qa_screenshots
    assert "level_1" in dest.name
    assert dest.read_bytes() == src.read_bytes()
    assert bridge.calls and bridge.calls[0][0] == "run_visual_qa"
    print("OK capture_screenshot copies file into qa/screenshots/")


def test_capture_screenshot_handles_disconnected_bridge() -> None:
    state, tmp = _fresh_studio()
    src = _fake_screenshot_source(tmp)
    init_studio_unity(FakeUnityBridge(src, connected=False))
    result = studio_capture_screenshot(name="x")
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    # Now without any bridge at all
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_capture_screenshot(name="x")
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK capture_screenshot fails cleanly without bridge")


def test_compare_to_reference_dispatches_and_logs() -> None:
    state, tmp = _fresh_studio()
    ref = state.paths.refs / "target.png"
    ref.write_bytes(b"fake-ref-bytes-1234567890")
    cand = state.paths.qa_screenshots / "current.png"
    cand.write_bytes(b"fake-screenshot-bytes-XYZ")

    diff = {
        "composition_match": 0.55,
        "palette_match": 0.8,
        "missing": ["pine tree on left ridge"],
        "extra": ["stray boulder in foreground"],
        "misplaced": [{"item": "campfire", "where_now": "center", "where_should_be": "right of cabin"}],
        "notes": "Composition diverged on the left third.",
    }
    fake = FakeVision(diff)
    init_studio_vision(fake)

    result = studio_compare_to_reference(reference_path=str(ref), screenshot_path=str(cand))
    assert result["ok"] is True
    assert result["composition_match"] == 0.55
    assert result["missing"] == ["pine tree on left ridge"]
    # FakeVision saw both images
    assert fake.calls[0]["ref_size"] == ref.stat().st_size
    assert fake.calls[0]["cand_size"] == cand.stat().st_size

    # regression.jsonl gained one entry
    log_lines = state.paths.qa_regression.read_text(encoding="utf-8").strip().splitlines()
    assert len(log_lines) == 1
    entry = json.loads(log_lines[0])
    assert entry["kind"] == "vision_compare"
    assert entry["composition_match"] == 0.55
    print("OK compare_to_reference dispatches + logs to regression.jsonl")


def test_compare_to_reference_handles_missing_files() -> None:
    state, _ = _fresh_studio()
    init_studio_vision(FakeVision({"composition_match": 1.0}))
    result = studio_compare_to_reference(reference_path=str(state.paths.refs / "nope.png"), screenshot_path="also_nope.png")
    assert result["ok"] is False
    assert "Reference not found" in result["error"]
    print("OK compare_to_reference rejects missing files")


def test_new_roles_see_only_their_tools() -> None:
    valid = set(ALL_STUDIO_TOOL_NAMES)
    assert LEVEL_DESIGNER.tool_set <= valid
    assert ART_DIRECTOR.tool_set <= valid
    # Level Designer can capture + compare; cannot write art bible
    assert "studio_capture_screenshot" in LEVEL_DESIGNER.tool_set
    assert "studio_compare_to_reference" in LEVEL_DESIGNER.tool_set
    assert "studio_write_art_bible" not in LEVEL_DESIGNER.tool_set
    assert "studio_write_gdd" not in LEVEL_DESIGNER.tool_set
    # Art Director can write the bible; cannot touch the GDD
    assert "studio_write_art_bible" in ART_DIRECTOR.tool_set
    assert "studio_write_gdd" not in ART_DIRECTOR.tool_set
    # get_role wires both up
    assert get_role("level_designer") is LEVEL_DESIGNER
    assert get_role("art_director") is ART_DIRECTOR
    print("OK new role tool whitelists are correct")


def test_list_references_returns_file_listing() -> None:
    state, _ = _fresh_studio()
    (state.paths.refs / "alpha.png").write_bytes(b"x")
    (state.paths.refs / "beta.jpg").write_bytes(b"yy")
    result = studio_list_references()
    assert result["ok"] is True
    names = sorted(r["name"] for r in result["references"])
    assert names == ["alpha.png", "beta.jpg"]
    print("OK list_references")


def test_level_designer_end_to_end_with_fake_bridge_and_vision() -> None:
    state, tmp = _fresh_studio()
    # Drop a reference image
    ref = state.paths.refs / "target.png"
    ref.write_bytes(b"reference-image-bytes")
    # Wire up the fake bridge so studio_capture_screenshot writes a file
    src = _fake_screenshot_source(tmp)
    init_studio_unity(FakeUnityBridge(src))
    # Wire up fake vision returning a diff that names one missing item
    init_studio_vision(
        FakeVision(
            {
                "composition_match": 0.45,
                "palette_match": 0.7,
                "missing": ["pine tree on the ridge"],
                "extra": [],
                "misplaced": [],
                "notes": "Left ridge silhouette is missing.",
            }
        )
    )

    # Scripted LLM walks Level Designer through the workflow
    turns = [
        _ScriptedTurn(tool_calls=[{"id": "c1", "name": "studio_list_references", "input": {}}], stop_reason="tool_use"),
        _ScriptedTurn(tool_calls=[{"id": "c2", "name": "studio_capture_screenshot", "input": {"name": "level_1"}}], stop_reason="tool_use"),
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c3",
                    "name": "studio_compare_to_reference",
                    "input": {"reference_path": str(ref), "screenshot_path": "__PLACEHOLDER__"},
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c4",
                    "name": "studio_add_task",
                    "input": {
                        "title": "Place pine tree on the ridge",
                        "role": "level_designer",
                        "description": "Reference shows a pine tree silhouette on the left ridge; current scene is missing it.",
                    },
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            text="composition_match=0.45 palette_match=0.7\ntop missing: pine tree on the ridge\nopened 1 task",
            stop_reason="end_turn",
        ),
    ]

    # The scripted compare call needs the real screenshot path. We fix it up
    # by driving the runner through the first two turns, reading the captured
    # path from the result, then patching turn 3.
    runner = RoleRunner(FakeLLM([]), max_iterations=8)
    runner.client = FakeLLM(turns)

    captured_paths: list[str] = []

    def on_result(name, result):
        if name == "studio_capture_screenshot" and isinstance(result, dict) and result.get("ok"):
            captured_paths.append(result["path"])
            # Patch the upcoming compare call's screenshot_path
            for t in turns:
                for tc in t.tool_calls:
                    if tc["name"] == "studio_compare_to_reference":
                        tc["input"]["screenshot_path"] = result["path"]

    result = runner.run(LEVEL_DESIGNER, brief="Audit level 1 against the target reference.", on_tool_result=on_result)
    assert result.stop_reason == "end_turn"
    tool_names = [tc.name for tc in result.tool_calls]
    assert tool_names == [
        "studio_list_references",
        "studio_capture_screenshot",
        "studio_compare_to_reference",
        "studio_add_task",
    ]
    assert captured_paths and Path(captured_paths[0]).exists()

    tasks = state.load_tasks()
    assert len(tasks) == 1
    assert tasks[0].title.startswith("Place pine tree")
    assert tasks[0].role == "level_designer"

    # Vision compare wrote a regression entry
    log = state.paths.qa_regression.read_text(encoding="utf-8").strip()
    assert '"vision_compare"' in log
    print("OK level_designer end-to-end with fake bridge + fake vision")


def run_test() -> None:
    test_extract_json_object_strips_fences_and_prose()
    test_capture_screenshot_copies_into_qa_folder()
    test_capture_screenshot_handles_disconnected_bridge()
    test_compare_to_reference_dispatches_and_logs()
    test_compare_to_reference_handles_missing_files()
    test_new_roles_see_only_their_tools()
    test_list_references_returns_file_listing()
    test_level_designer_end_to_end_with_fake_bridge_and_vision()
    print("All Phase 3 vision tests passed")


if __name__ == "__main__":
    run_test()
