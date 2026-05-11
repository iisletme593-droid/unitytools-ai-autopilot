"""Phase 30 tests: VFX Director role + studio_vfx_audit.

Covers: audit verdict against each budget, bridge guards, role
allowlist (VFX Director adds + tunes particles but doesn't place
objects, light, or frame), dispatch routing.
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
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_vfx_audit


class FakeUnity:
    """list_particle_systems returner; each test seeds a payload."""

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
        if method == "list_particle_systems":
            return self._payload or {
                "ok": True,
                "count": 0,
                "total_emission_rate": 0.0,
                "total_max_particles": 0,
                "systems": [],
            }
        raise AssertionError(f"unexpected bridge method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="vfx-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── audit verdicts


def test_audit_pass_when_under_all_budgets() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 3,
        "total_emission_rate": 90.0,
        "total_max_particles": 3000,
        "systems": [
            {"name": "DustA", "emission_rate": 30.0, "max_particles": 1000},
            {"name": "DustB", "emission_rate": 30.0, "max_particles": 1000},
            {"name": "FireC", "emission_rate": 30.0, "max_particles": 1000},
        ],
    }))
    result = studio_vfx_audit()
    assert result["ok"] is True
    assert result["verdict"] == "pass"
    assert result["violations"] == []
    print("OK audit verdict=pass under all budgets")


def test_audit_fails_when_too_many_systems() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 20,
        "total_emission_rate": 100.0,
        "total_max_particles": 1000,
        "systems": [{"name": f"PS{i}", "emission_rate": 5.0, "max_particles": 50} for i in range(20)],
    }))
    result = studio_vfx_audit(max_systems=12)
    assert result["verdict"] == "fail"
    assert any("too_many_systems" in v for v in result["violations"])
    print("OK too many systems -> violation flagged")


def test_audit_fails_when_emission_over_budget() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 3,
        "total_emission_rate": 800.0,
        "total_max_particles": 1000,
        "systems": [
            {"name": "QuietA", "emission_rate": 50.0, "max_particles": 100},
            {"name": "LoudA", "emission_rate": 400.0, "max_particles": 500},
            {"name": "LoudB", "emission_rate": 350.0, "max_particles": 400},
        ],
    }))
    result = studio_vfx_audit(max_total_emission=400.0)
    assert result["verdict"] == "fail"
    assert any("emission_over_budget" in v for v in result["violations"])
    # Recommendation names the two loudest systems
    recs = " ".join(result["recommendations"])
    assert "LoudA" in recs and "LoudB" in recs
    print("OK emission over budget -> names loudest offenders in recommendation")


def test_audit_fails_when_max_particles_over_budget() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 2,
        "total_emission_rate": 50.0,
        "total_max_particles": 15000,
        "systems": [
            {"name": "BigA", "emission_rate": 25.0, "max_particles": 8000},
            {"name": "BigB", "emission_rate": 25.0, "max_particles": 7000},
        ],
    }))
    result = studio_vfx_audit(max_total_particles=8000)
    assert result["verdict"] == "fail"
    assert any("max_particles_over_budget" in v for v in result["violations"])
    print("OK max_particles over budget -> violation flagged")


def test_audit_empty_scene_passes() -> None:
    """Zero particle systems is a valid 'pass' state — VFX is optional."""
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity())
    result = studio_vfx_audit()
    assert result["verdict"] == "pass"
    assert result["count"] == 0
    print("OK empty scene -> pass (VFX is optional)")


# ───────────────────────────────────────────── bridge guards


def test_audit_requires_bridge() -> None:
    state, _ = _fresh_studio()
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_vfx_audit()
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing bridge -> clean error")


def test_audit_requires_connection() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(connected=False))
    result = studio_vfx_audit()
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error")


def test_audit_surfaces_bridge_exception() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(raise_exc=True))
    result = studio_vfx_audit()
    assert result["ok"] is False
    assert "simulated bridge error" in result["error"]
    print("OK bridge exception surfaces in error")


# ───────────────────────────────────────────── role allowlist


def test_vfx_director_owns_particle_tools() -> None:
    assert "studio_vfx_audit" in VFX_DIRECTOR.tool_set
    assert "unity_list_particle_systems" in VFX_DIRECTOR.tool_set
    assert "unity_add_particle_system" in VFX_DIRECTOR.tool_set
    assert "unity_set_particle_properties" in VFX_DIRECTOR.tool_set
    # Snapshot + capture + save + lifecycle
    assert "unity_create_scene_snapshot" in VFX_DIRECTOR.tool_set
    assert "studio_capture_screenshot" in VFX_DIRECTOR.tool_set
    assert "unity_save_scene" in VFX_DIRECTOR.tool_set
    assert "studio_update_task_status" in VFX_DIRECTOR.tool_set
    # Reads Art Bible but does NOT write it
    assert "studio_read_art_bible" in VFX_DIRECTOR.tool_set
    assert "studio_write_art_bible" not in VFX_DIRECTOR.tool_set
    # Cannot edit GDD
    assert "studio_write_gdd" not in VFX_DIRECTOR.tool_set
    # Cannot place / move objects
    assert "unity_create_primitive" not in VFX_DIRECTOR.tool_set
    assert "unity_set_position" not in VFX_DIRECTOR.tool_set
    # Cannot touch lights or camera
    assert "unity_set_light_properties" not in VFX_DIRECTOR.tool_set
    assert "unity_frame_object" not in VFX_DIRECTOR.tool_set
    print("OK VFX Director allowlist: particles only, no scene placement / lights / camera / docs")


def test_other_roles_lack_particle_tools() -> None:
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR):
        assert "unity_add_particle_system" not in role.tool_set, (
            f"{role.id} must not add particle systems — that's the VFX Director"
        )
        assert "unity_set_particle_properties" not in role.tool_set, (
            f"{role.id} must not tune particle properties"
        )
    print("OK only VFX Director can add / tune particle systems")


def test_vfx_director_needs_engine_no_vision() -> None:
    assert VFX_DIRECTOR.needs_engine is True
    assert VFX_DIRECTOR.needs_vision is False  # no reference compare
    print("OK VFX Director needs engine, not vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_vfx_director_to_self() -> None:
    assert DISPATCH_MAP["vfx_director"] == "vfx_director"
    print("OK DISPATCH_MAP[vfx_director] -> vfx_director")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["audio_engineer"] == "audio_engineer"
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    assert DISPATCH_MAP["camera_director"] == "camera_director"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after vfx_director addition")


def run_test() -> None:
    # Audit
    test_audit_pass_when_under_all_budgets()
    test_audit_fails_when_too_many_systems()
    test_audit_fails_when_emission_over_budget()
    test_audit_fails_when_max_particles_over_budget()
    test_audit_empty_scene_passes()
    # Guards
    test_audit_requires_bridge()
    test_audit_requires_connection()
    test_audit_surfaces_bridge_exception()
    # Role
    test_vfx_director_owns_particle_tools()
    test_other_roles_lack_particle_tools()
    test_vfx_director_needs_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_vfx_director_to_self()
    test_existing_routes_unchanged()
    print("All Phase 30 VFX director tests passed")


if __name__ == "__main__":
    run_test()
