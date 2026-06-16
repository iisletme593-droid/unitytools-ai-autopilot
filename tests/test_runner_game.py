"""P14 (cycle 70): the endless runner -- the 9th game type, and the first that
ISN'T arena/collectathon-style (a real variety addition).

`runner` (AutopilotRunner) auto-runs the player forward (+Z); A/D strafe, Space jumps.
Distance is the score: the runner SendMessages "AddScore" each second to its own
`score` HUD (decoupled). plan_runner_game lays a weaving lane of `killzone` obstacles
that snap the player back to the start on touch. Endless -- no goal/win.
"""
import pytest

from unitytools.core.game_blueprint import (
    plan_runner_game, plan_game, BLUEPRINTS, group_execution_plan)
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import validate_plan
from unitytools.core.gameplay import generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the runner behaviour --------------------------------------------------

def test_runner_behaviour_source():
    s = generate_behaviour_script("runner")
    assert s["ok"] is True and s["class_name"] == "AutopilotRunner"
    src = s["source"]
    assert "runSpeed" in src                                    # auto-forward
    assert "KeyCode.Space" in src and "jumpForce" in src        # jump
    assert 'GetAxis("Horizontal")' in src                       # strafe to dodge
    assert "Vector3(h * strafeSpeed, verticalVelocity, runSpeed)" in src  # forward +Z


def test_runner_feeds_a_decoupled_distance_score():
    src = generate_behaviour_script("runner")["source"]
    assert 'SendMessage("AddScore"' in src                      # decoupled score tick
    assert "DontRequireReceiver" in src                         # no-op without a score HUD
    assert "scoreInterval" in src and "scoreTimer" in src       # per-second cadence


def test_runner_behaviour_is_deterministic_pure_ascii_balanced():
    src = generate_behaviour_script("runner")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime", "System.Random"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["runner", "kosu", "kosucu", "endless", "kosan"])
def test_runner_aliases(alias):
    assert normalize_behaviour(alias) == "runner"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotRunner"


def test_runner_registered_in_needs_script():
    assert "runner" in NEEDS_SCRIPT


# --- the runner blueprint --------------------------------------------------

def test_registered_as_ninth_game():
    assert "runner" in BLUEPRINTS
    assert plan_game("runner", 6)["game"] == "runner"
    assert len(BLUEPRINTS) >= 9


def test_player_auto_runs_and_scores_distance():
    plan = plan_runner_game(6)
    assert _beh_of(plan, "Player") == {"runner", "score"}       # auto-run + distance HUD
    tags = {s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"] == "Player"}
    assert tags == {"Player"}


def test_obstacles_are_killzones_along_the_track():
    plan = plan_runner_game(5)
    obstacles = [s["script_behaviour"]["object"] for s in plan["steps"]
                 if s.get("script_behaviour", {}).get("behaviour") == "killzone"]
    assert obstacles == [f"Obstacle_{i}" for i in range(5)]
    # each obstacle sits further forward (+Z increasing) so they form a track
    zs = [s["kwargs"]["position_z"] for s in plan["steps"] if s.get("tool") == "unity_create_primitive"
          and str(s["kwargs"].get("name", "")).startswith("Obstacle_")]
    assert zs == sorted(zs) and len(set(zs)) == len(zs)


def test_endless_has_no_goal_or_gameover():
    # an endless runner never "wins" -- it has no goal zone and no gameover manager
    plan = plan_runner_game(6)
    behaviours = {s["script_behaviour"]["behaviour"] for s in plan["steps"]
                  if "script_behaviour" in s}
    assert "goal" not in behaviours and "gameover" not in behaviours


@pytest.mark.parametrize("seed", ["a", "b", "42", "run"])
def test_valid_and_playable(seed):
    plan = plan_game("runner", 6, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("runner", 6, seed="x") == plan_game("runner", 6, seed="x")
    assert plan_game("runner", 6, seed="x") != plan_game("runner", 6, seed="y")
    assert plan_game("runner", 6, seed=None) == plan_game("runner", 6)


def test_seed_shifts_the_obstacle_lanes_not_the_forward_spacing():
    plain = plan_runner_game(6)
    seeded = plan_game("runner", 6, seed="weave")
    def xs(plan):
        return [s["kwargs"].get("position_x", 0.0) for s in plan["steps"]
                if s.get("tool") == "unity_create_primitive"
                and str(s["kwargs"].get("name", "")).startswith("Obstacle_")]
    def zs(plan):
        return [s["kwargs"]["position_z"] for s in plan["steps"]
                if s.get("tool") == "unity_create_primitive"
                and str(s["kwargs"].get("name", "")).startswith("Obstacle_")]
    assert xs(plain) != xs(seeded)        # the weave changes with the seed
    assert zs(plain) == zs(seeded)        # the forward track spacing does not


def test_obstacle_count_clamped():
    assert plan_runner_game(0)["obstacle_count"] == 1
    assert plan_runner_game(99)["obstacle_count"] == 50


def test_variations_work_for_runner():
    from unitytools.core.game_blueprint import plan_game_variations
    out = plan_game_variations("runner", counts=[3, 6, 9])
    assert [v["params"]["count"] for v in out["variations"]] == [3, 6, 9]
    assert all(v["playable"] for v in out["variations"])
