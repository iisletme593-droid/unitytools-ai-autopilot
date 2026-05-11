"""Phase 31 tests: UI Builder role + UI bridge tool wrappers.

Covers: canvas / text / button wrapper happy paths and validation,
role allowlist (UI Builder owns UI tools, no 3D placement, no lights
/ camera / particles), dispatch routing.
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
    AUDIO_DIRECTOR,
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
)


class FakeUnity:
    """Records create_ui_* + list_ui_elements calls; returns canned payloads."""

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
        if method == "create_ui_canvas":
            return {"ok": True, "name": params["name"], "created": True, "instance_id": 42}
        if method == "create_ui_text":
            return {
                "ok": True,
                "name": params["name"],
                "canvas": params.get("canvas_name") or "UICanvas",
                "text": params["text"],
                "font_size": params["font_size"],
            }
        if method == "create_ui_button":
            return {
                "ok": True,
                "name": params["name"],
                "canvas": params.get("canvas_name") or "UICanvas",
                "label": params["label"],
            }
        if method == "list_ui_elements":
            return {
                "ok": True,
                "canvas_count": 1,
                "total_texts": 2,
                "total_buttons": 1,
                "has_event_system": True,
                "canvases": [{"name": "UICanvas", "text_count": 2, "button_count": 1}],
            }
        raise AssertionError(f"unexpected bridge method: {method}")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="ui-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── canvas / text / button


def test_create_ui_canvas_happy_path() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_tools.unity_create_ui_canvas(name="TitleCanvas")
    assert result["ok"] is True
    assert result["name"] == "TitleCanvas"
    assert result["created"] is True
    method, params = fake.calls[0]
    assert method == "create_ui_canvas"
    assert params == {"name": "TitleCanvas"}
    print("OK unity_create_ui_canvas forwards name to bridge")


def test_create_ui_canvas_requires_name() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_tools.unity_create_ui_canvas(name="")
    assert result["ok"] is False
    assert "name is required" in result["error"]
    print("OK empty canvas name rejected")


def test_create_ui_canvas_requires_bridge() -> None:
    unity_tools._UNITY = None
    result = unity_tools.unity_create_ui_canvas(name="X")
    assert result["ok"] is False
    assert "not initialized" in result["error"]
    print("OK missing bridge -> clean error on canvas")


def test_create_ui_text_full_param_forwarding() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_tools.unity_create_ui_text(
        canvas_name="TitleCanvas",
        name="TitleText",
        text="PROJECT XENON",
        position_x=0.0, position_y=200.0,
        width=600, height=120,
        font_size=72,
        r=0.9, g=0.85, b=0.7, a=1.0,
    )
    assert result["ok"] is True
    method, params = fake.calls[0]
    assert method == "create_ui_text"
    assert params["canvas_name"] == "TitleCanvas"
    assert params["text"] == "PROJECT XENON"
    assert params["font_size"] == 72
    assert params["color"] == {"r": 0.9, "g": 0.85, "b": 0.7, "a": 1.0}
    print("OK unity_create_ui_text forwards full param block (text, position, font, color)")


def test_create_ui_button_full_param_forwarding() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_tools.unity_create_ui_button(
        canvas_name="TitleCanvas",
        name="StartBtn",
        label="START",
        position_x=0.0, position_y=-200.0,
        width=240, height=80,
        font_size=32,
        bg_r=0.15, bg_g=0.18, bg_b=0.25,
        label_r=0.95, label_g=0.92, label_b=0.85,
    )
    assert result["ok"] is True
    _, params = fake.calls[0]
    assert params["label"] == "START"
    assert params["width"] == 240
    assert params["background_color"]["r"] == 0.15
    assert params["label_color"]["r"] == 0.95
    print("OK unity_create_ui_button forwards label, size, bg + label colors")


def test_list_ui_elements_returns_inventory() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_tools.unity_list_ui_elements()
    assert result["ok"] is True
    assert result["canvas_count"] == 1
    assert result["total_texts"] == 2
    assert result["total_buttons"] == 1
    assert result["has_event_system"] is True
    print("OK unity_list_ui_elements returns canvas + element inventory")


def test_create_ui_text_surfaces_bridge_failure() -> None:
    unity_tools._UNITY = FakeUnity(raise_on_method="create_ui_text")
    result = unity_tools.unity_create_ui_text(name="X", text="x")
    assert result["ok"] is False
    assert "simulated failure" in result["error"]
    print("OK bridge exception on create_ui_text surfaces clean error")


# ───────────────────────────────────────────── role allowlist


def test_ui_builder_owns_ui_tools() -> None:
    assert "unity_create_ui_canvas" in UI_BUILDER.tool_set
    assert "unity_create_ui_text" in UI_BUILDER.tool_set
    assert "unity_create_ui_button" in UI_BUILDER.tool_set
    assert "unity_list_ui_elements" in UI_BUILDER.tool_set
    # Snapshot + capture + save + lifecycle
    assert "unity_create_scene_snapshot" in UI_BUILDER.tool_set
    assert "studio_capture_screenshot" in UI_BUILDER.tool_set
    assert "unity_save_scene" in UI_BUILDER.tool_set
    assert "studio_update_task_status" in UI_BUILDER.tool_set
    # Reads Art Bible but does NOT write
    assert "studio_read_art_bible" in UI_BUILDER.tool_set
    assert "studio_write_art_bible" not in UI_BUILDER.tool_set
    # Cannot edit GDD
    assert "studio_write_gdd" not in UI_BUILDER.tool_set
    # Cannot place 3D objects
    assert "unity_create_primitive" not in UI_BUILDER.tool_set
    assert "unity_set_position" not in UI_BUILDER.tool_set
    # Cannot touch lights / camera / particles
    assert "unity_set_light_properties" not in UI_BUILDER.tool_set
    assert "unity_frame_object" not in UI_BUILDER.tool_set
    assert "unity_add_particle_system" not in UI_BUILDER.tool_set
    print("OK UI Builder allowlist: UI tools only, no 3D / lights / camera / particles / doc writes")


def test_other_roles_lack_ui_tools() -> None:
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR):
        assert "unity_create_ui_canvas" not in role.tool_set, (
            f"{role.id} must not create UI canvases — that's UI Builder's job"
        )
        assert "unity_create_ui_button" not in role.tool_set, (
            f"{role.id} must not create UI buttons"
        )
    print("OK only UI Builder can create UI elements")


def test_ui_builder_needs_engine_no_vision() -> None:
    assert UI_BUILDER.needs_engine is True
    assert UI_BUILDER.needs_vision is False
    print("OK UI Builder needs engine, not vision")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_ui_builder_to_self() -> None:
    assert DISPATCH_MAP["ui_builder"] == "ui_builder"
    print("OK DISPATCH_MAP[ui_builder] -> ui_builder")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["lighting_director"] == "lighting_director"
    assert DISPATCH_MAP["camera_director"] == "camera_director"
    assert DISPATCH_MAP["vfx_director"] == "vfx_director"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after ui_builder addition")


def run_test() -> None:
    # Bridge wrappers
    test_create_ui_canvas_happy_path()
    test_create_ui_canvas_requires_name()
    test_create_ui_canvas_requires_bridge()
    test_create_ui_text_full_param_forwarding()
    test_create_ui_button_full_param_forwarding()
    test_list_ui_elements_returns_inventory()
    test_create_ui_text_surfaces_bridge_failure()
    # Role allowlist
    test_ui_builder_owns_ui_tools()
    test_other_roles_lack_ui_tools()
    test_ui_builder_needs_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_ui_builder_to_self()
    test_existing_routes_unchanged()
    print("All Phase 31 UI Builder tests passed")


if __name__ == "__main__":
    run_test()
