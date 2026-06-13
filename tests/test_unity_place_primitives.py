"""P1: unity_place_primitives tool wires the layout math to the bridge."""
import unitytools.tools.unity_tools as ut
from unitytools.core.layout import compute_layout_positions


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"name": params.get("name")}


def test_place_primitives_grid(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_place_primitives(type="Cube", count=4, pattern="grid", spacing=1.0)
    assert r["ok"] is True
    assert r["created_count"] == 4
    assert [m for (m, _p) in fb.calls] == ["create_primitive"] * 4
    expected = compute_layout_positions(4, "grid", spacing=1.0)
    got = [(p["position"]["x"], p["position"]["y"], p["position"]["z"]) for (_m, p) in fb.calls]
    assert got == expected


def test_place_primitives_count_safety_cap(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_place_primitives(type="Cube", count=100000)
    assert r["created_count"] == 500  # capped so the autopilot can't flood the scene


def test_place_primitives_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_place_primitives(type="Cube", count=3)
    assert r["ok"] is False
    assert "not initialized" in r["error"]
