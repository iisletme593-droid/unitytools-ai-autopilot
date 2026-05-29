"""Phase 28 tests: Lighting Director role + studio_lighting_audit.

Covers: audit verdict against each budget, bridge guards, role
allowlist (Lighting Director can mutate lights but not place
objects), dispatch routing.
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
    DESIGNER,
    DISPATCH_MAP,
    LIGHTING_DIRECTOR,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    WORKER,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_lighting_audit


class FakeUnity:
    """list_lights returner. Each test seeds a custom payload."""

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
        if method == "list_lights":
            return self._payload or {
                "ok": True,
                "count": 0,
                "total_intensity": 0.0,
                "shadow_casting_count": 0,
                "lights": [],
                "ambient_intensity": 1.0,
                "ambient_mode": "Skybox",
            }
        raise AssertionError(f"unexpected bridge method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="lighting-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── audit verdicts


def test_audit_pass_with_sun_under_all_budgets() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 2,
        "total_intensity": 2.5,
        "shadow_casting_count": 1,
        "ambient_intensity": 1.0,
        "ambient_mode": "Trilight",
        "lights": [
            {"name": "SunLight", "light_type": "Directional", "intensity": 1.5},
            {"name": "FillLight", "light_type": "Point", "intensity": 1.0},
        ],
    }))
    result = studio_lighting_audit()
    assert result["ok"] is True
    assert result["verdict"] == "pass"
    assert result["has_directional"] is True
    assert result["violations"] == []
    print("OK audit verdict=pass when sun + low intensity + few shadows")


def test_audit_fails_when_no_directional() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 1,
        "total_intensity": 1.0,
        "shadow_casting_count": 0,
        "lights": [{"name": "Fill", "light_type": "Point", "intensity": 1.0}],
    }))
    result = studio_lighting_audit()
    assert result["verdict"] == "fail"
    assert "no_directional_light" in result["violations"]
    assert any("Directional" in r for r in result["recommendations"])
    print("OK missing directional -> violation + recommendation")


def test_audit_fails_when_too_many_shadow_casters() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 10,
        "total_intensity": 5.0,
        "shadow_casting_count": 12,
        "lights": [{"name": "Sun", "light_type": "Directional", "intensity": 1.0}],
    }))
    result = studio_lighting_audit(max_shadow_casters=8)
    assert result["verdict"] == "fail"
    assert any("shadow_casters_over_budget" in v for v in result["violations"])
    print("OK too many shadow casters -> violation flagged")


def test_audit_fails_when_total_intensity_over_budget() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 5,
        "total_intensity": 75.0,
        "shadow_casting_count": 1,
        "lights": [{"name": "Sun", "light_type": "Directional", "intensity": 1.0}],
    }))
    result = studio_lighting_audit(max_total_intensity=50.0)
    assert result["verdict"] == "fail"
    assert any("total_intensity_over_budget" in v for v in result["violations"])
    print("OK total intensity over budget -> violation flagged")


def test_audit_fails_when_scene_has_zero_lights() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 0,
        "total_intensity": 0.0,
        "shadow_casting_count": 0,
        "lights": [],
    }))
    result = studio_lighting_audit()
    assert result["verdict"] == "fail"
    assert "scene_has_no_lights" in result["violations"]
    print("OK zero-light scene flagged separately from 'no directional'")


def test_audit_skips_directional_check_when_disabled() -> None:
    """require_directional=False lets a UI-only or indoor scene pass
    without a sun."""
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(payload={
        "ok": True,
        "count": 2,
        "total_intensity": 2.0,
        "shadow_casting_count": 0,
        "lights": [
            {"name": "FillA", "light_type": "Point", "intensity": 1.0},
            {"name": "FillB", "light_type": "Point", "intensity": 1.0},
        ],
    }))
    result = studio_lighting_audit(require_directional=False)
    assert result["verdict"] == "pass"
    assert "no_directional_light" not in result["violations"]
    print("OK require_directional=False bypasses sun check")


# ───────────────────────────────────────────── bridge guards


def test_audit_requires_bridge_injection() -> None:
    state, _ = _fresh_studio()
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_lighting_audit()
    assert result["ok"] is False
    assert "not injected" in result["error"]
    print("OK missing bridge -> clean error")


def test_audit_requires_connection() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(connected=False))
    result = studio_lighting_audit()
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected Unity -> clean error")


def test_audit_surfaces_bridge_exception() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakeUnity(raise_exc=True))
    result = studio_lighting_audit()
    assert result["ok"] is False
    assert "simulated bridge error" in result["error"]
    print("OK bridge exception surfaces in error")


# ───────────────────────────────────────────── role allowlist


def test_lighting_director_owns_lighting_tools() -> None:
    assert "studio_lighting_audit" in LIGHTING_DIRECTOR.tool_set
    assert "unity_list_lights" in LIGHTING_DIRECTOR.tool_set
    assert "unity_create_light" in LIGHTING_DIRECTOR.tool_set
    assert "unity_set_light_properties" in LIGHTING_DIRECTOR.tool_set
    assert "unity_set_ambient_light" in LIGHTING_DIRECTOR.tool_set
    # Snapshot + save + lifecycle
    assert "unity_create_scene_snapshot" in LIGHTING_DIRECTOR.tool_set
    assert "unity_save_scene" in LIGHTING_DIRECTOR.tool_set
    assert "studio_update_task_status" in LIGHTING_DIRECTOR.tool_set
    # Reads Art Bible but does NOT write it
    assert "studio_read_art_bible" in LIGHTING_DIRECTOR.tool_set
    assert "studio_write_art_bible" not in LIGHTING_DIRECTOR.tool_set
    # Cannot edit GDD
    assert "studio_write_gdd" not in LIGHTING_DIRECTOR.tool_set
    # Cannot place / move objects (only adds Light components)
    assert "unity_create_primitive" not in LIGHTING_DIRECTOR.tool_set
    assert "unity_set_position" not in LIGHTING_DIRECTOR.tool_set
    assert "unity_instantiate_best_asset" not in LIGHTING_DIRECTOR.tool_set
    print("OK Lighting Director allowlist: audit + light tools, no scene placement, no doc writes")


def test_other_roles_lack_lighting_mutation_tools() -> None:
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER):
        assert "unity_set_light_properties" not in role.tool_set, (
            f"{role.id} must not mutate lights — that's the Lighting Director"
        )
        assert "unity_set_ambient_light" not in role.tool_set, (
            f"{role.id} must not change ambient lighting"
        )
    print("OK only Lighting Director can mutate lights / ambient")


def test_lighting_director_needs_engine_with_vision() -> None:
    assert LIGHTING_DIRECTOR.needs_engine is True
    assert LIGHTING_DIRECTOR.needs_vision is True  # uses compare_to_reference
    print("OK Lighting Director needs engine + vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_lighting_director_to_self() -> None:
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    print("OK DISPATCH_MAP[lighting_director] -> lighting_director")


def test_existing_routes_unchanged() -> None:
    """Adding the lighting_director rule must not disturb earlier ones."""
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["audio_engineer"] == "audio_engineer"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after lighting_director addition")


def run_test() -> None:
    # Audit
    test_audit_pass_with_sun_under_all_budgets()
    test_audit_fails_when_no_directional()
    test_audit_fails_when_too_many_shadow_casters()
    test_audit_fails_when_total_intensity_over_budget()
    test_audit_fails_when_scene_has_zero_lights()
    test_audit_skips_directional_check_when_disabled()
    # Guards
    test_audit_requires_bridge_injection()
    test_audit_requires_connection()
    test_audit_surfaces_bridge_exception()
    # Role
    test_lighting_director_owns_lighting_tools()
    test_other_roles_lack_lighting_mutation_tools()
    test_lighting_director_needs_engine_with_vision()
    # Dispatch
    test_dispatch_map_routes_lighting_director_to_self()
    test_existing_routes_unchanged()
    print("All Phase 28 lighting tests passed")


if __name__ == "__main__":
    run_test()
