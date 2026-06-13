"""P1: deterministic layout/placement math for level building."""
import math

from unitytools.core.layout import compute_layout_positions


def test_count_and_empty():
    assert compute_layout_positions(0) == []
    assert compute_layout_positions(-3) == []
    assert len(compute_layout_positions(7, "grid")) == 7
    assert len(compute_layout_positions(5, "circle")) == 5
    assert len(compute_layout_positions(4, "line")) == 4
    assert len(compute_layout_positions(9, "scatter")) == 9


def test_line_spacing():
    pts = compute_layout_positions(3, "line", spacing=2.0, origin=(0.0, 0.0, 0.0))
    assert pts == [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (4.0, 0.0, 0.0)]


def test_grid_shape():
    pts = compute_layout_positions(4, "grid", spacing=1.0)  # 4 -> 2x2
    xs = sorted({round(p[0], 3) for p in pts})
    zs = sorted({round(p[2], 3) for p in pts})
    assert xs == [0.0, 1.0]
    assert zs == [0.0, 1.0]


def test_circle_points_equidistant():
    pts = compute_layout_positions(8, "circle", spacing=1.0, origin=(0.0, 0.0, 0.0))
    dists = [math.hypot(p[0], p[2]) for p in pts]
    assert max(dists) - min(dists) < 1e-6


def test_origin_offset_applied():
    pts = compute_layout_positions(1, "grid", origin=(10.0, 5.0, -3.0))
    assert pts == [(10.0, 5.0, -3.0)]


def test_unknown_pattern_falls_back_to_grid():
    a = compute_layout_positions(6, "bogus", spacing=1.5)
    b = compute_layout_positions(6, "grid", spacing=1.5)
    assert a == b


def test_scatter_deterministic_by_seed():
    a = compute_layout_positions(10, "scatter", spacing=2.0, seed=42)
    b = compute_layout_positions(10, "scatter", spacing=2.0, seed=42)
    c = compute_layout_positions(10, "scatter", spacing=2.0, seed=7)
    assert a == b
    assert a != c


def test_jitter_is_deterministic_and_bounded():
    base = compute_layout_positions(5, "line", spacing=2.0)
    j1 = compute_layout_positions(5, "line", spacing=2.0, jitter=0.25, seed=3)
    j2 = compute_layout_positions(5, "line", spacing=2.0, jitter=0.25, seed=3)
    assert j1 == j2  # deterministic
    assert j1 != base  # jitter actually moved things
    for (bx, _by, bz), (jx, _jy, jz) in zip(base, j1):
        assert abs(jx - bx) <= 0.25 * 2.0 + 1e-9
        assert abs(jz - bz) <= 0.25 * 2.0 + 1e-9
