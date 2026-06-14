"""P1 capstone: unity_blockout_scene composes the place/build/light/frame tools."""
import unitytools.tools.unity_tools as ut


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"ok": True}


def _counts(calls):
    out = {}
    for m, _p in calls:
        out[m] = out.get(m, 0) + 1
    return out


def test_blockout_full(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_blockout_scene(floor_size=4, prop_count=3, add_lighting=True, frame_camera=True)
    assert r["ok"] is True
    assert r["steps"]["floor"] == 16  # 4 x 4
    assert r["steps"]["props"] == 3
    assert r["steps"]["lights"] == 3  # key/fill/rim
    assert r["steps"]["camera"] is True
    c = _counts(fb.calls)
    assert c["create_primitive"] == 16 + 3
    assert c["create_light"] == 3
    assert c["set_transform"] == 2  # camera position + rotation


def test_blockout_minimal(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_blockout_scene(floor_size=2, prop_count=0, add_lighting=False, frame_camera=False)
    assert r["steps"]["lights"] == 0
    assert r["steps"]["camera"] is False
    assert r["steps"]["props"] == 0


def test_blockout_floor_cap(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_blockout_scene(floor_size=100, prop_count=0, add_lighting=False, frame_camera=False)
    assert r["steps"]["floor"] == 17 * 17  # capped at 17x17


def test_blockout_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_blockout_scene()["ok"] is False
