"""Lighting presets for the autopilot (presentable scenes). Pure math, no bridge."""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

Vec3 = Tuple[float, float, float]


def compute_studio_lighting_rig(
    target: Vec3 = (0.0, 0.0, 0.0),
    distance: float = 6.0,
    key_intensity: float = 1.3,
) -> List[Dict]:
    """Classic 3-point lighting (key / fill / rim) arranged around `target`.

    Returns one spec dict per light: role, type, position, look_at, intensity.
    Key is brightest; fill softens shadows (~40% of key); rim backlights (~70%).
    All positions sit at `distance` (scaled) from the target with some height.
    """
    tx, ty, tz = target
    height = distance * 0.6

    def at(angle_deg: float, dist: float, h: float) -> Vec3:
        a = math.radians(angle_deg)
        return (tx + dist * math.cos(a), ty + h, tz + dist * math.sin(a))

    return [
        {
            "role": "key",
            "type": "Directional",
            "position": at(45.0, distance, height),
            "look_at": target,
            "intensity": round(key_intensity, 3),
        },
        {
            "role": "fill",
            "type": "Point",
            "position": at(-60.0, distance * 0.9, height * 0.7),
            "look_at": target,
            "intensity": round(key_intensity * 0.4, 3),
        },
        {
            "role": "rim",
            "type": "Point",
            "position": at(180.0, distance, height * 1.1),
            "look_at": target,
            "intensity": round(key_intensity * 0.7, 3),
        },
    ]
