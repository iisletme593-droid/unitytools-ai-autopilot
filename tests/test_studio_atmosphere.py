"""Phase 35 tests: Atmosphere Director role + studio_atmosphere_audit.

Covers: audit verdict against each kind of fog/skybox incoherence,
bridge guards, role allowlist (Atmosphere Director owns skybox + fog
only, not lights / camera / objects), dispatch routing.
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
    ATMOSPHERE_DIRECTOR,
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
from unitytools.studio.tools import studio_atmosphere_audit


class FakeUnity:
    def __init__(self, connected: bool = True, payload: dict | None = None, raise_exc: bool = False):
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
        if method == "get_atmosphere_state":
            return self._payload or {
                "ok": True,
                "skybox_present": True,
                "skybox_shader": "Skybox/Procedural",
                "skybox_procedural": True,
                "fog_enabled": False,
                "fog_mode": "ExponentialSquared",
                "fog_density": 0.0,
                "fog_start_distance": 0.0,
                "fog_end_distance": 300.0,
                "fog_color_r": 0.5, "fog_color_g": 0.5, "fog_color_b": 0.5,
                "ambient_intensity": 1.0,
                "ambient_mode": "Skybox",
            }
        raise AssertionError(f"unexpected bridge method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="atmo-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── audit verdicts


def test_audit_pass_with_skybox_and_fog_off() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    result = studio_atmosphere_audit()
    assert result["ok"] is True
    assert result["verdict"] == "pass"
    assert result["skybox_present"] is True
    assert result["fog_enabled"] is False
    assert result["violations"] == []
    print("OK audit verdict=pass when skybox present + fog disabled")


def test_audit_fails_when_no_skybox() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "skybox_present": False,
        "skybox_shader": "",
        "fog_enabled": False,
        "fog_mode": "Linear",
        "fog_density": 0.0,
        "fog_start_distance": 0.0,
        "fog_end_distance": 100.0,
    }))
    result = studio_atmosphere_audit()
    assert result["verdict"] == "fail"
    assert "no_skybox" in result["violations"]
    assert any("unity_set_skybox" in r for r in result["recommendations"])
    print("OK missing skybox -> violation + recommendation")


def test_audit_fails_when_linear_fog_distances_inverted() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "skybox_present": True,
        "skybox_shader": "Skybox/Procedural",
        "fog_enabled": True,
        "fog_mode": "Linear",
        "fog_density": 0.0,
        "fog_start_distance": 80.0,
        "fog_end_distance": 50.0,  # end < start -- bug
    }))
    result = studio_atmosphere_audit()
    assert result["verdict"] == "fail"
    assert "fog_linear_distances_inverted" in result["violations"]
    print("OK linear fog with end<=start -> violation")


def test_audit_fails_when_exp_fog_density_zero() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "skybox_present": True,
        "skybox_shader": "Skybox/Procedural",
        "fog_enabled": True,
        "fog_mode": "ExponentialSquared",
        "fog_density": 0.0,    # enabled but won't render fog
        "fog_start_distance": 0.0,
        "fog_end_distance": 100.0,
    }))
    result = studio_atmosphere_audit()
    assert result["verdict"] == "fail"
    assert "fog_exp_density_zero" in result["violations"]
    print("OK exp fog enabled with zero density -> violation")


def test_audit_pass_when_linear_fog_distances_sane() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "skybox_present": True,
        "skybox_shader": "Skybox/Procedural",
        "fog_enabled": True,
        "fog_mode": "Linear",
        "fog_density": 0.0,
        "fog_start_distance": 10.0,
        "fog_end_distance": 200.0,
    }))
    result = studio_atmosphere_audit()
    assert result["verdict"] == "pass"
    print("OK linear fog with start<end -> pass")


# ───────────────────────────────────────────── bridge guards


def test_audit_requires_bridge() -> None:
    state, _ = _fresh_studio()
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_atmosphere_audit()
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing bridge -> clean error")


def test_audit_requires_connection() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(connected=False))
    result = studio_atmosphere_audit()
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error")


def test_audit_surfaces_bridge_exception() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(raise_exc=True))
    result = studio_atmosphere_audit()
    assert result["ok"] is False
    assert "simulated bridge error" in result["error"]
    print("OK bridge exception surfaces in error")


# ───────────────────────────────────────────── role allowlist


def test_atmosphere_director_owns_atmosphere_tools() -> None:
    assert "studio_atmosphere_audit" in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_get_atmosphere_state" in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_set_skybox" in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_set_fog" in ATMOSPHERE_DIRECTOR.tool_set
    # Snapshot + capture + save + lifecycle
    assert "unity_create_scene_snapshot" in ATMOSPHERE_DIRECTOR.tool_set
    assert "studio_capture_screenshot" in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_save_scene" in ATMOSPHERE_DIRECTOR.tool_set
    assert "studio_update_task_status" in ATMOSPHERE_DIRECTOR.tool_set
    # Reads Art Bible, does NOT write
    assert "studio_read_art_bible" in ATMOSPHERE_DIRECTOR.tool_set
    assert "studio_write_art_bible" not in ATMOSPHERE_DIRECTOR.tool_set
    # Can escalate to art_director
    assert "studio_add_task" in ATMOSPHERE_DIRECTOR.tool_set
    # Cannot touch GDD
    assert "studio_write_gdd" not in ATMOSPHERE_DIRECTOR.tool_set
    # Cannot place objects / lights / camera / particles
    assert "unity_create_primitive" not in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_set_light_properties" not in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_frame_object" not in ATMOSPHERE_DIRECTOR.tool_set
    assert "unity_add_particle_system" not in ATMOSPHERE_DIRECTOR.tool_set
    print("OK Atmosphere Director allowlist: skybox + fog only, no scene mutation, no doc writes")


def test_other_roles_lack_atmosphere_tools() -> None:
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR, UI_BUILDER,
                  BUILD_ENGINEER):
        assert "unity_set_skybox" not in role.tool_set, (
            f"{role.id} must not set the skybox — that's Atmosphere Director's job"
        )
        assert "unity_set_fog" not in role.tool_set, (
            f"{role.id} must not configure fog"
        )
    print("OK only Atmosphere Director can mutate skybox / fog")


def test_atmosphere_director_needs_engine_no_vision() -> None:
    assert ATMOSPHERE_DIRECTOR.needs_engine is True
    assert ATMOSPHERE_DIRECTOR.needs_vision is False
    print("OK Atmosphere Director needs engine, not vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_atmosphere_director_to_self() -> None:
    assert DISPATCH_MAP["atmosphere_director"] == "atmosphere_director"
    print("OK DISPATCH_MAP[atmosphere_director] -> atmosphere_director")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    assert DISPATCH_MAP["camera_director"] == "camera_director"
    assert DISPATCH_MAP["vfx_director"] == "vfx_director"
    assert DISPATCH_MAP["ui_builder"] == "ui_builder"
    assert DISPATCH_MAP["build_engineer"] == "build_engineer"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after atmosphere_director addition")


def run_test() -> None:
    # Audit
    test_audit_pass_with_skybox_and_fog_off()
    test_audit_fails_when_no_skybox()
    test_audit_fails_when_linear_fog_distances_inverted()
    test_audit_fails_when_exp_fog_density_zero()
    test_audit_pass_when_linear_fog_distances_sane()
    # Guards
    test_audit_requires_bridge()
    test_audit_requires_connection()
    test_audit_surfaces_bridge_exception()
    # Role
    test_atmosphere_director_owns_atmosphere_tools()
    test_other_roles_lack_atmosphere_tools()
    test_atmosphere_director_needs_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_atmosphere_director_to_self()
    test_existing_routes_unchanged()
    print("All Phase 35 atmosphere director tests passed")


if __name__ == "__main__":
    run_test()
