"""P2: themed color palettes + unity_color_group tool."""
import unitytools.tools.unity_tools as ut
from unitytools.core.palette import theme_palette


def test_theme_palette_returns_valid_rgb():
    for theme in ("fantasy", "nature", "warm", "cool", "mono"):
        pal = theme_palette(theme)
        assert len(pal) == 5
        for r, g, b in pal:
            assert 0.0 <= r <= 1.0 and 0.0 <= g <= 1.0 and 0.0 <= b <= 1.0


def test_unknown_theme_falls_back_to_fantasy():
    assert theme_palette("bogus") == theme_palette("fantasy")


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"ok": True}


def test_color_group_cycles_palette(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_color_group(name_prefix="Prop", count=7, theme="warm")
    assert r["ok"] is True
    assert r["colored_count"] == 7
    assert [m for (m, _p) in fb.calls] == ["set_material_color"] * 7
    # cycles: object 0 and object 5 (len-5 palette) share the same color
    pal = theme_palette("warm")
    assert (fb.calls[0][1]["r"], fb.calls[0][1]["g"], fb.calls[0][1]["b"]) == pal[0]
    assert (fb.calls[5][1]["r"], fb.calls[5][1]["g"], fb.calls[5][1]["b"]) == pal[0]


def test_color_group_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_color_group("Prop", 3)["ok"] is False
