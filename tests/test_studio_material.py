"""Phase 36 tests: Material Artist role + PBR tool wrappers.

Covers: unity_set_material_pbr param forwarding (partial updates,
emission, clamping), validation, role allowlist (Material Artist
owns PBR — Worker owns base color, doc roles don't touch materials),
dispatch routing.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import unitytools.tools.unity_tools as unity_tools
from unitytools.studio import (
    ART_DIRECTOR,
    ATMOSPHERE_DIRECTOR,
    AUDIO_DIRECTOR,
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    DISPATCH_MAP,
    LIGHTING_DIRECTOR,
    MATERIAL_ARTIST,
    PHYSICS_QA,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
)
from unitytools.tools.unity_tools import (
    unity_get_material_properties,
    unity_set_material_pbr,
)


class FakeUnity:
    def __init__(self, connected: bool = True, raise_on_method: str = ""):
        self._connected = connected
        self._raise_on = raise_on_method
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if self._raise_on and method == self._raise_on:
            raise RuntimeError(f"simulated failure on {method}")
        if method == "set_material_pbr":
            return {
                "ok": True,
                "target": params["name"],
                "material": "TestMat",
                "shader": "Universal Render Pipeline/Lit",
                "metallic": params.get("metallic", 0.0),
                "smoothness": params.get("smoothness", 0.5),
                "emission_enabled": bool(params.get("emission_enabled", False)),
            }
        if method == "get_material_properties":
            return {
                "ok": True,
                "target": params["name"],
                "material": "TestMat",
                "shader": "Universal Render Pipeline/Lit",
                "base_color_r": 0.5, "base_color_g": 0.5, "base_color_b": 0.5, "base_color_a": 1.0,
                "metallic": 0.0,
                "smoothness": 0.5,
                "emission_enabled": False,
                "emission_color_r": 0.0, "emission_color_g": 0.0, "emission_color_b": 0.0,
            }
        raise AssertionError(f"unexpected bridge method: {method}")


# ───────────────────────────────────────────── wrapper happy paths


def test_set_pbr_gold_preset_forwards_metallic_smoothness() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_set_material_pbr(
        target_name="Treasure",
        metallic=1.0,
        smoothness=0.85,
    )
    assert result["ok"] is True
    method, params = fake.calls[0]
    assert method == "set_material_pbr"
    assert params["name"] == "Treasure"
    assert params["metallic"] == 1.0
    assert params["smoothness"] == 0.85
    # Emission fields should be omitted (user didn't ask)
    assert "emission_enabled" not in params
    assert "emission_color" not in params
    print("OK gold preset: forwards metallic + smoothness, omits emission")


def test_set_pbr_magic_crystal_with_emission() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_set_material_pbr(
        target_name="MagicOrb",
        metallic=0.0,
        smoothness=0.95,
        emission_enabled=1,
        emission_r=0.6, emission_g=0.3, emission_b=0.95,
        emission_intensity=2.5,
    )
    assert result["ok"] is True
    _, params = fake.calls[0]
    assert params["emission_enabled"] is True
    assert params["emission_color"] == {"r": 0.6, "g": 0.3, "b": 0.95, "a": 1.0}
    assert params["emission_intensity"] == 2.5
    print("OK magic crystal: forwards emission enable + color + intensity")


def test_set_pbr_partial_update_only_emission_off() -> None:
    """User wants to disable emission only — don't stomp metallic/smoothness."""
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_set_material_pbr(target_name="Lamp", emission_enabled=0)
    assert result["ok"] is True
    _, params = fake.calls[0]
    assert "metallic" not in params
    assert "smoothness" not in params
    assert params["emission_enabled"] is False
    print("OK partial update: only emission_enabled forwarded")


def test_set_pbr_clamps_metallic_to_unit_range() -> None:
    """metallic > 1 is a bug; wrapper clamps so the bridge doesn't see junk."""
    fake = FakeUnity()
    unity_tools._UNITY = fake
    unity_set_material_pbr(target_name="X", metallic=5.0, smoothness=2.5)
    _, params = fake.calls[0]
    assert params["metallic"] == 1.0
    assert params["smoothness"] == 1.0
    print("OK metallic + smoothness clamped to [0,1]")


# ───────────────────────────────────────────── validation


def test_set_pbr_requires_target_name() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_set_material_pbr(target_name="", metallic=0.5)
    assert result["ok"] is False
    assert "target_name" in result["error"]
    print("OK empty target_name rejected")


def test_set_pbr_requires_bridge() -> None:
    unity_tools._UNITY = None
    result = unity_set_material_pbr(target_name="X", metallic=0.5)
    assert result["ok"] is False
    assert "not initialized" in result["error"]
    print("OK missing bridge -> clean error")


def test_set_pbr_surfaces_bridge_exception() -> None:
    unity_tools._UNITY = FakeUnity(raise_on_method="set_material_pbr")
    result = unity_set_material_pbr(target_name="X", metallic=0.5)
    assert result["ok"] is False
    assert "simulated failure" in result["error"]
    print("OK bridge exception surfaces clean error")


def test_get_material_properties_round_trip() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_get_material_properties("Treasure")
    assert result["ok"] is True
    assert "metallic" in result
    assert "smoothness" in result
    assert "emission_enabled" in result
    method, params = fake.calls[0]
    assert method == "get_material_properties"
    assert params["name"] == "Treasure"
    print("OK get_material_properties forwards target + returns props")


def test_get_material_properties_requires_target() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_get_material_properties("")
    assert result["ok"] is False
    assert "target_name" in result["error"]
    print("OK get_material_properties: empty target rejected")


# ───────────────────────────────────────────── role allowlist


def test_material_artist_owns_pbr_tools() -> None:
    assert "unity_set_material_pbr" in MATERIAL_ARTIST.tool_set
    assert "unity_get_material_properties" in MATERIAL_ARTIST.tool_set
    # Reads Art Bible, does NOT write
    assert "studio_read_art_bible" in MATERIAL_ARTIST.tool_set
    assert "studio_write_art_bible" not in MATERIAL_ARTIST.tool_set
    # Snapshot + capture + save + lifecycle
    assert "unity_create_scene_snapshot" in MATERIAL_ARTIST.tool_set
    assert "studio_capture_screenshot" in MATERIAL_ARTIST.tool_set
    assert "unity_save_scene" in MATERIAL_ARTIST.tool_set
    assert "studio_update_task_status" in MATERIAL_ARTIST.tool_set
    # Visual compare for refinement
    assert "studio_compare_to_reference" in MATERIAL_ARTIST.tool_set
    # Cannot do base color (Worker's job) — material_artist tunes PBR only
    assert "unity_set_material_color" not in MATERIAL_ARTIST.tool_set
    # Cannot place / move objects
    assert "unity_create_primitive" not in MATERIAL_ARTIST.tool_set
    assert "unity_set_position" not in MATERIAL_ARTIST.tool_set
    # Cannot touch lights / camera / sky / particles / GDD
    assert "unity_set_light_properties" not in MATERIAL_ARTIST.tool_set
    assert "unity_frame_object" not in MATERIAL_ARTIST.tool_set
    assert "unity_set_skybox" not in MATERIAL_ARTIST.tool_set
    assert "unity_add_particle_system" not in MATERIAL_ARTIST.tool_set
    assert "studio_write_gdd" not in MATERIAL_ARTIST.tool_set
    print("OK Material Artist allowlist: PBR + inspect + capture, no base-color, no scene mutation, no doc writes")


def test_other_roles_lack_pbr_mutation() -> None:
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR, UI_BUILDER,
                  BUILD_ENGINEER, ATMOSPHERE_DIRECTOR):
        assert "unity_set_material_pbr" not in role.tool_set, (
            f"{role.id} must not tune PBR — that's Material Artist's job"
        )
    print("OK only Material Artist can mutate PBR properties")


def test_material_artist_needs_engine_and_vision() -> None:
    """Engine to mutate the material, vision to compare against a reference
    image for fine-tuning."""
    assert MATERIAL_ARTIST.needs_engine is True
    assert MATERIAL_ARTIST.needs_vision is True
    print("OK Material Artist needs engine + vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_material_artist_to_self() -> None:
    assert DISPATCH_MAP["material_artist"] == "material_artist"
    print("OK DISPATCH_MAP[material_artist] -> material_artist")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    assert DISPATCH_MAP["camera_director"] == "camera_director"
    assert DISPATCH_MAP["vfx_director"] == "vfx_director"
    assert DISPATCH_MAP["ui_builder"] == "ui_builder"
    assert DISPATCH_MAP["build_engineer"] == "build_engineer"
    assert DISPATCH_MAP["atmosphere_director"] == "atmosphere_director"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after material_artist addition")


def run_test() -> None:
    # Happy paths
    test_set_pbr_gold_preset_forwards_metallic_smoothness()
    test_set_pbr_magic_crystal_with_emission()
    test_set_pbr_partial_update_only_emission_off()
    test_set_pbr_clamps_metallic_to_unit_range()
    # Validation
    test_set_pbr_requires_target_name()
    test_set_pbr_requires_bridge()
    test_set_pbr_surfaces_bridge_exception()
    test_get_material_properties_round_trip()
    test_get_material_properties_requires_target()
    # Role
    test_material_artist_owns_pbr_tools()
    test_other_roles_lack_pbr_mutation()
    test_material_artist_needs_engine_and_vision()
    # Dispatch
    test_dispatch_map_routes_material_artist_to_self()
    test_existing_routes_unchanged()
    print("All Phase 36 material artist tests passed")


if __name__ == "__main__":
    run_test()
