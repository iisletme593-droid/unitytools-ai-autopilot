"""Phase 37 tests: Marketing Director role + press kit + asset manifest.

Covers: press_kit path + template, read/write round-trip, asset
manifest scan, player_settings wrapper validation (bundle_id
reverse-DNS check), role allowlist (Marketing Director owns press
kit + metadata + screenshots, NOT GDD / scene mutation), dispatch
routing.
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
    MARKETING_DIRECTOR,
    MATERIAL_ARTIST,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
)
from unitytools.studio.templates import starter_files
from unitytools.studio.tools import (
    studio_asset_manifest,
    studio_read_press_kit,
    studio_write_press_kit,
)
from unitytools.tools.unity_tools import (
    unity_get_player_settings,
    unity_set_player_settings,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="marketing-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


class FakeUnity:
    def __init__(self, connected: bool = True):
        self._connected = connected
        self.calls: list[tuple[str, dict]] = []
        self._settings = {
            "product_name": "Untitled Project",
            "company_name": "DefaultCompany",
            "version": "0.1",
            "bundle_id": "com.DefaultCompany.UntitledProject",
            "default_width": 1920,
            "default_height": 1080,
        }

    def is_connected(self):
        return self._connected

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, dict(params or {})))
        if method == "set_player_settings":
            for k, v in (params or {}).items():
                if k in self._settings:
                    self._settings[k] = v
            return {"ok": True, **self._settings}
        if method == "get_player_settings":
            return {
                "ok": True,
                **self._settings,
                "active_build_target": "StandaloneWindows64",
                "unity_version": "2022.3.0f1",
            }
        raise AssertionError(f"unexpected bridge method: {method}")


# ───────────────────────────────────────────── paths + templates


def test_paths_expose_press_kit() -> None:
    state, _ = _fresh_studio()
    assert state.paths.press_kit.name == "press_kit.md"
    assert state.paths.press_kit.parent == state.paths.root
    print("OK StudioPaths.press_kit -> studio/press_kit.md")


def test_starter_files_include_press_kit_template() -> None:
    files = starter_files()
    assert "press_kit.md" in files
    body = files["press_kit.md"]
    # Canonical sections
    for section in ("Game Title", "Tagline", "Description", "Features", "Hero Shots", "Credits"):
        assert section in body, f"press_kit template missing section: {section}"
    print("OK starter_files() includes press_kit.md with canonical sections")


# ───────────────────────────────────────────── doc r/w round-trip


def test_read_press_kit_returns_empty_when_absent() -> None:
    state, _ = _fresh_studio()
    result = studio_read_press_kit()
    assert result["ok"] is True
    assert result["content"] == ""
    print("OK read_press_kit: empty when file absent")


def test_write_then_read_press_kit_round_trip() -> None:
    state, _ = _fresh_studio()
    body = "# Press Kit\n\n## Game Title\nProject Xenon\n\n## Tagline\nA neon-soaked roguelite.\n"
    write_result = studio_write_press_kit(content=body)
    assert write_result["ok"] is True
    assert write_result["path"] == str(state.paths.press_kit)
    assert state.paths.press_kit.exists()

    read_result = studio_read_press_kit()
    assert "Project Xenon" in read_result["content"]
    assert "neon-soaked" in read_result["content"]
    print("OK press kit write then read round-trips")


# ───────────────────────────────────────────── asset manifest


def test_asset_manifest_empty_studio_returns_zero_counts() -> None:
    state, _ = _fresh_studio()
    result = studio_asset_manifest()
    assert result["ok"] is True
    assert result["references"]["count"] == 0
    assert result["screenshots"]["count"] == 0
    assert result["builds"]["count"] == 0
    print("OK asset_manifest on empty studio reports zero counts")


def test_asset_manifest_counts_and_lists_real_files() -> None:
    state, tmp = _fresh_studio()
    # Seed a couple of files in each bucket
    (state.paths.refs / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (state.paths.refs / "moodboard.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
    audio_refs = state.paths.refs / "audio"
    audio_refs.mkdir(exist_ok=True)
    (audio_refs / "theme.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 80)
    state.paths.qa_screenshots.mkdir(parents=True, exist_ok=True)
    (state.paths.qa_screenshots / "shot1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
    gen = state.paths.root / "assets" / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "rock_01.fbx").write_bytes(b"FBX-fake" + b"\x00" * 1500)
    builds = state.paths.root / "builds"
    builds.mkdir(parents=True, exist_ok=True)
    (builds / "Game.exe").write_bytes(b"MZ" + b"\x00" * 10_000)

    result = studio_asset_manifest()
    assert result["references"]["count"] == 2
    assert result["audio_references"]["count"] == 1
    assert result["screenshots"]["count"] == 1
    assert result["generated_assets"]["count"] == 1
    assert result["builds"]["count"] == 1
    # Totals add up
    assert result["builds"]["total_bytes"] >= 10_000
    # Newest list capped at 10
    assert len(result["references"]["newest"]) == 2
    print("OK asset_manifest counts + sizes seeded files across all 5 buckets")


def test_asset_manifest_skips_non_matching_extensions() -> None:
    """A stray .txt in refs/ shouldn't appear in the images bucket."""
    state, _ = _fresh_studio()
    (state.paths.refs / "notes.txt").write_text("ignore me", encoding="utf-8")
    result = studio_asset_manifest()
    assert result["references"]["count"] == 0
    print("OK asset_manifest filters by extension (no .txt in image bucket)")


# ───────────────────────────────────────────── player settings


def test_set_player_settings_forwards_basic_fields() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_set_player_settings(
        product_name="Project Xenon",
        company_name="Wizardly Studio",
        version="0.4.2",
        bundle_id="com.wizardly.xenon",
    )
    assert result["ok"] is True
    method, params = fake.calls[0]
    assert method == "set_player_settings"
    assert params["product_name"] == "Project Xenon"
    assert params["bundle_id"] == "com.wizardly.xenon"
    print("OK set_player_settings forwards full metadata")


def test_set_player_settings_rejects_non_reverse_dns_bundle_id() -> None:
    """bundle_id 'MyGame' is invalid; should be 'com.studio.mygame'."""
    unity_tools._UNITY = FakeUnity()
    result = unity_set_player_settings(bundle_id="MyGame")
    assert result["ok"] is False
    assert "reverse-DNS" in result["error"]
    print("OK non-reverse-DNS bundle_id rejected")


def test_set_player_settings_requires_at_least_one_field() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_set_player_settings()
    assert result["ok"] is False
    assert "at least one" in result["error"]
    print("OK empty set_player_settings call rejected")


def test_set_player_settings_omits_empty_fields() -> None:
    """Partial update: only product_name -> only that one goes."""
    fake = FakeUnity()
    unity_tools._UNITY = fake
    unity_set_player_settings(product_name="Xenon")
    _, params = fake.calls[0]
    assert "product_name" in params
    assert "company_name" not in params
    assert "version" not in params
    assert "bundle_id" not in params
    print("OK only-populated fields forwarded")


def test_get_player_settings_round_trip() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_get_player_settings()
    assert result["ok"] is True
    assert "product_name" in result
    assert "bundle_id" in result
    assert "active_build_target" in result
    print("OK get_player_settings returns full state")


def test_set_player_settings_requires_bridge() -> None:
    unity_tools._UNITY = None
    result = unity_set_player_settings(product_name="X")
    assert result["ok"] is False
    assert "not initialized" in result["error"]
    print("OK missing bridge -> clean error on set_player_settings")


# ───────────────────────────────────────────── role allowlist


def test_marketing_director_owns_marketing_tools() -> None:
    assert "studio_read_press_kit" in MARKETING_DIRECTOR.tool_set
    assert "studio_write_press_kit" in MARKETING_DIRECTOR.tool_set
    assert "studio_asset_manifest" in MARKETING_DIRECTOR.tool_set
    assert "unity_get_player_settings" in MARKETING_DIRECTOR.tool_set
    assert "unity_set_player_settings" in MARKETING_DIRECTOR.tool_set
    assert "studio_capture_screenshot" in MARKETING_DIRECTOR.tool_set
    assert "studio_list_screenshots" in MARKETING_DIRECTOR.tool_set
    # Reads GDD for pitch context, does NOT write it
    assert "studio_read_gdd" in MARKETING_DIRECTOR.tool_set
    assert "studio_write_gdd" not in MARKETING_DIRECTOR.tool_set
    # Cannot write Art Bible / Audio Brief / Sprint
    assert "studio_write_art_bible" not in MARKETING_DIRECTOR.tool_set
    assert "studio_write_audio_brief" not in MARKETING_DIRECTOR.tool_set
    # Cannot build (Build Engineer's job)
    assert "unity_build_player" not in MARKETING_DIRECTOR.tool_set
    assert "studio_build_check" not in MARKETING_DIRECTOR.tool_set
    # Cannot mutate scene
    assert "unity_create_primitive" not in MARKETING_DIRECTOR.tool_set
    assert "unity_set_light_properties" not in MARKETING_DIRECTOR.tool_set
    assert "unity_set_skybox" not in MARKETING_DIRECTOR.tool_set
    assert "unity_set_material_pbr" not in MARKETING_DIRECTOR.tool_set
    # Lifecycle + escalation
    assert "studio_update_task_status" in MARKETING_DIRECTOR.tool_set
    assert "studio_add_task" in MARKETING_DIRECTOR.tool_set
    print("OK Marketing Director allowlist: press kit + PlayerSettings + screenshots, no docs / build / scene mutation")


def test_other_roles_lack_press_kit_write() -> None:
    """Only Marketing Director writes the press kit."""
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR, UI_BUILDER,
                  BUILD_ENGINEER, ATMOSPHERE_DIRECTOR, MATERIAL_ARTIST):
        assert "studio_write_press_kit" not in role.tool_set, (
            f"{role.id} must not write the press kit"
        )
        assert "unity_set_player_settings" not in role.tool_set, (
            f"{role.id} must not change PlayerSettings"
        )
    print("OK only Marketing Director writes press kit / mutates PlayerSettings")


def test_marketing_director_needs_engine_no_vision() -> None:
    assert MARKETING_DIRECTOR.needs_engine is True
    assert MARKETING_DIRECTOR.needs_vision is False
    print("OK Marketing Director needs engine, not vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_marketing_director_to_self() -> None:
    assert DISPATCH_MAP["marketing_director"] == "marketing_director"
    print("OK DISPATCH_MAP[marketing_director] -> marketing_director")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["build_engineer"] == "build_engineer"
    assert DISPATCH_MAP["atmosphere_director"] == "atmosphere_director"
    assert DISPATCH_MAP["material_artist"] == "material_artist"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after marketing_director addition")


def run_test() -> None:
    # Paths + templates
    test_paths_expose_press_kit()
    test_starter_files_include_press_kit_template()
    # Doc r/w
    test_read_press_kit_returns_empty_when_absent()
    test_write_then_read_press_kit_round_trip()
    # Asset manifest
    test_asset_manifest_empty_studio_returns_zero_counts()
    test_asset_manifest_counts_and_lists_real_files()
    test_asset_manifest_skips_non_matching_extensions()
    # PlayerSettings
    test_set_player_settings_forwards_basic_fields()
    test_set_player_settings_rejects_non_reverse_dns_bundle_id()
    test_set_player_settings_requires_at_least_one_field()
    test_set_player_settings_omits_empty_fields()
    test_get_player_settings_round_trip()
    test_set_player_settings_requires_bridge()
    # Role
    test_marketing_director_owns_marketing_tools()
    test_other_roles_lack_press_kit_write()
    test_marketing_director_needs_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_marketing_director_to_self()
    test_existing_routes_unchanged()
    print("All Phase 37 marketing director tests passed")


if __name__ == "__main__":
    run_test()
