"""P1: unity_setup_studio_lighting wires the lighting rig to the bridge."""
import unitytools.tools.unity_tools as ut
from unitytools.core.lighting import compute_studio_lighting_rig


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"name": params.get("name")}


def test_setup_studio_lighting(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_setup_studio_lighting(distance=6.0, key_intensity=1.3)
    assert r["ok"] is True
    assert set(r["lights"]) == {"key", "fill", "rim"}
    assert [m for (m, _p) in fb.calls] == ["create_light"] * 3
    rig = compute_studio_lighting_rig(distance=6.0, key_intensity=1.3)
    # each call carries the rig's type + intensity
    sent_types = [p["light_type"] for (_m, p) in fb.calls]
    assert sent_types == [s["type"] for s in rig]
    sent_int = [p["intensity"] for (_m, p) in fb.calls]
    assert sent_int == [s["intensity"] for s in rig]


def test_lighting_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_setup_studio_lighting()
    assert r["ok"] is False
    assert "not initialized" in r["error"]
