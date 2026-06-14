"""P1: camera framing math + unity_frame_camera tool."""
import math

import unitytools.tools.unity_tools as ut
from unitytools.core.camera import frame_camera_pose


def test_default_axis_pose():
    pos, rot = frame_camera_pose(target=(0.0, 0.0, 0.0), distance=10.0, yaw_deg=0.0, pitch_deg=0.0)
    assert pos == (0.0, 0.0, -10.0)
    assert rot == (0.0, 0.0, 0.0)


def test_pose_distance_from_target():
    pos, _rot = frame_camera_pose(target=(0.0, 0.0, 0.0), distance=7.5, yaw_deg=40.0, pitch_deg=25.0)
    assert abs(math.sqrt(sum(c * c for c in pos)) - 7.5) < 1e-6


def test_pitch_elevates_and_looks_down():
    pos, rot = frame_camera_pose(distance=10.0, yaw_deg=0.0, pitch_deg=20.0)
    assert pos[1] > 0.0  # camera elevated
    assert rot[0] > 0.0  # positive Unity pitch looks down


def test_target_offset_applied():
    pos, _rot = frame_camera_pose(target=(5.0, 1.0, -2.0), distance=10.0, yaw_deg=0.0, pitch_deg=0.0)
    assert pos == (5.0, 1.0, -12.0)


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"ok": True}


def test_frame_camera_tool(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_frame_camera(distance=10.0, yaw_deg=0.0, pitch_deg=0.0, fov=55.0)
    assert r["ok"] is True
    methods = [m for (m, _p) in fb.calls]
    assert methods == ["set_transform", "set_transform", "set_camera"]
    # position call carries the framed position
    assert fb.calls[0][1]["position"] == {"x": 0.0, "y": 0.0, "z": -10.0}
    assert fb.calls[2][1]["fov"] == 55.0


def test_frame_camera_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_frame_camera()
    assert r["ok"] is False
