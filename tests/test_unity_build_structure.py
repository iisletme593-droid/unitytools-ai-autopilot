"""P1: unity_build_structure tool wires structure math to the bridge."""
import unitytools.tools.unity_tools as ut
from unitytools.core.layout import compute_structure_positions


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"name": params.get("name")}


def test_build_wall(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_build_structure(kind="wall", width=5, height=3, spacing=1.0)
    assert r["ok"] is True
    assert r["created_count"] == 15  # 5 x 3
    expected = compute_structure_positions("wall", width=5, height=3, spacing=1.0)
    got = [(p["position"]["x"], p["position"]["y"], p["position"]["z"]) for (_m, p) in fb.calls]
    assert got == expected


def test_build_structure_safety_cap(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_build_structure(kind="floor", width=40, depth=40)  # 1600 -> capped
    assert r["created_count"] == 500


def test_build_structure_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_build_structure(kind="tower", height=4)
    assert r["ok"] is False
    assert "not initialized" in r["error"]
