"""Phase 29 tests: Camera Director role + studio_camera_frame_check.

Covers: frame happy path + screenshot copy under qa/screenshots,
target-name validation, bridge / capture guards, optional reference
compare wiring, role allowlist (Camera Director can frame but not
place objects or mutate lights), dispatch routing.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ART_DIRECTOR,
    AUDIO_DIRECTOR,
    CAMERA_DIRECTOR,
    DESIGNER,
    DISPATCH_MAP,
    LIGHTING_DIRECTOR,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    WORKER,
    init_studio_tools,
    init_studio_unity,
    init_studio_vision,
)
from unitytools.studio.tools import studio_camera_frame_check


class FakeUnity:
    """Records bridge calls; emits a screenshot file when run_visual_qa fires."""

    def __init__(
        self,
        connected: bool = True,
        frame_ok: bool = True,
        capture_ok: bool = True,
        capture_dir: Path | None = None,
        capture_missing_file: bool = False,
    ):
        self._connected = connected
        self._frame_ok = frame_ok
        self._capture_ok = capture_ok
        self._capture_dir = capture_dir
        self._capture_missing_file = capture_missing_file
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if method == "frame_object":
            if not self._frame_ok:
                raise RuntimeError(f"target object not found: {params.get('target_name')}")
            return {
                "ok": True,
                "camera": "Main Camera",
                "target": params["target_name"],
                "distance": params.get("distance", 5.0),
                "yaw": params["yaw_degrees"],
                "pitch": params["pitch_degrees"],
                "center_x": 0.0, "center_y": 0.0, "center_z": 0.0,
                "camera_position_x": 5.0, "camera_position_y": 2.0, "camera_position_z": -5.0,
                "target_radius": 1.0,
            }
        if method == "run_visual_qa":
            if not self._capture_ok:
                return {"ok": False, "error": "simulated capture failure"}
            assert self._capture_dir is not None
            shot = self._capture_dir / "raw_capture.png"
            if not self._capture_missing_file:
                shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
            return {"ok": True, "screenshot_path": str(shot)}
        raise AssertionError(f"unexpected bridge method: {method}")


class FakeVision:
    """Returns a fixed diff payload from .compare(); records inputs."""

    def __init__(self, diff: dict | None = None):
        self.diff = diff or {"composition_match": 0.78, "palette_match": 0.82}
        self.calls: list[dict] = []

    def compare(self, reference_bytes, reference_mime, candidate_bytes, candidate_mime, instruction=""):
        self.calls.append({
            "ref_size": len(reference_bytes),
            "cand_size": len(candidate_bytes),
            "instruction": instruction,
        })
        return self.diff


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="cam-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── happy path


def test_frame_check_happy_path_no_reference() -> None:
    state, tmp = _fresh_studio()
    capture_dir = tmp / "_unity_caps"
    capture_dir.mkdir()
    fake = FakeUnity(capture_dir=capture_dir)
    init_studio_unity(fake)

    result = studio_camera_frame_check(
        target_name="HeroCube",
        label="hero",
        distance=4.0,
        yaw_degrees=-30,
        pitch_degrees=15,
    )
    assert result["ok"] is True
    assert result["target"] == "HeroCube"
    assert "compare" not in result, "no reference -> no compare block"
    # Screenshot copied under studio/qa/screenshots/
    shot = Path(result["screenshot"])
    assert shot.exists()
    assert shot.parent == state.paths.qa_screenshots
    assert "hero" in shot.name and "HeroCube" in shot.name
    # Bridge saw frame_object first, then run_visual_qa
    methods = [m for (m, _) in fake.calls]
    assert methods == ["frame_object", "run_visual_qa"]
    # frame_object got the distance + angles we requested
    _, frame_params = fake.calls[0]
    assert frame_params["target_name"] == "HeroCube"
    assert frame_params["distance"] == 4.0
    assert frame_params["yaw_degrees"] == -30
    print("OK frame -> capture -> copy works, no reference")


def test_frame_check_with_reference_returns_compare_block() -> None:
    state, tmp = _fresh_studio()
    cap = tmp / "_caps"; cap.mkdir()
    init_studio_unity(FakeUnity(capture_dir=cap))
    vision = FakeVision(diff={"composition_match": 0.62, "palette_match": 0.71})
    init_studio_vision(vision)

    ref = state.paths.refs / "hero.png"
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff" * 64)

    result = studio_camera_frame_check(
        target_name="Hero",
        label="hero_v2",
        reference_path=str(ref),
    )
    assert result["ok"] is True
    assert result["compare"]["ok"] is True
    assert result["compare"]["composition_match"] == 0.62
    # Vision saw bytes for both images
    assert len(vision.calls) == 1
    assert vision.calls[0]["ref_size"] > 0
    assert vision.calls[0]["cand_size"] > 0
    assert "Hero" in vision.calls[0]["instruction"]
    print("OK reference compare wires through and returns scores")


# ───────────────────────────────────────────── validation + guards


def test_frame_check_requires_target_name() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    result = studio_camera_frame_check(target_name="")
    assert result["ok"] is False
    assert "target_name" in result["error"]
    print("OK empty target_name rejected")


def test_frame_check_requires_bridge() -> None:
    state, _ = _fresh_studio()
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_camera_frame_check(target_name="X")
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing bridge -> clean error")


def test_frame_check_requires_connection() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(connected=False))
    result = studio_camera_frame_check(target_name="X")
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error")


def test_frame_check_surfaces_frame_failure() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(frame_ok=False))
    result = studio_camera_frame_check(target_name="MissingObj")
    assert result["ok"] is False
    assert "frame_object failed" in result["error"]
    assert "MissingObj" in result["error"]
    print("OK frame_object failure surfaces with target name")


def test_frame_check_surfaces_capture_failure() -> None:
    state, tmp = _fresh_studio()
    cap = tmp / "_caps"; cap.mkdir()
    init_studio_unity(FakeUnity(capture_dir=cap, capture_ok=False))
    result = studio_camera_frame_check(target_name="X")
    assert result["ok"] is False
    # The frame succeeded; we keep the frame block so the LLM can read what
    # the camera DID move to even when capture failed.
    assert "frame" in result
    print("OK capture failure leaves frame info accessible")


def test_frame_check_surfaces_missing_screenshot_file() -> None:
    state, tmp = _fresh_studio()
    cap = tmp / "_caps"; cap.mkdir()
    init_studio_unity(FakeUnity(capture_dir=cap, capture_missing_file=True))
    result = studio_camera_frame_check(target_name="X")
    assert result["ok"] is False
    assert "does not exist" in result["error"]
    print("OK missing screenshot file caught defensively")


def test_compare_block_handles_missing_reference() -> None:
    state, tmp = _fresh_studio()
    cap = tmp / "_caps"; cap.mkdir()
    init_studio_unity(FakeUnity(capture_dir=cap))
    init_studio_vision(FakeVision())
    result = studio_camera_frame_check(
        target_name="X",
        reference_path=str(tmp / "ghost.png"),
    )
    # Screenshot still produced; compare block reports the issue
    assert result["ok"] is True
    assert result["compare"]["ok"] is False
    assert "not found" in result["compare"]["error"]
    print("OK reference missing -> capture still OK, compare reports error")


def test_compare_block_handles_missing_vision_client() -> None:
    state, tmp = _fresh_studio()
    cap = tmp / "_caps"; cap.mkdir()
    init_studio_unity(FakeUnity(capture_dir=cap))
    import unitytools.studio.tools as st
    st._VISION = None
    ref = state.paths.refs / "r.png"; ref.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = studio_camera_frame_check(target_name="X", reference_path=str(ref))
    assert result["ok"] is True
    assert result["compare"]["ok"] is False
    assert "not injected" in result["compare"]["error"]
    print("OK missing vision -> capture OK, compare cleanly errors")


# ───────────────────────────────────────────── role allowlist


def test_camera_director_owns_framing_tools() -> None:
    assert "studio_camera_frame_check" in CAMERA_DIRECTOR.tool_set
    assert "unity_frame_object" in CAMERA_DIRECTOR.tool_set
    assert "unity_set_camera_transform" in CAMERA_DIRECTOR.tool_set
    assert "unity_list_cameras" in CAMERA_DIRECTOR.tool_set
    assert "unity_set_camera" in CAMERA_DIRECTOR.tool_set  # FOV / clip planes
    # Snapshot + save + lifecycle
    assert "unity_create_scene_snapshot" in CAMERA_DIRECTOR.tool_set
    assert "unity_save_scene" in CAMERA_DIRECTOR.tool_set
    assert "studio_update_task_status" in CAMERA_DIRECTOR.tool_set
    # Reads docs; does not write them
    assert "studio_read_art_bible" in CAMERA_DIRECTOR.tool_set
    assert "studio_write_art_bible" not in CAMERA_DIRECTOR.tool_set
    assert "studio_write_gdd" not in CAMERA_DIRECTOR.tool_set
    # Cannot place/move objects (Worker's job)
    assert "unity_create_primitive" not in CAMERA_DIRECTOR.tool_set
    assert "unity_set_position" not in CAMERA_DIRECTOR.tool_set
    # Cannot mutate lights (Lighting Director's job)
    assert "unity_set_light_properties" not in CAMERA_DIRECTOR.tool_set
    assert "unity_set_ambient_light" not in CAMERA_DIRECTOR.tool_set
    print("OK Camera Director allowlist: framing + verify, no placement, no lighting")


def test_other_roles_lack_camera_mutation_tools() -> None:
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER, LIGHTING_DIRECTOR):
        assert "studio_camera_frame_check" not in role.tool_set, (
            f"{role.id} must not call the camera frame check"
        )
        assert "unity_frame_object" not in role.tool_set, (
            f"{role.id} must not move the camera"
        )
        assert "unity_set_camera_transform" not in role.tool_set, (
            f"{role.id} must not set the camera transform"
        )
    print("OK only Camera Director can frame / move the camera")


def test_camera_director_needs_engine_and_vision() -> None:
    assert CAMERA_DIRECTOR.needs_engine is True
    assert CAMERA_DIRECTOR.needs_vision is True  # uses compare_to_reference
    print("OK Camera Director needs engine + vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_camera_director_to_self() -> None:
    assert DISPATCH_MAP["camera_director"] == "camera_director"
    print("OK DISPATCH_MAP[camera_director] -> camera_director")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["audio_engineer"] == "audio_engineer"
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after camera_director addition")


def run_test() -> None:
    # Happy paths
    test_frame_check_happy_path_no_reference()
    test_frame_check_with_reference_returns_compare_block()
    # Validation + guards
    test_frame_check_requires_target_name()
    test_frame_check_requires_bridge()
    test_frame_check_requires_connection()
    test_frame_check_surfaces_frame_failure()
    test_frame_check_surfaces_capture_failure()
    test_frame_check_surfaces_missing_screenshot_file()
    test_compare_block_handles_missing_reference()
    test_compare_block_handles_missing_vision_client()
    # Role
    test_camera_director_owns_framing_tools()
    test_other_roles_lack_camera_mutation_tools()
    test_camera_director_needs_engine_and_vision()
    # Dispatch
    test_dispatch_map_routes_camera_director_to_self()
    test_existing_routes_unchanged()
    print("All Phase 29 camera director tests passed")


if __name__ == "__main__":
    run_test()
