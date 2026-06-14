"""P4 robustness: snapshot-before-mutate safety policy + orchestrator hook."""
import unitytools.tools.unity_tools as ut
from unitytools.core.config import Config
from unitytools.core.orchestrator import Orchestrator
from unitytools.core.safety import DESTRUCTIVE_TOOLS, is_destructive, snapshot_label_for


# --- pure policy -----------------------------------------------------------

def test_destructive_detection():
    assert is_destructive("unity_delete_object")
    assert is_destructive("unity_apply_material_palette")
    assert is_destructive("unity_create_optimized_forest_scene")
    assert not is_destructive("unity_get_scene_catalog")
    assert not is_destructive("unity_ping")
    assert not is_destructive("unity_place_primitives")  # additive, not destructive


def test_snapshot_label_is_filesystem_safe():
    assert snapshot_label_for("unity_delete_object") == "auto_before_delete_object"
    label = snapshot_label_for("weird tool!!")
    assert label.startswith("auto_before_")
    assert all(ch.isalnum() or ch == "_" for ch in label)


def test_destructive_set_references_only_real_tools():
    for name in DESTRUCTIVE_TOOLS:
        assert hasattr(ut, name), name


# --- orchestrator hook -----------------------------------------------------

class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        return {"ok": True}


def _orch():
    c = Config()
    c.provider = "cloudflare"
    c.cloudflare_account_id = "acct"
    c.cloudflare_api_token = "tok"
    return Orchestrator(c)


def test_snapshot_taken_before_destructive_tool(monkeypatch):
    o = _orch()
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    o._execute_tool("unity_delete_object", {"name": "Cube"})
    methods = [m for (m, _p) in fb.calls]
    assert "create_scene_snapshot" in methods
    assert "delete_object" in methods
    assert methods.index("create_scene_snapshot") < methods.index("delete_object")


def test_snapshot_taken_only_once_per_turn(monkeypatch):
    o = _orch()
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    o._execute_tool("unity_delete_object", {"name": "A"})
    o._execute_tool("unity_apply_material_palette", {"palette": "forest"})
    methods = [m for (m, _p) in fb.calls]
    assert methods.count("create_scene_snapshot") == 1


def test_no_snapshot_for_readonly_tool(monkeypatch):
    o = _orch()
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    o._execute_tool("unity_get_scene_catalog", {"max_results": 10})
    methods = [m for (m, _p) in fb.calls]
    assert "create_scene_snapshot" not in methods
    assert methods == ["get_scene_catalog"]


def test_snapshot_flag_resets_each_chat(monkeypatch):
    o = _orch()
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    # simulate one turn that snapshotted
    o._snapshot_taken = True
    # a fresh chat() turn must reset the flag so the next turn can snapshot again
    o._select_ollama_tools = lambda msg: []
    o._cloudflare_chat = lambda messages, tools: {"message": {"content": "ok", "tool_calls": []}}
    o.chat("merhaba", max_iterations=1)
    assert o._snapshot_taken is False
