"""P14 (cycle 86): sokoban puzzle -- the 13th game type, and the first with a PUSH
mechanic and no combat/timer.

New `pushable` (AutopilotPushable: a crate slides away from the approaching Player) and
`puzzle` (AutopilotPuzzle: a name-based win manager that wins once every Target_* has a
Crate_* on it -- no custom Unity tags, no hard type refs). plan_puzzle_game: a WASD
player + N pushable crates + N target markers + a GameManager(puzzle+title+sound).
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_puzzle_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, INTERACTIVE_BEHAVIOURS, studio_health)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the new behaviours -----------------------------------------------------

def test_pushable_source():
    s = generate_behaviour_script("pushable")
    assert s["ok"] is True and s["class_name"] == "AutopilotPushable"
    src = s["source"]
    assert 'FindWithTag("Player")' in src        # decoupled
    assert "pushRange" in src and "pushSpeed" in src
    assert "transform.position +=" in src         # it slides


def test_puzzle_manager_is_name_based_and_decoupled():
    src = generate_behaviour_script("puzzle")["source"]
    assert 'StartsWith("Target")' in src and 'StartsWith("Crate")' in src   # by NAME
    assert "CompareTag" not in src                # no custom tags
    assert "AutopilotPushable" not in src         # no hard type reference
    assert "Solved" in src and 'SendMessage("PlayCue"' in src   # win + decoupled beep


def test_new_behaviours_are_deterministic_ascii_balanced():
    for b in ("pushable", "puzzle"):
        src = generate_behaviour_script(b)["source"]
        assert all(ord(c) < 128 for c in src)
        assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
        assert "__" not in src
        for forbidden in ("Random.", "Math.random", "DateTime"):
            assert forbidden not in src


@pytest.mark.parametrize("alias,expected", [
    ("kutu", "pushable"), ("crate", "pushable"), ("itilebilir", "pushable"),
    ("puzzle", "puzzle"), ("sokoban", "puzzle"), ("bulmaca", "puzzle"),
])
def test_aliases(alias, expected):
    assert normalize_behaviour(alias) == expected


def test_registered_and_interactive():
    assert {"pushable", "puzzle"} <= NEEDS_SCRIPT
    assert {"pushable", "puzzle"} <= set(_SCRIPT_TEMPLATES)
    assert "pushable" in INTERACTIVE_BEHAVIOURS      # so the puzzle is playable


# --- the blueprint ----------------------------------------------------------

def test_registered_as_thirteenth_game():
    assert "puzzle" in BLUEPRINTS
    assert plan_game("puzzle", 3)["game"] == "puzzle"
    assert len(BLUEPRINTS) >= 13


def test_player_crates_targets_and_manager():
    plan = plan_puzzle_game(4)
    assert _beh_of(plan, "Player") == {"player"}
    assert _beh_of(plan, "Crate") == {"pushable"}
    assert _beh_of(plan, "GameManager") == {"puzzle", "title", "sound"}
    crates = [s["script_behaviour"]["object"] for s in plan["steps"]
              if s.get("script_behaviour", {}).get("behaviour") == "pushable"]
    assert crates == [f"Crate_{i}" for i in range(4)]
    # N target markers exist, named Target_*, with no script (the manager scores by name)
    targets = [s for s in plan["steps"] if s.get("tool") == "unity_place_primitives"
               and s["kwargs"]["name_prefix"] == "Target"]
    assert targets and targets[0]["kwargs"]["count"] == 4


def test_puzzle_is_clean_by_the_self_audit():
    # the new type must pass studio_health (valid + playable + coherent) like all others
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    assert "puzzle" in [g["game_type"] for g in h["games"]]
    puzzle = next(g for g in h["games"] if g["game_type"] == "puzzle")
    assert puzzle["valid"] and puzzle["playable"] and puzzle["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "box"])
def test_valid_and_playable(seed):
    plan = plan_game("puzzle", 3, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["design_notes"] == []


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("puzzle", 3, seed="x") == plan_game("puzzle", 3, seed="x")
    assert plan_game("puzzle", 3, seed="x") != plan_game("puzzle", 3, seed="y")
    assert plan_game("puzzle", 3, seed=None) == plan_game("puzzle", 3)


def test_crate_count_clamped():
    assert plan_puzzle_game(0)["crate_count"] == 1
    assert plan_puzzle_game(99)["crate_count"] == 20


# --- intent -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "puzzle oyunu kur", "sokoban yap", "bulmaca oyunu kur", "kutu itme oyunu yap",
])
def test_puzzle_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "puzzle", prompt


def test_puzzle_does_not_steal_other_intents():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("arena oyunu kur") == "arena"
    assert gt("toplama oyunu yap") == "collectathon"
    assert gt("stealth oyunu kur") == "stealth"
    assert gt("labirent oyunu kur") == "maze"
