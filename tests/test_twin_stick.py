"""Cycle 103: twin-stick shooter -- the 18th game type, and the first RANGED-PRIMARY game.

The player is a lean kiter: movement + health + a `ranged` auto-aim weapon + score, with NO
melee attack (the gun is the whole game). It kites a ring of N enemies (enemy AI + reward)
while the weapon mows them down. Distinct from arena (melee + xp/loot + mini-boss) and horde
(full kit + wave spawner). Win by clearing the ring; lose if cornered. No new C# -- reuses
the existing behaviours.
"""
import pytest

from unitytools.core.game_blueprint import plan_twinstick_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import assess_game_readiness, studio_health, _GAME_EXAMPLES
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the blueprint ----------------------------------------------------------

def test_registered_as_eighteenth_game():
    assert "twin_stick" in BLUEPRINTS
    assert plan_game("twin_stick", 6)["game"] == "twin_stick"
    assert len(BLUEPRINTS) >= 18


def test_player_is_a_ranged_only_kiter():
    plan = plan_twinstick_game(6)
    # the lean kit: ranged (the gun) + health + score, and crucially NO melee attack
    assert _beh_of(plan, "Player") == {"player", "health", "ranged", "score"}
    assert "attack" not in _beh_of(plan, "Player")
    # the enemies are a chasable, killable ring
    assert _beh_of(plan, "Enemy") == {"enemy", "reward"}
    tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"].startswith("Enemy")]
    assert tags == ["Enemy"] * 6
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}


def test_twin_stick_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    ts = next(g for g in h["games"] if g["game_type"] == "twin_stick")
    assert ts["valid"] and ts["playable"] and ts["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "kite"])
def test_valid_and_playable(seed):
    plan = plan_game("twin_stick", 6, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["design_notes"] == []          # ranged + enemies + gameover is coherent


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("twin_stick", 6, seed="x") == plan_game("twin_stick", 6, seed="x")
    assert plan_game("twin_stick", 6, seed="x") != plan_game("twin_stick", 6, seed="y")
    assert plan_game("twin_stick", 6, seed=None) == plan_game("twin_stick", 6)


def test_enemy_count_clamped():
    assert plan_twinstick_game(0)["enemy_count"] == 1
    assert plan_twinstick_game(99)["enemy_count"] == 30


# --- showcase + intent ------------------------------------------------------

def test_has_a_showcase_example_that_routes():
    assert "twin_stick" in _GAME_EXAMPLES
    prompt = _GAME_EXAMPLES["twin_stick"][0]
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game" and step["kwargs"]["game_type"] == "twin_stick"


@pytest.mark.parametrize("prompt", [
    "twin stick oyunu kur", "twinstick yap", "top down shooter game", "iki yon ates oyunu kur",
])
def test_twin_stick_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "twin_stick", prompt


def test_twin_stick_does_not_steal_ranged_composer_or_other_combat():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"), s["kwargs"].get("ranged"))
    # the composer ranged FLAG ("menzilli"/"nisan") must still compose, not build twin_stick
    t, _gt, ranged = route("5 dusman menzilli oyun yap")
    assert t == "unity_compose_game" and ranged is True
    # arena + horde are untouched
    assert route("arena oyunu kur")[:2] == ("unity_build_simple_game", "arena")
    assert route("horde oyunu kur")[:2] == ("unity_build_simple_game", "horde")
