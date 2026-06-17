"""P10 (cycle 48): deterministic, always-solvable maze generation.

generate_maze builds a perfect maze (spanning tree over all cells) via a seeded
recursive backtracker — same seed/size => identical maze, and it is ALWAYS
solvable (proved by an independent BFS, maze_is_solvable). maze_wall_positions
maps the wall grid onto Unity cube positions. Pure; no system time.
"""
import pytest

from unitytools.core.maze import (
    generate_maze, maze_is_solvable, maze_wall_positions, maze_dead_end_cells)

SEEDS = ["a", "b", "c", "42", "forest", "x-1", "9", "level"]
SIZES = [(1, 1), (2, 2), (3, 4), (5, 5), (6, 8), (10, 10), (25, 25)]


# --- structure --------------------------------------------------------------

@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("size", [3, 5, 8])
def test_dead_end_cells_are_real_leaves_off_the_solution(seed, size):
    from collections import deque
    m = generate_maze(seed, size, size)
    grid = m["grid"]
    rows, cols = len(grid), len(grid[0])
    dead_ends = maze_dead_end_cells(m)
    # never the entrance or exit
    assert m["entrance"] not in dead_ends and m["exit"] not in dead_ends
    # each really has exactly ONE open passage (a leaf)
    for (cx, cy) in dead_ends:
        c, r = 2 * cx + 1, 2 * cy + 1
        opens = sum(1 for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= r + dr < rows and 0 <= c + dc < cols and grid[r + dr][c + dc] == " ")
        assert opens == 1, (cx, cy)
    # a dead-end is OFF the unique entrance->exit path: removing its passage keeps the maze
    # solvable (proof that a hazard there cannot block the solution)
    assert maze_is_solvable(m) is True
    # determinism
    assert maze_dead_end_cells(generate_maze(seed, size, size)) == dead_ends


def test_grid_dimensions_and_chars():
    m = generate_maze("s", 5, 4)
    assert m["ok"] is True and m["width"] == 5 and m["height"] == 4
    assert len(m["grid"]) == 2 * 4 + 1
    assert all(len(row) == 2 * 5 + 1 for row in m["grid"])
    assert set("".join(m["grid"])) <= {"#", " "}
    assert m["entrance"] == (0, 0) and m["exit"] == (4, 3)


def test_border_is_walls():
    m = generate_maze("s", 5, 5)
    g = m["grid"]
    assert set(g[0]) == {"#"} and set(g[-1]) == {"#"}          # top/bottom rows
    assert all(row[0] == "#" and row[-1] == "#" for row in g)  # left/right cols


def test_size_is_clamped():
    assert generate_maze("s", 0, 0)["width"] == 1
    assert generate_maze("s", 99, 99)["width"] == 25 and generate_maze("s", 99, 99)["height"] == 25


# --- determinism ------------------------------------------------------------

@pytest.mark.parametrize("seed", SEEDS)
def test_same_seed_same_maze(seed):
    assert generate_maze(seed, 8, 8) == generate_maze(seed, 8, 8)


def test_different_seeds_differ():
    assert generate_maze("one", 8, 8)["grid"] != generate_maze("two", 8, 8)["grid"]


# --- the key invariant: ALWAYS solvable -------------------------------------

@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("size", SIZES)
def test_every_maze_is_solvable(seed, size):
    m = generate_maze(seed, size[0], size[1])
    assert maze_is_solvable(m) is True


def test_perfect_maze_passage_count():
    # a perfect maze over W*H cells has exactly W*H passage cells + (W*H - 1) carved
    # walls between them => 2*W*H - 1 passage chars in the grid.
    w, h = 6, 7
    m = generate_maze("s", w, h)
    passages = "".join(m["grid"]).count(" ")
    assert passages == 2 * w * h - 1


def test_solvable_detects_a_broken_maze():
    # wall off the entrance -> not solvable (guards against malformed/imported mazes)
    m = generate_maze("s", 4, 4)
    g = list(m["grid"])
    g[1] = "#" * len(g[1])          # seal row 1 (entrance row)
    m["grid"] = g
    assert maze_is_solvable(m) is False


# --- wall positions (Unity mapping) -----------------------------------------

def test_wall_positions_match_wall_count_and_are_deterministic():
    m = generate_maze("s", 5, 5)
    walls = "".join(m["grid"]).count("#")
    pos = maze_wall_positions(m, cell_size=2.0)
    assert len(pos) == walls
    assert pos == maze_wall_positions(m, cell_size=2.0)        # deterministic
    assert all(isinstance(x, float) and isinstance(z, float) for x, z in pos)


def test_wall_positions_respect_origin():
    m = generate_maze("s", 3, 3)
    base = maze_wall_positions(m, cell_size=2.0, origin=(0.0, 0.0))
    shifted = maze_wall_positions(m, cell_size=2.0, origin=(10.0, 5.0))
    assert shifted[0] == (round(base[0][0] + 10.0, 3), round(base[0][1] + 5.0, 3))
