"""P7 (cycle 17, STEP A): MonoBehaviour script generation for scripted behaviours.

Pure, deterministic C# source for rotate/spin/move (the script-driven behaviours
that physics composition can't do). unity_add_script_behaviour returns the source;
auto_import (opt-in) imports it so Unity compiles it. Default is generate-only
(safe — no recompile triggered).
"""
import unitytools.tools.unity_tools as ut
from unitytools.core.gameplay import generate_behaviour_script, plan_gameplay_behaviour


# --- pure generator --------------------------------------------------------

def test_rotator_source():
    s = generate_behaviour_script("rotate")
    assert s["ok"] is True
    assert s["class_name"] == "AutopilotRotator"
    assert s["filename"] == "Assets/AutopilotScripts/AutopilotRotator.cs"
    src = s["source"]
    assert "MonoBehaviour" in src
    assert "transform.Rotate" in src
    assert "Time.deltaTime" in src
    assert src.count("{") == src.count("}")   # balanced braces (compilable shape)


def test_mover_source_and_custom_speed():
    s = generate_behaviour_script("move", speed=5.0)
    assert s["class_name"] == "AutopilotMover"
    assert "transform.Translate" in s["source"]
    assert "5.0f" in s["source"]


def test_aliases_and_unknown():
    assert generate_behaviour_script("spin")["class_name"] == "AutopilotRotator"
    bad = generate_behaviour_script("teleport")
    assert bad["ok"] is False and "available" in bad


def test_plan_needs_script_now_carries_source():
    plan = plan_gameplay_behaviour("rotate", "Coin")
    assert plan["ok"] is False and plan["needs_script"] is True
    assert "transform.Rotate" in plan["script"]["source"]
    assert plan["script"]["class_name"] == "AutopilotRotator"


# --- tool ------------------------------------------------------------------

def test_tool_generate_only_no_bridge_needed(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_add_script_behaviour("Coin", "rotate")  # auto_import defaults False
    assert r["ok"] is True
    assert r["imported"] is False
    assert "transform.Rotate" in r["source"]
    assert "AutopilotRotator" in r["next_step"]


class _ImpBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        return {"ok": True}


def test_tool_auto_import_writes_and_imports(monkeypatch):
    fb = _ImpBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_add_script_behaviour("Coin", "rotate", auto_import=True)
    assert r["ok"] is True and r["imported"] is True
    imports = [p for (m, p) in fb.calls if m == "import_asset"]
    assert imports and imports[0]["dst_relative"].endswith("AutopilotRotator.cs")


def test_tool_unknown_behaviour(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_add_script_behaviour("Coin", "teleport")["ok"] is False


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_add_script_behaviour") is not None
