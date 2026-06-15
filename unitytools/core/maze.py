"""Maze generation — deterministic, always-solvable labyrinths (P10 step 1).

A new game type in the making: a procedural maze. ``generate_maze(seed, w, h)``
builds a *perfect* maze (a spanning tree over all cells via a seeded recursive
backtracker), so there is exactly one path between any two cells and the maze is
ALWAYS solvable. Pure and deterministic — same seed => same maze, no system time,
no global random. The result is a wall grid ('#' = wall, ' ' = passage) that maps
directly onto Unity wall cubes (see ``maze_wall_positions``), plus an entrance and
exit cell for the player and the goal.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from .procedural import seeded_rng

_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))   # fixed order; the seed picks among them


def generate_maze(seed: object, width: int = 6, height: int = 6) -> dict[str, Any]:
    """Generate a deterministic perfect maze.

    Returns {ok, width, height, grid, entrance, exit, seed} where ``grid`` is a list
    of ``2*height+1`` strings of ``2*width+1`` chars ('#'=wall, ' '=passage). The
    entrance is cell (0,0) and the exit is cell (width-1, height-1); both are
    passages. Always solvable (perfect maze). width/height are clamped to 1..25.
    """
    w = max(1, min(int(width), 25))
    h = max(1, min(int(height), 25))
    rng = seeded_rng(f"maze:{seed}:{w}x{h}")
    rows, cols = 2 * h + 1, 2 * w + 1
    grid = [["#"] * cols for _ in range(rows)]

    def carve_cell(cx: int, cy: int) -> None:
        grid[2 * cy + 1][2 * cx + 1] = " "

    visited = {(0, 0)}
    stack = [(0, 0)]
    carve_cell(0, 0)
    while stack:
        cx, cy = stack[-1]
        neighbours = [
            (cx + dx, cy + dy, dx, dy)
            for dx, dy in _DIRS
            if 0 <= cx + dx < w and 0 <= cy + dy < h and (cx + dx, cy + dy) not in visited
        ]
        if not neighbours:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(neighbours)
        grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = " "   # knock down the wall between
        carve_cell(nx, ny)
        visited.add((nx, ny))
        stack.append((nx, ny))

    return {
        "ok": True,
        "width": w,
        "height": h,
        "grid": ["".join(r) for r in grid],
        "entrance": (0, 0),
        "exit": (w - 1, h - 1),
        "seed": seed,
    }


def _cell_to_grid(cx: int, cy: int) -> tuple[int, int]:
    """Map a cell (cx, cy) to its (col, row) center in the wall grid."""
    return 2 * cx + 1, 2 * cy + 1


def maze_is_solvable(maze: dict[str, Any]) -> bool:
    """True if the exit cell is reachable from the entrance through passages.

    A correctly generated maze is always solvable; this BFS exists to PROVE it
    (and to guard against a malformed/imported maze). Pure.
    """
    grid = maze.get("grid") or []
    if not grid:
        return False
    rows, cols = len(grid), len(grid[0])
    sc, sr = _cell_to_grid(*maze["entrance"])
    ec, er = _cell_to_grid(*maze["exit"])
    if not (0 <= sr < rows and 0 <= sc < cols and grid[sr][sc] == " "):
        return False
    seen = {(sc, sr)}
    queue: deque[tuple[int, int]] = deque([(sc, sr)])
    while queue:
        c, r = queue.popleft()
        if (c, r) == (ec, er):
            return True
        for dc, dr in _DIRS:
            nc, nr = c + dc, r + dr
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == " " and (nc, nr) not in seen:
                seen.add((nc, nr))
                queue.append((nc, nr))
    return (ec, er) in seen


def maze_wall_positions(maze: dict[str, Any], cell_size: float = 2.0, origin=(0.0, 0.0)) -> list[tuple[float, float]]:
    """World (x, z) positions for every wall cell, for placing Unity wall cubes.

    Each '#' in the grid becomes one position, spaced by ``cell_size/2`` (wall and
    passage cells alternate in the grid). Deterministic. ``origin`` shifts the whole
    maze. Returns a flat list of (x, z) rounded to 3 places.
    """
    grid = maze.get("grid") or []
    step = float(cell_size) / 2.0
    ox, oz = origin
    return [
        (round(ox + c * step, 3), round(oz + r * step, 3))
        for r, row in enumerate(grid)
        for c, ch in enumerate(row)
        if ch == "#"
    ]
