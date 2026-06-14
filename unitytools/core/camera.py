"""Camera framing helpers (pure math) for presentable shots."""
from __future__ import annotations

import math
from typing import Tuple

Vec3 = Tuple[float, float, float]


def frame_camera_pose(
    target: Vec3 = (0.0, 0.0, 0.0),
    distance: float = 10.0,
    yaw_deg: float = 30.0,
    pitch_deg: float = 20.0,
) -> Tuple[Vec3, Vec3]:
    """Return (position, euler_rotation_deg) for a camera orbiting `target`.

    The camera sits `distance` away at azimuth `yaw_deg` / elevation `pitch_deg`
    and looks back at the target. yaw=0,pitch=0 -> camera on -Z looking +Z.
    Positive Unity pitch (X) looks downward.
    """
    tx, ty, tz = target
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    # direction from target to camera
    dx = math.sin(yaw) * math.cos(pitch)
    dy = math.sin(pitch)
    dz = -math.cos(yaw) * math.cos(pitch)
    pos = (tx + distance * dx, ty + distance * dy, tz + distance * dz)
    # look-at rotation (camera -> target)
    fx, fy, fz = (tx - pos[0], ty - pos[1], tz - pos[2])
    flen = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx, fy, fz = fx / flen, fy / flen, fz / flen
    yaw_rot = math.degrees(math.atan2(fx, fz))
    pitch_rot = math.degrees(-math.asin(max(-1.0, min(1.0, fy))))
    return pos, (round(pitch_rot, 4), round(yaw_rot, 4), 0.0)
