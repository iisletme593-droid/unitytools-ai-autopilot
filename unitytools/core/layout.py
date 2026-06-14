"""Deterministic layout/placement helpers for the autopilot (level building).

Pure math, no Unity/bridge dependency, so it is fully unit-testable and runs on
any machine (no GPU). Tools use these to place N objects in a grid / circle /
line / scatter pattern with optional deterministic jitter.
"""
from __future__ import annotations

import math
from typing import List, Tuple

Vec3 = Tuple[float, float, float]

_PATTERNS = ("grid", "circle", "line", "scatter")


def _lcg(seed: int):
    """Deterministic 0..1 pseudo-random generator (no `random`, reproducible)."""
    s = (int(seed) * 2654435761 + 12345) & 0x7FFFFFFF

    def nxt() -> float:
        nonlocal s
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF

    return nxt


def compute_layout_positions(
    count: int,
    pattern: str = "grid",
    spacing: float = 2.0,
    origin: Vec3 = (0.0, 0.0, 0.0),
    jitter: float = 0.0,
    *,
    seed: int = 0,
) -> List[Vec3]:
    """Return `count` (x, y, z) positions arranged in `pattern`.

    pattern: "grid" | "circle" | "line" | "scatter" (unknown -> grid).
    spacing: distance between objects (grid/line) or radius scale (circle/scatter).
    origin:  center/start point.
    jitter:  per-position random offset of +/- jitter*spacing (deterministic via seed).
    """
    if count <= 0:
        return []
    pattern = (pattern or "grid").lower()
    ox, oy, oz = origin
    positions: List[Vec3] = []

    if pattern == "line":
        for i in range(count):
            positions.append((ox + i * spacing, oy, oz))
    elif pattern == "circle":
        radius = max(spacing, spacing * count / (2 * math.pi))
        for i in range(count):
            a = 2 * math.pi * i / count
            positions.append((ox + radius * math.cos(a), oy, oz + radius * math.sin(a)))
    elif pattern == "scatter":
        rnd = _lcg(seed)
        span = spacing * max(1.0, math.sqrt(count))
        for _ in range(count):
            rx = rnd() * 2 - 1
            rz = rnd() * 2 - 1
            positions.append((ox + rx * span, oy, oz + rz * span))
    else:  # grid (default)
        cols = max(1, int(math.ceil(math.sqrt(count))))
        for i in range(count):
            row, col = divmod(i, cols)
            positions.append((ox + col * spacing, oy, oz + row * spacing))

    if jitter > 0:
        rnd = _lcg(seed * 31 + 7)
        positions = [
            (x + (rnd() * 2 - 1) * jitter * spacing, y, z + (rnd() * 2 - 1) * jitter * spacing)
            for (x, y, z) in positions
        ]
    return positions


_STRUCTURES = ("wall", "tower", "stairs", "room", "floor")


def compute_structure_positions(
    kind: str = "wall",
    width: int = 5,
    height: int = 3,
    depth: int = 1,
    spacing: float = 1.0,
    origin: Vec3 = (0.0, 0.0, 0.0),
) -> List[Vec3]:
    """Block-out positions for a simple primitive structure (e.g. a wall of cubes).

    kind:
      - "wall"  : width x height grid in the XY plane (a flat wall).
      - "tower" : a vertical column of `height` blocks.
      - "stairs": `height` steps, each +1 up and +1 forward (a diagonal staircase).
      - "floor" : width x depth grid on the ground (y = origin.y).
      - "room"  : hollow width x depth footprint, `height` tall (perimeter walls only).
      - unknown -> "wall".
    """
    kind = (kind or "wall").lower()
    ox, oy, oz = origin
    width = max(1, int(width))
    height = max(1, int(height))
    depth = max(1, int(depth))
    out: List[Vec3] = []

    if kind == "tower":
        for h in range(height):
            out.append((ox, oy + h * spacing, oz))
    elif kind == "stairs":
        for s in range(height):
            out.append((ox, oy + s * spacing, oz + s * spacing))
    elif kind == "floor":
        for d in range(depth):
            for w in range(width):
                out.append((ox + w * spacing, oy, oz + d * spacing))
    elif kind == "room":
        for d in range(depth):
            for w in range(width):
                if w in (0, width - 1) or d in (0, depth - 1):
                    for h in range(height):
                        out.append((ox + w * spacing, oy + h * spacing, oz + d * spacing))
    else:  # wall
        for h in range(height):
            for w in range(width):
                out.append((ox + w * spacing, oy + h * spacing, oz))
    return out
