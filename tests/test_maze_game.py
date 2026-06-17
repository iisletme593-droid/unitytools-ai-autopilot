"""P10 (cycle 49): maze blueprint — the 6th game type, built on the generator.

plan_maze_game turns a deterministic perfect maze into a playable game: solid
wall cubes + a WASD+jump player (with score HUD) at the entrance + a goal at the
exit. Every seed is deterministic, valid, playable, and reasonably sized; the
player and goal never sit inside a wall.
"""
import pytest

from unitytools.core.game_blueprint import plan_maze_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import validate_plan
from unitytools.core.maze import generate_maze, maze_wall_positions

SEEDS = ["a", "b", "42", "forest", "x-1"]


def _kw(step):
    return step.get("kwargs", {})


def test_registered_in_catalog():
    assert "maze" in BLUEPRINTS
    assert plan_game("maze", 5)["game"] == "maze"


def test_structure():
    plan = plan_maze_game(5)
    assert plan["ok"] is True and plan["game"] == "maze"
    assert plan["steps"][0]["kwargs"]["name"] == "Ground"
    # player: tagged, controller + score; goal present
    tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"]
    assert tags and tags[0]["kwargs"] == {"name": "Player", "tag": "Player"}
    player_scripts = {s["script_behaviour"]["behaviour"] for s in plan["steps"]
                      if s.get("script_behaviour", {}).get("object") == "Player"}
    assert player_scripts == {"player", "score"}
    assert any(s.get("script_behaviour") == {"object": "Goal", "behaviour": "goal"} for s in plan["steps"])
    # walls are solid (static_obstacle)
    solids = [s for s in plan["steps"] if s.get("tool") == "unity_add_gameplay_behaviour"
              and s["kwargs"]["behaviour"] == "static_obstacle"]
    assert len(solids) == plan["wall_count"] > 0


@pytest.mark.parametrize("seed", SEEDS)
def test_valid_and_playable(seed):
    plan = plan_game("maze", 5, seed=seed)
    assert validate_plan(plan)["ok"] is True
    assert assess_game_readiness(plan)["playable"] is True


def test_deterministic_and_seed_recorded():
    assert plan_game("maze", 5, seed="forest") == plan_game("maze", 5, seed="forest")
    assert plan_game("maze", 5, seed="forest") != plan_game("maze", 5, seed="desert")
    assert plan_game("maze", 5, seed="forest")["seed"] == "forest"
    assert "seed" not in plan_maze_game(5)            # unseeded -> no seed key


def test_size_clamped_and_object_count_reasonable():
    assert plan_maze_game(0)["size"] == 3
    assert plan_maze_game(99)["size"] == 8
    # even the largest maze stays well under the 500-object ceiling
    assert assess_game_readiness(plan_maze_game(8))["object_count"] < 200


def test_player_and_goal_are_not_inside_walls():
    plan = plan_maze_game(6, seed="check")
    walls = {(_kw(s)["position_x"], _kw(s)["position_z"]) for s in plan["steps"]
             if str(_kw(s).get("name", "")).startswith("Wall_")}
    player = next(_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Player")
    goal = next(_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Goal")
    assert (player["position_x"], player["position_z"]) not in walls
    assert (goal["position_x"], goal["position_z"]) not in walls
    assert (player["position_x"], player["position_z"]) != (goal["position_x"], goal["position_z"])


def test_player_goal_sit_on_entrance_and_exit_cells():
    n, seed = 5, "xy"
    plan = plan_maze_game(n, seed=seed)
    mz = generate_maze(seed, n, n)
    step = 1.0  # cell_size 2.0 / 2
    ex, ey = mz["entrance"]
    gx, gy = mz["exit"]
    player = next(_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Player")
    goal = next(_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Goal")
    assert (player["position_x"], player["position_z"]) == ((2 * ex + 1) * step, (2 * ey + 1) * step)
    assert (goal["position_x"], goal["position_z"]) == ((2 * gx + 1) * step, (2 * gy + 1) * step)


def test_groups_to_four_unique_scripts_one_recompile():
    grouped = group_execution_plan(plan_maze_game(5)["steps"])
    # player/score/goal + the dead-end trap killzone; walls are physics (tool steps, no recompile)
    assert set(grouped["script_behaviours"]) == {"player", "score", "goal", "killzone"}


# --- dead-end traps (cycle 102): deadly wrong turns, never block the solution -----

def test_dead_end_traps_are_off_the_solution_and_always_solvable():
    from unitytools.core.maze import maze_dead_end_cells, maze_is_solvable
    n, seed = 6, "trapcheck"
    mz = generate_maze(seed, n, n)
    dead_ends = maze_dead_end_cells(mz)
    # dead-ends exclude the entrance + exit, and the maze is still solvable (traps are not walls)
    assert mz["entrance"] not in dead_ends and mz["exit"] not in dead_ends
    assert maze_is_solvable(mz) is True
    plan = plan_maze_game(n, seed=seed)
    assert plan["trap_count"] == len(dead_ends)
    # each trap is a killzone; none sits on the player cell, the goal cell, or any wall cell
    traps = {(_kw(s)["position_x"], _kw(s)["position_z"]) for s in plan["steps"]
             if str(_kw(s).get("name", "")).startswith("Trap_")}
    walls = {(_kw(s)["position_x"], _kw(s)["position_z"]) for s in plan["steps"]
             if str(_kw(s).get("name", "")).startswith("Wall_")}
    player = next(_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Player")
    goal = next(_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Goal")
    assert (player["position_x"], player["position_z"]) not in traps
    assert (goal["position_x"], goal["position_z"]) not in traps
    assert traps.isdisjoint(walls)
    kz = [s for s in plan["steps"] if s.get("script_behaviour", {}).get("behaviour") == "killzone"]
    assert len(kz) == plan["trap_count"]


def test_trapped_maze_stays_clean_by_the_self_audit():
    from unitytools.core.game_qa import studio_health
    h = studio_health()
    mz_health = next(g for g in h["games"] if g["game_type"] == "maze")
    assert mz_health["valid"] and mz_health["playable"] and mz_health["coherent"]


def test_variations_work_for_maze():
    from unitytools.core.game_blueprint import plan_game_variations
    out = plan_game_variations("maze", counts=[3, 5, 7])
    assert [v["params"]["count"] for v in out["variations"]] == [3, 5, 7]
    assert all(v["playable"] for v in out["variations"])
