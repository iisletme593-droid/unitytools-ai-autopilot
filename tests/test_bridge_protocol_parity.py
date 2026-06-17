"""Cycle 99: PROTOCOL PARITY -- the Python bridge client and the C# BridgeServer must agree.

This is the real end-to-end integration guarantee that does NOT need a live Unity: it reads
the C# command vocabulary straight out of unity_plugin/Editor/Bridge/CommandHandlers.cs (the
`case "name": return Handler(p);` dispatch), then drives the actual Python tool/build paths
against a recording bridge and asserts EVERY method Python emits is one the C# side handles.

If a future change makes Python call a method the editor cannot answer (the exact bug that
silently breaks "chat -> game" at runtime), this test goes red in CI -- long before anyone
opens Unity.
"""
import pathlib
import re

import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import BLUEPRINTS

CSHARP = pathlib.Path(__file__).resolve().parents[1] / "unity_plugin" / "Editor" / "Bridge" / "CommandHandlers.cs"


def csharp_command_vocabulary() -> set[str]:
    """The set of RPC methods the C# CommandHandlers dispatch actually handles.

    Matches only real dispatch arms (`case "x": return Handler(...)`), so the category
    fall-through cases elsewhere in the file (case "forest": / "tree": ...) are excluded.
    """
    text = CSHARP.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r'case\s+"([a-z_]+)"\s*:\s*return\s+\w+', text))


class _Recorder:
    def __init__(self):
        self.methods: list[str] = []

    def call(self, method, params=None, timeout=None):
        self.methods.append(method)
        if method == "get_editor_state":
            return {"is_compiling": False}
        if method == "create_primitive":
            return {"name": (params or {}).get("name", "obj")}
        if method == "ping":
            return {"pong": True}
        return {"ok": True}

    def is_connected(self):
        return True

    def ping(self):
        return self.call("ping")


def _emit_methods_for_full_studio(monkeypatch) -> set[str]:
    """Every distinct bridge method the studio emits when it actually BUILDS: every game
    type (execute=True), a composed game, and the bridge-wired scene tools."""
    rec = _Recorder()
    monkeypatch.setattr(ut, "_UNITY", rec)
    for gt in sorted(BLUEPRINTS):
        ut.unity_build_simple_game(execute=True, game_type=gt, collectible_count=4)
    ut.unity_compose_game(enemy=3, collectible=2, hazard=2, moving_hazard=2, spawner=1,
                          guard=1, crate=1, turret=2, goal=True, timer=True, ranged=True, execute=True)
    ut.unity_animate_group(count=4, execute=True)
    # a representative sweep of the scene-editing tools (each is one bridge method)
    ut.unity_get_editor_state()
    ut.unity_get_scene_catalog()
    ut.unity_create_scene_snapshot(label="parity")
    ut.unity_run_visual_qa(capture_screenshot=False)
    ut.unity_set_tag("X", "Player")
    ut.unity_add_collider("X")
    ut.unity_set_rigidbody("X")
    ut.unity_ping()
    return set(rec.methods)


# --- the C# side actually exists and has the game-build vocabulary ----------

def test_csharp_command_handler_exists():
    assert CSHARP.is_file(), f"C# bridge handler missing at {CSHARP}"
    vocab = csharp_command_vocabulary()
    assert len(vocab) >= 30, f"only parsed {len(vocab)} commands -- dispatch format changed?"


def test_game_build_methods_are_all_handled_by_csharp():
    vocab = csharp_command_vocabulary()
    # the exact methods the game-build execute path relies on
    for method in ("create_primitive", "set_tag", "import_asset", "get_editor_state",
                   "add_component", "add_collider", "set_rigidbody", "ping"):
        assert method in vocab, f"C# bridge does not handle '{method}' -- builds would fail live"


# --- the parity guarantee: Python never emits an unhandled method -----------

def test_every_method_the_studio_emits_is_handled_by_csharp(monkeypatch):
    emitted = _emit_methods_for_full_studio(monkeypatch)
    vocab = csharp_command_vocabulary()
    unhandled = sorted(emitted - vocab)
    assert unhandled == [], (
        f"Python emits bridge methods the C# editor does not handle: {unhandled}. "
        "These would fail at runtime against a live Unity.")
    # sanity: the sweep really did exercise the build path
    assert {"create_primitive", "import_asset", "add_component"} <= emitted


def test_place_primitives_is_not_a_bridge_method(monkeypatch):
    # regression guard: unity_place_primitives must LOOP create_primitive (which C# handles),
    # never call a bare "place_primitives" (which C# does NOT handle)
    rec = _Recorder()
    monkeypatch.setattr(ut, "_UNITY", rec)
    ut.unity_place_primitives(type="Sphere", count=5, name_prefix="P")
    assert "place_primitives" not in rec.methods
    assert rec.methods.count("create_primitive") == 5
