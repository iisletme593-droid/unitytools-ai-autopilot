"""Cycle 15: gameplay behaviour authoring — the first "scene -> game" step.

unity_add_gameplay_behaviour composes existing Rigidbody/collider tools into a real
physics primitive. Scripted behaviours (rotate/patrol) are honestly reported as
needs_script (a future bridge command), not faked.
"""
import unitytools.tools.unity_tools as ut
from unitytools.core.gameplay import (
    plan_gameplay_behaviour,
    normalize_behaviour,
    prune_redundant_steps,
    GAMEPLAY_BEHAVIOURS,
    NEEDS_SCRIPT,
)


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        return {"ok": True}


# --- pure planning ---------------------------------------------------------

def test_physics_composes_rigidbody_and_collider():
    plan = plan_gameplay_behaviour("physics", "Crate")
    assert plan["ok"] is True
    assert [s["tool"] for s in plan["steps"]] == ["unity_set_rigidbody", "unity_add_collider"]
    assert all(s["kwargs"]["name"] == "Crate" for s in plan["steps"])
    assert plan["steps"][0]["kwargs"]["use_gravity"] is True


def test_static_obstacle_is_collider_only():
    plan = plan_gameplay_behaviour("static_obstacle", "Wall")
    assert [s["tool"] for s in plan["steps"]] == ["unity_add_collider"]


def test_scripted_behaviour_reports_needs_script():
    plan = plan_gameplay_behaviour("rotate", "Cube")
    assert plan["ok"] is False and plan["needs_script"] is True
    assert "patrol" in NEEDS_SCRIPT


def test_unknown_behaviour_lists_available():
    plan = plan_gameplay_behaviour("xyzzy", "Cube")
    assert plan["ok"] is False and "physics" in plan["available"]


def test_aliases_including_turkish():
    assert normalize_behaviour("fizik") == "physics"
    assert normalize_behaviour("don") == "rotate"
    assert plan_gameplay_behaviour("engel", "Wall")["behaviour"] == "static_obstacle"
    assert plan_gameplay_behaviour("platform", "P")["steps"][0]["kwargs"]["is_kinematic"] is True


# --- the tool --------------------------------------------------------------

def test_tool_applies_physics(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_add_gameplay_behaviour("Crate", "physics")
    assert r["ok"] is True
    methods = [m for (m, _p) in fb.calls]
    assert "set_rigidbody" in methods and "add_collider" in methods
    assert r["behaviour"] == "physics"


def test_tool_static_obstacle_only_collider(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_add_gameplay_behaviour("Wall", "static_obstacle")
    methods = [m for (m, _p) in fb.calls]
    assert "add_collider" in methods
    assert "set_rigidbody" not in methods


# --- idempotent collider ---------------------------------------------------

class _CompBridge:
    """Fake bridge reporting a fixed component list for get_object_details."""

    def __init__(self, components):
        self.components = components
        self.calls = []

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        if method == "get_object_details":
            return {"components": list(self.components)}
        return {"ok": True}


def test_prune_drops_collider_when_object_has_one():
    steps = [{"tool": "unity_set_rigidbody", "kwargs": {}}, {"tool": "unity_add_collider", "kwargs": {}}]
    kept, skipped = prune_redundant_steps(steps, ["Transform", "BoxCollider"])
    assert [s["tool"] for s in kept] == ["unity_set_rigidbody"]
    assert len(skipped) == 1


def test_prune_keeps_collider_when_absent():
    steps = [{"tool": "unity_add_collider", "kwargs": {}}]
    kept, skipped = prune_redundant_steps(steps, ["Transform", "MeshRenderer"])
    assert len(kept) == 1 and skipped == []


def test_tool_skips_collider_when_present(monkeypatch):
    fb = _CompBridge(["Transform", "BoxCollider", "MeshRenderer"])
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_add_gameplay_behaviour("Cube", "physics")
    methods = [m for (m, _p) in fb.calls]
    assert "set_rigidbody" in methods
    assert "add_collider" not in methods          # idempotent: already has a collider
    assert any(a.get("skipped") for a in r["applied"])
    assert r["ok"] is True


def test_tool_adds_collider_when_absent(monkeypatch):
    fb = _CompBridge(["Transform", "MeshRenderer"])
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_add_gameplay_behaviour("Empty", "physics")
    assert "add_collider" in [m for (m, _p) in fb.calls]


def test_tool_needs_script_does_not_touch_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_add_gameplay_behaviour("Cube", "patrol")
    assert r["ok"] is False and r.get("needs_script") is True
    assert fb.calls == []


def test_tool_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_add_gameplay_behaviour("Cube", "physics")["ok"] is False


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_add_gameplay_behaviour") is not None
