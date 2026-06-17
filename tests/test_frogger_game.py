"""P14 (cycle 119): Frogger -- the 21st game type, and the first about CROSSING LANES OF TRAFFIC.

New `wrapmover` behaviour (AutopilotWrapMover): glides +X and WRAPS (once past +bound it reappears
at -bound), so each lane is an endless stream. plan_frogger_game: a player at the near edge must
thread the gaps in L phase-staggered lanes of `wrapmover`+`killzone` traffic to reach the goal at
the far edge. Distinct from `dodge` (scattered drifting hazards): the threats are ORGANISED into
crossing lanes. A reach-the-goal WIN (gameover), no combat -- so no QA-surface changes.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_frogger_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, game_howto_from_plan, build_game_howto,
    _BEHAVIOUR_CATEGORIES, _BEHAVIOUR_PURPOSES, _GAME_EXAMPLES)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the wrapmover behaviour ------------------------------------------------

def test_wrapmover_source_glides_and_wraps():
    s = generate_behaviour_script("wrapmover")
    assert s["ok"] is True and s["class_name"] == "AutopilotWrapMover"
    src = s["source"]
    assert "Translate" in src and "bound" in src               # glides + wraps at a bound
    assert "speed" in src


def test_wrapmover_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("wrapmover")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["wrapmover", "lanemover", "trafik"])
def test_wrapmover_aliases(alias):
    assert normalize_behaviour(alias) == "wrapmover"


def test_wrapmover_registered_and_categorized():
    assert "wrapmover" in NEEDS_SCRIPT and "wrapmover" in _SCRIPT_TEMPLATES
    assert "wrapmover" in _BEHAVIOUR_CATEGORIES["movement"]     # drift guard
    assert "wrapmover" in _BEHAVIOUR_PURPOSES                   # glossary drift guard


# --- the blueprint ----------------------------------------------------------

def test_registered_as_twenty_first_game():
    assert "frogger" in BLUEPRINTS
    assert plan_game("frogger", 4)["game"] == "frogger"
    assert len(BLUEPRINTS) >= 21


def test_lanes_are_wrapping_traffic_with_a_goal():
    plan = plan_frogger_game(4)
    assert _beh_of(plan, "Player") == {"player"}
    # every obstacle composes wrapmover + killzone
    assert _beh_of(plan, "Obstacle") == {"wrapmover", "killzone"}
    assert _beh_of(plan, "Goal") == {"goal"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    # 4 lanes * 4 per lane = 16 obstacles, each a wrapmover
    n_traffic = sum(1 for s in plan["steps"]
                    if s.get("script_behaviour", {}).get("behaviour") == "wrapmover")
    assert n_traffic == 16
    # the player and goal sit at opposite edges (cross from near to far)
    pz = [s["kwargs"]["position_z"] for s in plan["steps"]
          if s.get("tool") == "unity_create_primitive" and s["kwargs"]["name"] == "Player"][0]
    gz = [s["kwargs"]["position_z"] for s in plan["steps"]
          if s.get("tool") == "unity_create_primitive" and s["kwargs"]["name"] == "Goal"][0]
    assert pz < 0 < gz


def test_frogger_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    fr = next(g for g in h["games"] if g["game_type"] == "frogger")
    assert fr["valid"] and fr["playable"] and fr["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "hop"])
def test_valid_and_playable(seed):
    plan = plan_game("frogger", 4, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True and r["has_goal"] is True
    assert r["design_notes"] == []


def test_seed_shifts_traffic_but_keeps_the_object_count():
    # the obstacles are named Obstacle_* so the seed shifts them laterally (varying the gaps),
    # but adds/removes nothing -> object_count is seed-independent
    base = assess_game_readiness(plan_game("frogger", 4))["object_count"]
    assert plan_game("frogger", 4, seed="x") != plan_game("frogger", 4, seed="y")
    assert plan_game("frogger", 4, seed=None) == plan_game("frogger", 4)
    for seed in ("x", "y", "z"):
        assert assess_game_readiness(plan_game("frogger", 4, seed=seed))["object_count"] == base


def test_lane_count_clamped():
    assert plan_frogger_game(0)["lane_count"] == 2
    assert plan_frogger_game(99)["lane_count"] == 12


# --- how-to + showcase + intent ---------------------------------------------

def test_howto_is_about_crossing_to_the_exit():
    h = game_howto_from_plan(plan_game("frogger", 4))
    assert any("reach the goal" in w.lower() for w in h["win"])
    assert any("hazard" in t.lower() for t in h["threats"])
    text = build_game_howto("frogger")
    assert all(ord(c) < 128 for c in text)


def test_showcase_example_present():
    assert "frogger" in _GAME_EXAMPLES
    prompt, pitch = _GAME_EXAMPLES["frogger"]
    assert pitch and all(ord(c) < 128 for c in prompt + pitch)


@pytest.mark.parametrize("prompt", [
    "frogger oyunu kur", "crossy road oyunu yap", "karsidan karsiya gec oyunu",
    "lane crossing game", "trafikten gec oyunu kur",
])
def test_frogger_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "frogger", prompt


def test_frogger_does_not_steal_dodge_or_stealth():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("dodge oyunu yap") == "dodge"
    assert gt("kacma oyunu kur") == "dodge"
    assert gt("gizli gec oyunu kur") == "stealth"               # "gec" alone is not a frogger trigger
