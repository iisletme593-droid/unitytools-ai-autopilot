"""P1: structure composition math (wall/tower/stairs/room/floor)."""
from unitytools.core.layout import compute_structure_positions


def test_wall_count_and_shape():
    pts = compute_structure_positions("wall", width=5, height=3, spacing=1.0)
    assert len(pts) == 15  # 5 x 3
    xs = {round(p[0], 3) for p in pts}
    ys = {round(p[1], 3) for p in pts}
    zs = {round(p[2], 3) for p in pts}
    assert xs == {0.0, 1.0, 2.0, 3.0, 4.0}
    assert ys == {0.0, 1.0, 2.0}
    assert zs == {0.0}  # flat wall


def test_tower_is_vertical():
    pts = compute_structure_positions("tower", height=4, spacing=2.0)
    assert len(pts) == 4
    assert all(p[0] == 0.0 and p[2] == 0.0 for p in pts)
    assert [p[1] for p in pts] == [0.0, 2.0, 4.0, 6.0]


def test_stairs_step_up_and_forward():
    pts = compute_structure_positions("stairs", height=3, spacing=1.0)
    assert pts == [(0.0, 0.0, 0.0), (0.0, 1.0, 1.0), (0.0, 2.0, 2.0)]


def test_floor_grid_count():
    pts = compute_structure_positions("floor", width=4, depth=3, spacing=1.0)
    assert len(pts) == 12  # 4 x 3 on the ground
    assert all(p[1] == 0.0 for p in pts)


def test_room_is_hollow_perimeter():
    pts = compute_structure_positions("room", width=3, depth=3, height=2, spacing=1.0)
    # perimeter of a 3x3 footprint = 8 cells, x 2 height = 16
    assert len(pts) == 16
    # the center column (1,*,1) must be empty (hollow)
    assert not any(p[0] == 1.0 and p[2] == 1.0 for p in pts)


def test_unknown_kind_falls_back_to_wall():
    a = compute_structure_positions("bogus", width=3, height=2)
    b = compute_structure_positions("wall", width=3, height=2)
    assert a == b
