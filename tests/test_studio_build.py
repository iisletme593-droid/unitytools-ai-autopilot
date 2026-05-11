"""Phase 32 tests: Build Engineer role + studio_build_check preflight.

Covers: preflight pass/fail across each violation kind, bridge guards,
role allowlist (Build Engineer ships but doesn't make), dispatch
routing.
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
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    DISPATCH_MAP,
    LIGHTING_DIRECTOR,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_build_check


class FakeUnity:
    """list_build_scenes returner; each test seeds a payload."""

    def __init__(
        self,
        connected: bool = True,
        payload: dict | None = None,
        raise_exc: bool = False,
    ):
        self._connected = connected
        self._payload = payload
        self._raise = raise_exc
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if self._raise:
            raise RuntimeError("simulated bridge error")
        if method == "list_build_scenes":
            return self._payload or {
                "ok": True,
                "count": 1,
                "enabled_count": 1,
                "active_target": "StandaloneWindows64",
                "scenes": [{"index": 0, "path": "Assets/Scenes/Main.unity", "enabled": True}],
            }
        raise AssertionError(f"unexpected bridge method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="build-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_gdd(state: StudioState, body: str = "# GDD\n\nThe game is about cubes.\n") -> None:
    state.paths.gdd.write_text(body, encoding="utf-8")


# ───────────────────────────────────────────── preflight verdicts


def test_preflight_pass_with_scenes_and_gdd() -> None:
    state, _ = _fresh_studio()
    _seed_gdd(state)
    init_studio_unity(FakeUnity())
    result = studio_build_check()
    assert result["ok"] is True
    assert result["verdict"] == "pass"
    assert result["enabled_scenes"] == 1
    assert result["violations"] == []
    print("OK preflight pass when GDD non-empty + 1 enabled scene")


def test_preflight_fails_when_no_enabled_scenes() -> None:
    state, _ = _fresh_studio()
    _seed_gdd(state)
    init_studio_unity(FakeUnity(payload={
        "ok": True, "count": 2, "enabled_count": 0,
        "active_target": "WebGL", "scenes": [],
    }))
    result = studio_build_check()
    assert result["verdict"] == "fail"
    assert "no_enabled_scenes" in result["violations"]
    assert any("add_scene_to_build" in r for r in result["recommendations"])
    print("OK zero enabled scenes -> violation + recommendation")


def test_preflight_fails_when_gdd_missing() -> None:
    state, _ = _fresh_studio()
    # Do NOT seed GDD
    init_studio_unity(FakeUnity())
    result = studio_build_check()
    assert result["verdict"] == "fail"
    assert "gdd_empty_or_missing" in result["violations"]
    print("OK missing GDD blocks build")


def test_preflight_fails_when_gdd_empty() -> None:
    state, _ = _fresh_studio()
    state.paths.gdd.write_text("   \n  \n", encoding="utf-8")  # whitespace only
    init_studio_unity(FakeUnity())
    result = studio_build_check()
    assert result["verdict"] == "fail"
    assert "gdd_empty_or_missing" in result["violations"]
    print("OK whitespace-only GDD counts as empty")


def test_preflight_can_waive_gdd_requirement() -> None:
    """A user explicitly shipping a tech demo can pass require_gdd=False."""
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    result = studio_build_check(require_gdd=False)
    assert result["verdict"] == "pass"
    assert not any("gdd" in v for v in result["violations"])
    print("OK require_gdd=False waives the GDD check")


def test_preflight_optional_art_bible_check() -> None:
    state, _ = _fresh_studio()
    _seed_gdd(state)
    init_studio_unity(FakeUnity())
    # Default: doesn't check art bible
    pass_result = studio_build_check()
    assert pass_result["verdict"] == "pass"
    # Opting in: art bible missing -> fail
    fail_result = studio_build_check(require_art_bible=True)
    assert fail_result["verdict"] == "fail"
    assert "art_bible_empty_or_missing" in fail_result["violations"]
    print("OK require_art_bible=True opts into the bible check")


def test_preflight_collects_multiple_violations() -> None:
    state, _ = _fresh_studio()
    # No GDD, no art bible, no scenes
    init_studio_unity(FakeUnity(payload={
        "ok": True, "count": 0, "enabled_count": 0,
        "active_target": "StandaloneWindows64", "scenes": [],
    }))
    result = studio_build_check(require_art_bible=True)
    assert result["verdict"] == "fail"
    # All three violations show up — preflight collects, doesn't short-circuit
    assert "no_enabled_scenes" in result["violations"]
    assert "gdd_empty_or_missing" in result["violations"]
    assert "art_bible_empty_or_missing" in result["violations"]
    assert len(result["recommendations"]) >= 3
    print("OK preflight collects every violation (does not short-circuit)")


# ───────────────────────────────────────────── bridge guards


def test_preflight_requires_bridge() -> None:
    state, _ = _fresh_studio()
    _seed_gdd(state)
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_build_check()
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing bridge -> clean error")


def test_preflight_requires_connection() -> None:
    state, _ = _fresh_studio()
    _seed_gdd(state)
    init_studio_unity(FakeUnity(connected=False))
    result = studio_build_check()
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error")


def test_preflight_surfaces_bridge_exception() -> None:
    state, _ = _fresh_studio()
    _seed_gdd(state)
    init_studio_unity(FakeUnity(raise_exc=True))
    result = studio_build_check()
    assert result["ok"] is False
    assert "simulated bridge error" in result["error"]
    print("OK bridge exception surfaces in error")


# ───────────────────────────────────────────── role allowlist


def test_build_engineer_owns_build_tools() -> None:
    assert "studio_build_check" in BUILD_ENGINEER.tool_set
    assert "unity_list_build_scenes" in BUILD_ENGINEER.tool_set
    assert "unity_build_player" in BUILD_ENGINEER.tool_set
    # Reads GDD for context
    assert "studio_read_gdd" in BUILD_ENGINEER.tool_set
    # Lifecycle + escalation
    assert "studio_update_task_status" in BUILD_ENGINEER.tool_set
    assert "studio_add_task" in BUILD_ENGINEER.tool_set
    assert "studio_propose_decision" in BUILD_ENGINEER.tool_set
    # Cannot edit content: GDD, Art Bible
    assert "studio_write_gdd" not in BUILD_ENGINEER.tool_set
    assert "studio_write_art_bible" not in BUILD_ENGINEER.tool_set
    # Cannot mutate the scene
    assert "unity_create_primitive" not in BUILD_ENGINEER.tool_set
    assert "unity_set_position" not in BUILD_ENGINEER.tool_set
    assert "unity_save_scene" not in BUILD_ENGINEER.tool_set
    # Cannot touch UI / lights / camera / particles
    assert "unity_create_ui_canvas" not in BUILD_ENGINEER.tool_set
    assert "unity_set_light_properties" not in BUILD_ENGINEER.tool_set
    assert "unity_frame_object" not in BUILD_ENGINEER.tool_set
    assert "unity_add_particle_system" not in BUILD_ENGINEER.tool_set
    # Phase 48: Build Engineer now CAN add scenes to EditorBuildSettings,
    # but only as the execution arm of Scene Director's catalog. The
    # catalog is the source-of-truth; Build Engineer copies its
    # checklist into the project. (Earlier rule treated this as a
    # "planning gap"; Phase 48 introduced the catalog so there's a
    # proper plan to act on.)
    assert "unity_add_scene_to_build" in BUILD_ENGINEER.tool_set
    assert "studio_read_scene_catalog" in BUILD_ENGINEER.tool_set
    print("OK Build Engineer allowlist: preflight + build + (Phase 48) read catalog & add scenes to build settings")


def test_other_roles_lack_build_tools() -> None:
    """unity_build_player is the most destructive single action in
    the studio (kicks off a 5-30 minute build). It belongs only to
    the Build Engineer."""
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR, UI_BUILDER):
        assert "unity_build_player" not in role.tool_set, (
            f"{role.id} must not build the player — that's Build Engineer's job"
        )
        assert "studio_build_check" not in role.tool_set, (
            f"{role.id} must not run the build preflight"
        )
    print("OK only Build Engineer can build / preflight")


def test_build_engineer_needs_engine_no_vision() -> None:
    assert BUILD_ENGINEER.needs_engine is True
    assert BUILD_ENGINEER.needs_vision is False
    print("OK Build Engineer needs engine, not vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_build_engineer_to_self() -> None:
    assert DISPATCH_MAP["build_engineer"] == "build_engineer"
    print("OK DISPATCH_MAP[build_engineer] -> build_engineer")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    assert DISPATCH_MAP["camera_director"] == "camera_director"
    assert DISPATCH_MAP["vfx_director"] == "vfx_director"
    assert DISPATCH_MAP["ui_builder"] == "ui_builder"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after build_engineer addition")


def run_test() -> None:
    # Preflight verdicts
    test_preflight_pass_with_scenes_and_gdd()
    test_preflight_fails_when_no_enabled_scenes()
    test_preflight_fails_when_gdd_missing()
    test_preflight_fails_when_gdd_empty()
    test_preflight_can_waive_gdd_requirement()
    test_preflight_optional_art_bible_check()
    test_preflight_collects_multiple_violations()
    # Guards
    test_preflight_requires_bridge()
    test_preflight_requires_connection()
    test_preflight_surfaces_bridge_exception()
    # Role
    test_build_engineer_owns_build_tools()
    test_other_roles_lack_build_tools()
    test_build_engineer_needs_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_build_engineer_to_self()
    test_existing_routes_unchanged()
    print("All Phase 32 Build Engineer tests passed")


if __name__ == "__main__":
    run_test()
