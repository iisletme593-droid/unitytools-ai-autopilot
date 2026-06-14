"""Color helpers for the autopilot (pure, no bridge): name/hex/rgb -> RGB 0..1."""
from __future__ import annotations

from typing import Tuple

RGB = Tuple[float, float, float]

_NAMED = {
    "red": (1.0, 0.0, 0.0), "kirmizi": (1.0, 0.0, 0.0),
    "green": (0.0, 0.8, 0.0), "yesil": (0.0, 0.8, 0.0),
    "blue": (0.1, 0.3, 1.0), "mavi": (0.1, 0.3, 1.0),
    "yellow": (1.0, 0.9, 0.0), "sari": (1.0, 0.9, 0.0),
    "white": (1.0, 1.0, 1.0), "beyaz": (1.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0), "siyah": (0.0, 0.0, 0.0),
    "gray": (0.5, 0.5, 0.5), "grey": (0.5, 0.5, 0.5), "gri": (0.5, 0.5, 0.5),
    "orange": (1.0, 0.5, 0.0), "turuncu": (1.0, 0.5, 0.0),
    "purple": (0.5, 0.0, 0.8), "mor": (0.5, 0.0, 0.8),
    "pink": (1.0, 0.4, 0.7), "pembe": (1.0, 0.4, 0.7),
    "brown": (0.5, 0.3, 0.1), "kahverengi": (0.5, 0.3, 0.1),
    "gold": (0.83, 0.69, 0.22), "altin": (0.83, 0.69, 0.22),
    "cyan": (0.0, 0.9, 0.9), "magenta": (1.0, 0.0, 1.0),
}

_FALLBACK: RGB = (0.8, 0.8, 0.8)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _hex_to_rgb(h: str) -> RGB:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"invalid hex color: {h}")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def resolve_color(spec) -> RGB:
    """Resolve a color from a name (en/tr), '#RRGGBB'/'#RGB' hex, or 'r,g,b' (0-1 or 0-255)."""
    if isinstance(spec, (tuple, list)) and len(spec) == 3:
        r, g, b = (float(c) for c in spec)
    elif isinstance(spec, str):
        s = spec.strip().lower()
        if s in _NAMED:
            return _NAMED[s]
        if s.startswith("#"):
            try:
                return _hex_to_rgb(s)
            except ValueError:
                return _FALLBACK
        if "," in s:
            try:
                r, g, b = (float(p) for p in s.split(",")[:3])
            except ValueError:
                return _FALLBACK
        else:
            return _FALLBACK
    else:
        return _FALLBACK
    if max(r, g, b) > 1.0:  # treat as 0-255
        r, g, b = r / 255.0, g / 255.0, b / 255.0
    return (_clamp01(r), _clamp01(g), _clamp01(b))
