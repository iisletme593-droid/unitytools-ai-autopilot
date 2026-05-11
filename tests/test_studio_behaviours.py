"""Phase 34 tests: Behaviour library + attach tool wrappers.

The Unity plugin ships 9 runtime MonoBehaviours (Rotator, Bobber,
PulseScale, LookAtCamera, DestroyAfter, FollowTarget,
LoadSceneOnClick, QuitOnClick, KeyboardMover). The bridge has an
attach_behaviour RPC that uses reflection to AddComponent and set
serialized fields by name. We cannot exercise the C# reflection
path from Python tests, so we cover:
- the Python wrapper validates behaviour names against the library
- the wrapper forwards target + behaviour + params block correctly
- the role allowlists (Worker + UI Builder) match
- the C# source files exist and parse as expected
"""
from __future__ import annotations

import re
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
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    LIGHTING_DIRECTOR,
    PHYSICS_QA,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
)
from unitytools.tools.unity_tools import (
    _BEHAVIOUR_LIBRARY,
    unity_attach_behaviour,
    unity_list_attached_behaviours,
    unity_list_behaviour_library,
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
        if method == "attach_behaviour":
            return {
                "ok": True,
                "target": params["target_name"],
                "behaviour": params["behaviour_name"],
                "created": True,
                "applied_fields": list((params.get("params") or {}).keys()),
                "skipped_fields": [],
            }
        if method == "list_behaviour_library":
            return {
                "ok": True,
                "count": 9,
                "library": [
                    {"name": "Rotator", "found": True, "full_type": "UnityTools.Behaviours.Rotator",
                     "fields": [{"name": "axis", "type": "Vector3"}, {"name": "speedDegPerSec", "type": "Single"}]},
                ],
            }
        if method == "list_attached_behaviours":
            return {
                "ok": True,
                "count": 1,
                "attached": [
                    {"game_object": params.get("target_name") or "Cube", "behaviour": "Rotator",
                     "full_type": "UnityTools.Behaviours.Rotator"},
                ],
            }
        raise AssertionError(f"unexpected bridge method: {method}")


# ───────────────────────────────────────────── library presence


def test_behaviour_library_contains_nine_known_behaviours() -> None:
    expected = {
        "Rotator", "Bobber", "PulseScale", "LookAtCamera",
        "DestroyAfter", "FollowTarget", "LoadSceneOnClick",
        "QuitOnClick", "KeyboardMover",
    }
    assert set(_BEHAVIOUR_LIBRARY) == expected
    assert len(_BEHAVIOUR_LIBRARY) == 9
    print("OK Behaviour library exposes 9 known names")


def test_each_behaviour_has_a_corresponding_cs_file() -> None:
    behaviours_dir = _REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours"
    for name in _BEHAVIOUR_LIBRARY:
        path = behaviours_dir / f"{name}.cs"
        assert path.exists(), f"behaviour file missing: {path}"
        body = path.read_text(encoding="utf-8")
        # Must live in the canonical namespace so reflection lookup finds it
        assert "namespace UnityTools.Behaviours" in body, f"{name}.cs has wrong namespace"
        # Must derive from MonoBehaviour
        assert "MonoBehaviour" in body, f"{name}.cs does not extend MonoBehaviour"
        # Must declare the class with the right name
        assert re.search(rf"class\s+{name}\b", body), f"{name}.cs does not declare class {name}"
    print("OK every library name has a matching MonoBehaviour file in unity_plugin/Scripts/Behaviours/")


def test_runtime_scripts_do_not_use_editor_assembly() -> None:
    """Runtime scripts must compile into Assembly-CSharp, not the Editor
    assembly. We guard against accidental `using UnityEditor;` so the
    behaviour library still loads at runtime in built players."""
    behaviours_dir = _REPO_ROOT / "unity_plugin" / "Scripts" / "Behaviours"
    for name in _BEHAVIOUR_LIBRARY:
        body = (behaviours_dir / f"{name}.cs").read_text(encoding="utf-8")
        # QuitOnClick has an `#if UNITY_EDITOR` guarded import — that's OK.
        # Reject only unconditional editor usings.
        unconditional = re.search(r"^using UnityEditor;\s*$", body, re.MULTILINE)
        if unconditional:
            # Allow only inside a UNITY_EDITOR conditional block
            assert "#if UNITY_EDITOR" in body, (
                f"{name}.cs uses UnityEditor unconditionally — breaks runtime builds"
            )
    print("OK no runtime behaviour pulls in UnityEditor unconditionally")


# ───────────────────────────────────────────── wrapper validation


def test_attach_behaviour_rejects_unknown_name() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_attach_behaviour(target_name="X", behaviour_name="Teleporter")
    assert result["ok"] is False
    assert "unknown behaviour" in result["error"]
    assert "Rotator" in result["error"]
    print("OK unknown behaviour name rejected at the wrapper, with help text")


def test_attach_behaviour_requires_target_name() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_attach_behaviour(target_name="", behaviour_name="Rotator")
    assert result["ok"] is False
    assert "target_name" in result["error"]
    print("OK empty target_name rejected")


def test_attach_behaviour_requires_bridge() -> None:
    unity_tools._UNITY = None
    result = unity_attach_behaviour(target_name="X", behaviour_name="Rotator")
    assert result["ok"] is False
    assert "not initialized" in result["error"]
    print("OK missing bridge -> clean error on attach")


def test_attach_behaviour_forwards_params_block() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_attach_behaviour(
        target_name="Coin",
        behaviour_name="Rotator",
        params={"speedDegPerSec": 180, "axis": {"x": 0, "y": 1, "z": 0}},
    )
    assert result["ok"] is True
    assert result["behaviour"] == "Rotator"
    method, sent = fake.calls[0]
    assert method == "attach_behaviour"
    assert sent["target_name"] == "Coin"
    assert sent["behaviour_name"] == "Rotator"
    assert sent["params"]["speedDegPerSec"] == 180
    assert sent["params"]["axis"] == {"x": 0, "y": 1, "z": 0}
    print("OK wrapper forwards full param block (scalar + Vector3 dict)")


def test_attach_behaviour_handles_no_params() -> None:
    """Some behaviours (LookAtCamera with defaults) need no params."""
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_attach_behaviour(target_name="Label", behaviour_name="LookAtCamera")
    assert result["ok"] is True
    _, sent = fake.calls[0]
    assert sent["params"] == {}
    print("OK params omitted -> empty dict sent")


def test_attach_behaviour_surfaces_bridge_exception() -> None:
    unity_tools._UNITY = FakeUnity(raise_on_method="attach_behaviour")
    result = unity_attach_behaviour(target_name="X", behaviour_name="Bobber")
    assert result["ok"] is False
    assert "simulated failure" in result["error"]
    print("OK bridge exception surfaces clean error")


def test_list_behaviour_library_returns_inventory() -> None:
    unity_tools._UNITY = FakeUnity()
    result = unity_list_behaviour_library()
    assert result["ok"] is True
    assert result["count"] == 9
    assert any(row["name"] == "Rotator" for row in result["library"])
    print("OK unity_list_behaviour_library returns inventory")


def test_list_attached_behaviours_scopes_to_target() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_list_attached_behaviours(target_name="Coin")
    assert result["ok"] is True
    _, sent = fake.calls[0]
    assert sent["target_name"] == "Coin"
    print("OK list_attached_behaviours forwards target_name scope")


def test_list_attached_behaviours_scans_whole_scene() -> None:
    fake = FakeUnity()
    unity_tools._UNITY = fake
    result = unity_list_attached_behaviours()
    assert result["ok"] is True
    _, sent = fake.calls[0]
    assert sent["target_name"] == ""
    print("OK list_attached_behaviours defaults to whole-scene scan")


# ───────────────────────────────────────────── role allowlist


def test_worker_owns_behaviour_attach_tools() -> None:
    """Worker is the role that places objects, so it owns 'make this
    object do something' too."""
    assert "unity_attach_behaviour" in WORKER.tool_set
    assert "unity_list_behaviour_library" in WORKER.tool_set
    assert "unity_list_attached_behaviours" in WORKER.tool_set
    print("OK Worker allowlist gets the attach + list behaviour tools")


def test_ui_builder_can_wire_buttons_to_behaviours() -> None:
    """UI Builder needs LoadSceneOnClick / QuitOnClick on buttons. It
    has the attach + list-library tools (not the list-attached one —
    that's a scene-wide inspection more suited to Worker)."""
    assert "unity_attach_behaviour" in UI_BUILDER.tool_set
    assert "unity_list_behaviour_library" in UI_BUILDER.tool_set
    print("OK UI Builder allowlist gets attach + list-library for button wiring")


def test_non_executor_roles_lack_behaviour_attach() -> None:
    """Director / reviewer / engineer roles plan and audit; they do
    not directly attach behaviours."""
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR,
                  BUILD_ENGINEER):
        assert "unity_attach_behaviour" not in role.tool_set, (
            f"{role.id} must not attach behaviours — that's Worker + UI Builder"
        )
    print("OK only Worker + UI Builder can attach behaviours")


def run_test() -> None:
    # Library presence
    test_behaviour_library_contains_nine_known_behaviours()
    test_each_behaviour_has_a_corresponding_cs_file()
    test_runtime_scripts_do_not_use_editor_assembly()
    # Wrappers
    test_attach_behaviour_rejects_unknown_name()
    test_attach_behaviour_requires_target_name()
    test_attach_behaviour_requires_bridge()
    test_attach_behaviour_forwards_params_block()
    test_attach_behaviour_handles_no_params()
    test_attach_behaviour_surfaces_bridge_exception()
    test_list_behaviour_library_returns_inventory()
    test_list_attached_behaviours_scopes_to_target()
    test_list_attached_behaviours_scans_whole_scene()
    # Role surface
    test_worker_owns_behaviour_attach_tools()
    test_ui_builder_can_wire_buttons_to_behaviours()
    test_non_executor_roles_lack_behaviour_attach()
    print("All Phase 34 behaviour-library tests passed")


if __name__ == "__main__":
    run_test()
