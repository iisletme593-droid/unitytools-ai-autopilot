"""P9 (cycle 46): seed reaches the LAYOUT — patterns, spacing, platform shift.

A seed now varies placement pattern/spacing/jitter and a platformer's lateral
platform offsets, while keeping object counts and the climb (y/z) intact — so
every seed stays deterministic, valid, and playable.
"""
import pytest

from unitytools.core.procedural import seeded_pick, seeded_positions
from unitytools.core.game_blueprint import plan_game, BLUEPRINTS
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import validate_plan

SEEDS = ["s0", "s1", "s2", "s3", "s4", "42", "forest", "level-9"]


def _kw(step):
    return step.get("kwargs", {})


# --- new pure helpers -------------------------------------------------------

def test_seeded_pick_deterministic_and_in_options():
    opts = ["a", "b", "c", "d"]
    assert seeded_pick("x", opts) == seeded_pick("x", opts)
    assert seeded_pick("x", opts) in opts


def test_seeded_pick_empty_raises():
    with pytest.raises(ValueError):
        seeded_pick("x", [])


def test_seeded_positions_deterministic_and_bounded():
    a = seeded_positions("p", 10, area=8.0)
    b = seeded_positions("p", 10, area=8.0)
    assert a == b and len(a) == 10
    for x, z in a:
        assert -4.0 <= x <= 4.0 and -4.0 <= z <= 4.0


# --- seed varies the placement layout ---------------------------------------

def test_pattern_and_spacing_come_from_seed():
    a = plan_game("chase", 5, seed="one")
    b = plan_game("chase", 5, seed="two")
    pa = [_kw(s) for s in a["steps"] if s.get("tool") == "unity_place_primitives"]
    pb = [_kw(s) for s in b["steps"] if s.get("tool") == "unity_place_primitives"]
    assert pa and pb
    # at least one of pattern/spacing differs between the two seeds
    assert [(k["pattern"], k["spacing"]) for k in pa] != [(k["pattern"], k["spacing"]) for k in pb]
    for k in pa + pb:
        assert k["pattern"] in ("scatter", "circle", "grid")


# --- platformer keeps its climb monotone ------------------------------------

@pytest.mark.parametrize("seed", SEEDS)
def test_platformer_climb_stays_monotone(seed):
    plan = plan_game("platformer", 5, seed=seed)
    plats = [_kw(s) for s in plan["steps"] if str(_kw(s).get("name", "")).startswith("Platform_")]
    ys = [p["position_y"] for p in plats]
    zs = [p["position_z"] for p in plats]
    assert ys == sorted(ys) and len(set(ys)) == len(ys)   # strictly climbing
    assert zs == sorted(zs)                                # still stepping outward
    goal = [_kw(s) for s in plan["steps"] if _kw(s).get("name") == "Goal"][0]
    assert goal["position_x"] == plats[-1]["position_x"]   # goal stays on the top platform
    assert goal["position_y"] > plats[-1]["position_y"]


# --- invariants across every seed -------------------------------------------

@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
@pytest.mark.parametrize("seed", SEEDS)
def test_every_seed_is_valid_and_playable(game_type, seed):
    plan = plan_game(game_type, 5, seed=seed)
    assert validate_plan(plan)["ok"] is True
    assert assess_game_readiness(plan)["playable"] is True


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_object_count_is_seed_independent(game_type):
    # the seed perturbs layout, never the number of objects
    base = assess_game_readiness(plan_game(game_type, 5))["object_count"]
    for seed in SEEDS:
        assert assess_game_readiness(plan_game(game_type, 5, seed=seed))["object_count"] == base


def test_same_seed_same_plan_and_none_is_plain():
    assert plan_game("dodge", 5, seed="z") == plan_game("dodge", 5, seed="z")
    assert plan_game("platformer", 4, seed=None) == plan_game("platformer", 4)
    assert "seed" not in plan_game("platformer", 4)
