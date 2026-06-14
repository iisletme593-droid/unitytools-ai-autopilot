"""P2: color resolution (name/hex/rgb) + unity_set_object_color tool."""
import unitytools.tools.unity_tools as ut
from unitytools.core.palette import resolve_color


def test_named_colors_en_and_tr():
    assert resolve_color("red") == (1.0, 0.0, 0.0)
    assert resolve_color("kirmizi") == (1.0, 0.0, 0.0)
    assert resolve_color("MAVI") == resolve_color("blue")  # case-insensitive + tr alias


def test_hex():
    assert resolve_color("#ff0000") == (1.0, 0.0, 0.0)
    r, g, b = resolve_color("#00ff00")
    assert (round(r), round(g), round(b)) == (0, 1, 0)
    # short hex
    assert resolve_color("#fff") == (1.0, 1.0, 1.0)


def test_rgb_0_255_normalized():
    assert resolve_color("255,0,0") == (1.0, 0.0, 0.0)
    assert resolve_color((0, 128, 255)) == (0.0, 128 / 255.0, 1.0)


def test_unknown_falls_back():
    assert resolve_color("not-a-color") == (0.8, 0.8, 0.8)
    assert resolve_color("#zzz") == (0.8, 0.8, 0.8)


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"ok": True}


def test_set_object_color_tool(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_set_object_color(name="Cube", color="kirmizi")
    assert r["ok"] is True
    m, p = fb.calls[0]
    assert m == "set_material_color"
    assert (p["r"], p["g"], p["b"]) == (1.0, 0.0, 0.0)
    assert p["name"] == "Cube"


def test_set_object_color_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_set_object_color("Cube", "red")["ok"] is False
